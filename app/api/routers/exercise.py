from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.exercise import ExerciseRequest, ExerciseResponse
from app.services.exercise_service import (
    create_exercise_no_rag,
    create_exercise_native_rag,
)
from app.db.session import get_db
from fastapi import Query
router = APIRouter()

@router.post("/no-rag", response_model=ExerciseResponse)
async def generate_no_rag(
    req: ExerciseRequest, use_vertex: bool = Query(False, alias="useVertex"), db: AsyncSession = Depends(get_db),
):
    try:
        return await create_exercise_no_rag(db, req,use_vertex)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/native-rag", response_model=ExerciseResponse)
async def generate_native_rag(
    req: ExerciseRequest,
    use_vertex: bool = Query(False, alias="useVertex"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_exercise_native_rag(db, req, use_vertex)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))