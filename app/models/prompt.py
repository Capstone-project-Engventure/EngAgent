from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
Base = declarative_base()
enum_choices = ['ollama', 'vertex', 'rag_ollama', 'rag_vertex']

# SQLAlchemy model reflecting the Django PromptTemplate table

class DBPromptTemplate(Base):
    __tablename__ = 'prompt_templates'  # adjust to your Django table name (app_label)
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    engine = Column(String(20))
    content = Column(Text)

class PromptTemplateOut(BaseModel):
    name: str
    engine: str | None = None
    content: str

    class Config:
        orm_mode = True
