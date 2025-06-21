from typing import NamedTuple, List, Dict, Any
from langchain.prompts import PromptTemplate as LcPromptTemplate
from app.models import DBPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import DBAPIError, ProgrammingError
from app.services.prompt_service import get_by_name, list_all
import logging

logger = logging.getLogger(__name__)
# Define your prompt templates here
_exercise_default = LcPromptTemplate(
    input_variables=[
        "number",
        "name",
        "skill",
        "skills",
        "level",
        "topic",
        "type",
        # "context",
        "use_few_shot",
        "few_shot_examples",
        "model_name",
        "options",
    ],
    template_format="jinja2",
    template="""
    CRITICAL: Respond with ONLY a raw JSON array. No markdown, no explanations.
Your response must:
- Begin with [
- End with ]
- Contain only the JSON array.

Generate {{ number }} diverse English learning exercises of type '{{ type }}'. Each exercise must be unique and different.

[
{% for i in range(number|int) %}
  {
    "name": "{{ name }} - Exercise {{ loop.index }}",
    "question": "Generate a unique {{ type }} question for {{ skill }} at {{ level }} level, topic: {{ topic }}. Make it different from previous questions.",
    "system_answer": "{{ 'Provide correct option key (A/B/C/D)' if type=='mcq' else 'Provide correct answer' }}",
    "type": "{{ type }}",
    "level": "{{ level }}",
    "skill": "{{ skill }}",
    "topic": "{{ topic }}",
    "lesson": "lesson_{{ skill }}_{{ '%03d'|format(loop.index) }}",
    "generated_by": "{{ model_name if model_name else 'ai_model' }}",
    "description": "Provide clear, specific instructions for this {{ type }} exercise focusing on {{ skill }}"{% if type=='mcq' %},
    "options": [
      { "key": "A", "option": "First option" },
      { "key": "B", "option": "Second option" },
      { "key": "C", "option": "Third option" },
      { "key": "D", "option": "Fourth option" }
    ]{% endif %},
    "explanation": "Explain why the correct answer is correct, and why the other options are not. Be concise but clear."
  }{% if not loop.last %},{% endif %}
{% endfor %}
]

Instructions for AI model:
1. Create {{ number }} DIFFERENT exercises, not similar ones
2. Vary question types, difficulty within the level, and specific focus areas
3. For MCQ: Use object format for options with keys A, B, C, D
4. Make each exercise unique in content and approach
5. Ensure system_answer matches the correct option key for MCQ
6. Be creative with question formats while staying within the skill/topic boundaries
""",
)


class PromptData(NamedTuple):
    lc_template: LcPromptTemplate
    output_schema: Dict[str, Any]
    few_shots: List[Dict[str, Any]]


# Registry of all templates
_default_templates: Dict[str, LcPromptTemplate] = {
    "english_exercise_default": _exercise_default
}


async def get_prompt_template(name: str, db: AsyncSession) -> LcPromptTemplate:
    """
    1) Try DB
    2) On SQL errors, log + treat as missing
    3) Fallback to in-memory _default_templates
    4) If still missing, ValueError
    """
    db_obj = None
    try:
        db_obj = await get_by_name(db, name)
    except (ProgrammingError, DBAPIError) as e:
        logger.warning("Error querying prompt_templates.%r: %s", name, e)

    if db_obj:
        # if your JSONField returns a string, parse it:
        vars_list = db_obj.variables
        if isinstance(vars_list, str):
            import json

            vars_list = json.loads(vars_list)

        var_names = [v["name"] for v in vars_list]

        return LcPromptTemplate(
            input_variables=var_names,
            template=db_obj.content,
            template_format="jinja2",  # use Jinja2
            validate_template=False,  # skip f-string validation
        )

    # fallback
    default = _default_templates.get("english_exercise_default")
    if default:
        return default

    raise ValueError(f"Prompt template '{name}' không tồn tại")


# async def get_prompt_data(
#     name: str, db: AsyncSession
# ) -> PromptData:
#     db_obj = None
#     try:
#         db_obj = await get_by_name(db, name)
#     except (ProgrammingError, DBAPIError):
#         db_obj = None

#     if db_obj:
#         var_names = [v["name"] for v in db_obj.variables]
#         lc = LcPromptTemplate(
#             input_variables=var_names,
#             template=db_obj.content,
#             template_format="jinja2",
#             validate_template=False,
#         )
#         # few_shot_examples lưu trong DB có field example_json (dict)
#         few_shots = [ex.example_json for ex in db_obj.few_shot_examples]
#         return PromptData(lc, db_obj.output_schema, few_shots)

#     # fallback
#     lc = _default_templates[name]
#     return PromptData(lc, {}, [])


async def list_prompt_templates(db: AsyncSession) -> List[str]:
    """
    Nếu DB có bản ghi, trả tên của tất cả template trong DB;
    nếu không, trả danh sách các key của `_default_templates`.
    """
    try:
        db_objs = await list_all(db)
    except (ProgrammingError, DBAPIError) as e:
        logger.warning("Error listing PromptTemplates: %s", e)
        db_objs = []
    if db_objs:
        return [obj.name for obj in db_objs]
    return list(_default_templates.keys())
