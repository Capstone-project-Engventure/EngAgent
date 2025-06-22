import app.api.routers
import logging
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.exercise import ExerciseRequest, ExerciseResponse

from app.db.session import get_db
from fastapi import Query
from typing import Any, Dict, Literal
import app.core.rag as rag
import app.core.prompts as prompt  
from app.services.exercise_service import _generate_exercise

logger = logging.getLogger(__name__)

router = APIRouter()

def _get_llm_pipeline(model_type: str):
    """Get LLM pipeline with fallback logic"""
    # Priority order: deepseek -> vertex -> ollama
    if model_type == "deepseek" and rag.pipelines["deepseek"]["llm"]:
        return "deepseek"
    elif model_type == "vertex" and rag.pipelines["vertex"]["llm"]:
        return "vertex"
    elif model_type == "ollama" and rag.pipelines["ollama"]["llm"]:
        return "ollama"
    else:
        # Fallback logic
        for key in ["deepseek", "vertex", "ollama"]:
            if rag.pipelines[key]["llm"]:
                logger.info(f"Falling back to {key} LLM")
                return key
        raise HTTPException(status_code=503, detail="No LLM pipeline available")

@router.post("/no-rag")
async def generate_no_rag(
    body: Dict[str, Any] = Body(...),
    model_type: Literal["ollama", "vertex", "deepseek"] = Query("ollama", alias="modelType"),
    db: AsyncSession = Depends(get_db),
):

    required_fields = ["prompt_name", "number", "type", "skill", "level", "topic"]
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {missing}")
    
    prompt_name = body.get("prompt_name","english_exercise_default")
    number = body.get("number", 1)
    exercise_type = body.get("type", "mcq")

    tpl = await prompt.get_prompt_template(prompt_name, db)

    try:
        prompt_text = tpl.format(**body, context="") #body.get("context", "No context provided")
    except Exception as e:
        logger.error("Error formatting prompt %s with vars %s: %s", prompt_name, body, e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Prompt format error: {e}")

    # Get LLM with fallback
    key = _get_llm_pipeline(model_type)
    llm = rag.pipelines[key]["llm"]
    
    logger.info(f"Using {key} LLM for generation")

    # Generate exercise with memory error handling
    try:
        result = await _generate_exercise(llm, prompt_text, expected_count=number, expected_type=exercise_type)
    except MemoryError:
        logger.warning(f"MemoryError on {key}, trying fallback")
        # Try other available pipelines
        for fallback_key in ["deepseek", "vertex", "ollama"]:
            if fallback_key != key and rag.pipelines[fallback_key]["llm"]:
                logger.info(f"Retrying with {fallback_key}")
                llm = rag.pipelines[fallback_key]["llm"]
                try:
                    result = await _generate_exercise(llm, prompt_text, expected_count=number, expected_type=exercise_type)
                    break
                except MemoryError:
                    continue
        else:
            raise HTTPException(status_code=503, detail="All LLM pipelines failed due to memory issues")

    result["context_length"] = 0
    result["used_model"] = key
    return JSONResponse(status_code=200, content=result)


@router.post("/native-rag")
async def generate_native_rag(
    body: Dict[str, Any] = Body(...),
    model_type: Literal["ollama", "vertex", "deepseek"] = Query("ollama", alias="modelType"),
    db: AsyncSession = Depends(get_db),
):
    """
    Tương tự /no-rag, nhưng trước đó chạy RAG chain để lấy context.
    Body cần có: prompt_name, skill, level, topic, type, …
    """

    required_fields = ["prompt_name", "number", "type", "skill", "level", "topic"]
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {missing}")
    
    # Get RAG context first
    key = _get_llm_pipeline(model_type)
    pipeline = rag.pipelines[key]
    llm, chain = pipeline.get("llm"), pipeline.get("chain")
    if not (llm and chain):
        raise HTTPException(status_code=503, detail=f"RAG pipeline '{key}' chưa khởi tạo")

    # Build RAG query
    rag_query = (
        f"Generate an English learning exercise for "
        f"skill={body.get('skill')}, level={body.get('level')}, "
        f"topic={body.get('topic')}, type={body.get('type')}"
    )
    rag_out = chain({"query": rag_query})
    context = rag_out.get("result", "")

    # 3) Get and format template
    prompt_name = body.get("prompt_name", "english_exercise_default")
    number = body.get("number", 1)
    tpl = await prompt.get_prompt_template(prompt_name, db)
    try:
        prompt_text = tpl.format(**body, context=context)
    except Exception as e:
        logger.error("Error formatting prompt %s: %s", prompt_name, e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Prompt format error: {e}")

    # 4) Gọi LLM
    result = await _generate_exercise(llm, prompt_text, number, body.get("type"))
    result["context_length"] = len(context)
    result["used_model"] = key
    return JSONResponse(status_code=200, content=result)