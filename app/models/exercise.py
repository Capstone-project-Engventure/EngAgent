from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(length=100), nullable=False)
    question = Column(String(length=1000), nullable=False)
    system_answer = Column(String(length=1000), nullable=True)
    type = Column(String(length=50), nullable=False)
    level = Column(String(length=50), nullable=False)
    skill = Column(String(length=50), nullable=False)
    lesson = Column(String(length=100), nullable=True)
    generated_by = Column(String(length=100), nullable=False)
    description = Column(String(length=500), nullable=True)
    options = Column(JSON, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    context_length = Column(Integer, nullable=True)
    
    # Approval fields
    is_approved = Column(Boolean, default=False, nullable=False)
    is_rejected = Column(Boolean, default=False, nullable=False)
    rejection_reason = Column(String(length=500), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)