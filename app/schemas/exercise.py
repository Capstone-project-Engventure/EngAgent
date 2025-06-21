from pydantic import BaseModel
from typing import Optional, Dict

class ExerciseRequest(BaseModel):
    name: str = "Exercise"
    skill: str
    level: str
    topic: str
    type: str
    prompt_name: str

class ExerciseResponse(BaseModel):
    id: int
    name: str
    question: str
    system_answer: Optional[str]
    type: str
    level: str
    skill: str
    lesson: Optional[str]
    generated_by: str
    description: Optional[str]
    options: Dict[str, str] | list = []
    duration_seconds: float
    context_length: int
