from sqlalchemy import (
    Column, Integer, String, Text, Boolean, JSON, ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class DBPromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    output_schema = Column(JSON, nullable=False, default=lambda: {})
    variables = Column(JSON, nullable=False, default=lambda: [])
    use_few_shot = Column(Boolean, default=False, nullable=False)
    min_count = Column(Integer, default=1, nullable=False)
    max_count = Column(Integer, default=15, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # 1-n relationship (one template → many examples)
    few_shot_examples = relationship(
        "FewShotExample",
        back_populates="template",
        cascade="all, delete-orphan",
    )


class FewShotExample(Base):
    __tablename__ = "few_shot_examples"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    skill = Column(String(50), nullable=False)
    level = Column(String(20), nullable=False)
    type = Column(String(20), nullable=False)
    topic = Column(String(100), nullable=False)
    example_json = Column(JSON, nullable=False)

    # back-populate lên template
    template = relationship(
        "DBPromptTemplate",
        back_populates="few_shot_examples",
    )
