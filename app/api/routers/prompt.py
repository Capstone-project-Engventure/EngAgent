# app/api/v1/routers/prompts.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate

from app.core.prompts import _default_templates, get_prompt_template, list_prompt_templates
import app.core.rag as rag

router = APIRouter()

# Schemas
template_response = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "input_variables": {
            "type": "array",
            "items": {"type": "string"}
        },
        "template": {"type": "string"}
    }
}

class PromptTemplateSchema(BaseModel):
    name: str
    input_variables: List[str]
    template: str

class GenerateIn(BaseModel):
    variables: Dict[str, Any]

class GenerateOut(BaseModel):
    result: str

# CRUD endpoints for prompt templates
@router.get("/", response_model=List[str])
async def list_templates():
    """List all available prompt template names"""
    return list_prompt_templates()

@router.get("/{name}", response_model=PromptTemplateSchema, responses={404: {"description": "Not Found"}})
async def get_template(name: str):
    """Get a prompt template by name"""
    try:
        tpl = get_prompt_template(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PromptTemplateSchema(
        name=name,
        input_variables=tpl.input_variables,
        template=tpl.template
    )

@router.post("/", response_model=PromptTemplateSchema, status_code=201)
async def create_template(schema: PromptTemplateSchema):
    """Create a new prompt template"""
    if schema.name in _default_templates:
        raise HTTPException(status_code=400, detail="Template already exists")
    tpl = PromptTemplate(
        input_variables=schema.input_variables,
        template=schema.template
    )
    _default_templates[schema.name] = tpl
    return schema

@router.put("/{name}", response_model=PromptTemplateSchema, responses={404: {"description": "Not Found"}})
async def update_template(name: str, schema: PromptTemplateSchema):
    """Update an existing prompt template"""
    if name not in _default_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    tpl = PromptTemplate(
        input_variables=schema.input_variables,
        template=schema.template
    )
    _default_templates[name] = tpl
    return schema

@router.delete("/{name}", status_code=204, responses={404: {"description": "Not Found"}})
async def delete_template(name: str):
    """Delete a prompt template"""
    if name not in _default_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    del _default_templates[name]
    return None

# Generate from selected template
@router.post("/{name}/generate", response_model=GenerateOut, responses={404: {"description": "Template Not Found"}})
async def generate_prompt(name: str, body: GenerateIn):
    """Generate content using specified prompt template"""
    try:
        tpl = get_prompt_template(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        prompt = tpl.format(**body.variables)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing variable: {e}")

    try:
        raw = llm(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return GenerateOut(result=raw)
