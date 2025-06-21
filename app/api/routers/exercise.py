import app.api.routers
import logging
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.exercise import ExerciseRequest, ExerciseResponse

from app.db.session import get_db
from fastapi import Query
from typing import Any, Dict
import app.core.rag as rag
import app.core.prompts as prompt  
from app.services.exercise_service import _generate_exercise

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/no-rag")
async def generate_no_rag(
    body: Dict[str, Any] = Body(...),
    use_vertex: bool = Query(False, alias="useVertex"),
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


    key = "vertex" if use_vertex else "ollama"
    llm = rag.pipelines[key]["llm"]
    if not llm:
        raise HTTPException(status_code=503, detail=f"LLM pipeline '{key}' unavailable")

    # 4) Gọi LLM, fallback nếu MemoryError
    try:
        result = await _generate_exercise(llm, prompt_text, expected_count=number, expected_type=exercise_type)
    except MemoryError:
        logger.warning("MemoryError on %s, retrying on Vertex", key)
        llm = rag.pipelines["vertex"]["llm"]
        if not llm:
            raise HTTPException(status_code=503, detail="Vertex LLM unavailable for retry")
        result = await _generate_exercise(llm, prompt_text, expected_count=number, expected_type=exercise_type)

    result["context_length"] = 0
    return JSONResponse(status_code=200, content=result)


@router.post("/native-rag")
async def generate_native_rag(
    body: Dict[str, Any] = Body(...),
    use_vertex: bool = Query(False, alias="useVertex"),
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
    key = "vertex" if use_vertex else "ollama"
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
    result = await _generate_exercise(llm, prompt_text, number, type)
    result["context_length"] = len(context)
    return JSONResponse(status_code=200, content=result)