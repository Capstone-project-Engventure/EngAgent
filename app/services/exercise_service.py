import json, re, time
import logging
from fastapi import HTTPException

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA

from app.core.config import settings
import app.core.rag as rag
from app.core.prompts import get_prompt_template

from app.db.session import engine
from app.models.exercise import Exercise
# from app.db.session import AsyncSessionLocal
from app.schemas.exercise import ExerciseRequest

logger = logging.getLogger(__name__)


def extract_clean_json(text: str):
    match = re.search(r"{.*}", text, re.DOTALL)
    if not match:
        raise ValueError("Không tìm thấy JSON trong response")
    return json.loads(match.group(0))

async def _generate_exercise(
    llm,
    prompt: str,
) -> dict:
    """Helper chung cho việc gọi LLM, parse JSON và đo thời gian."""
    start = time.time()
    try:
        raw = llm.invoke(prompt)
    except Exception as e:
        logger.error("Error khi gọi LLM: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="LLM service error")

    try:
        text = raw.content if hasattr(raw, "content") else str(raw)
        data = extract_clean_json(text)
    except (ValueError, json.JSONDecodeError) as e:
        logger.error("Failed to parse JSON từ LLM response: %s\nRaw: %s", e, raw, exc_info=True)
        raise HTTPException(status_code=500, detail="Invalid JSON format from LLM")

    # metadata
    data["duration_seconds"] = time.time() - start
    return data

async def create_exercise_no_rag(
    db: AsyncSession,
    request: ExerciseRequest,
    use_vertex: bool = False
) -> JSONResponse:
    template = await get_prompt_template("exercise", db)
    prompt = template.format(
        name=request.name,
        skill=request.skill,
        level=request.level,
        topic=request.topic,
        type=request.type,
        context="No context provided",
    )
    key = "vertex" if use_vertex else "ollama"
    llm = rag.pipelines[key]["llm"]
    if not llm:
        raise HTTPException(status_code=503, detail=f"LLM pipeline '{key}' unavailable")

    
    try:
        data = await _generate_exercise(llm, prompt)
    except MemoryError:
        logger.error("MemoryError khi gọi LLM với prompt: %s", prompt, exc_info=True)
        key = "vertex"
        llm = rag.pipelines[key]["llm"]
        data = await _generate_exercise(llm, prompt)
    # bổ sung field context_length
    data["context_length"] = 0
    return JSONResponse(status_code=200, content=data)

async def create_exercise_native_rag(
    db: AsyncSession,
    request: ExerciseRequest,
    use_vertex: bool = False
) -> JSONResponse:
    key = "vertex" if use_vertex else "ollama"
    llm   = rag.pipelines[key]["llm"]
    chain = rag.pipelines[key]["chain"]
    if not llm or not chain:
        raise HTTPException(status_code=503, detail="RAG pipeline chưa khởi tạo")

    query = (
        f"Generate an English learning exercise for skill: {request.skill}, "
        f"level: {request.level}, topic: {request.topic}, type: {request.type}"
    )
    rag_result = chain({"query": query})
    context = rag_result.get("result") or ""

    template = await get_prompt_template("exercise", db)
    prompt = template.format(
        name=request.name,
        skill=request.skill,
        level=request.level,
        topic=request.topic,
        type=request.type,
        context=context,
    )

    data = await _generate_exercise(llm, prompt)
    data["context_length"] = len(context)
    return JSONResponse(status_code=200, content=data)

 