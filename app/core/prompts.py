from langchain.prompts import PromptTemplate
from typing import Dict, List
from langchain.prompts import PromptTemplate as LcPromptTemplate
from app.models import DBPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import DBAPIError, ProgrammingError
from app.services.prompt_service import get_by_name, list_all 
import logging
logger = logging.getLogger(__name__)
# Define your prompt templates here
_exercise_default = PromptTemplate(
    input_variables=["skill", "level", "topic", "type", "name", "context"],
    template="""
You are an educational content generator. Your task is to return a **valid JSON object only**.
Requirements:
    - Do NOT include any markdown syntax like ```json
    - Do NOT add explanation or description outside the JSON
    - Use the provided context to enhance the exercise if available
    - If the type is not mcq, leave the options field empty

Generate 1 English learning exercise in JSON with the following metadata:
- Name: {name}
- Skill: {skill}
- Level: {level}
- Topic: {topic}
- Type: {type}
Return strictly formatted JSON like:
{{
  "name": "{name}",
  "question": "Question text",
  "system_answer": null,
  "type": "{type}",
  "level": "{level}",
  "skill": "{skill}",
  "lesson": "lesson_id",
  "generated_by": "mistral_model",
  "description": "Instruction",
  "options": {{
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "..."
  }} || []
}}
Context: {context}
""",
)

# Registry of all templates
_default_templates: Dict[str, PromptTemplate] = {
    "exercise": _exercise_default,
  
}

async def get_prompt_template(
    name: str,
    db: AsyncSession
) -> LcPromptTemplate:
    """
    1) Thử lấy `PromptTemplate` từ DB qua get_by_name.
    2) Nếu có lỗi DB (ví dụ table không tồn tại), ghi log và coi như không tìm được.
    3) Nếu không có trong DB, fallback về `_default_templates`.
    4) Nếu vẫn không tồn tại, raise ValueError.
    """
    try:
        db_obj = await get_by_name(db, name)
    except (ProgrammingError, DBAPIError) as e:
        # catch lỗi SQLAlchemy wrap DBAPIError hoặc ProgrammingError
        logger.warning("Lỗi khi truy vấn prompt_templates.%s: %s", name, e)
        db_obj = None

    if db_obj:
        return LcPromptTemplate(
            input_variables=_exercise_default.input_variables,
            template=db_obj.content
        )

    # Fallback về default template
    try:
        return _default_templates[name]
    except KeyError:
        raise ValueError(f"Prompt template '{name}' không tồn tại")


async def list_prompt_templates(db: AsyncSession) -> List[str]:
    """
    Nếu DB có bản ghi, trả tên của tất cả template trong DB;
    nếu không, trả danh sách các key của `_default_templates`.
    """
    db_objs = await list_all(db)
    if db_objs:
        return [obj.name for obj in db_objs]
    return list(_default_templates.keys())