from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DBPromptTemplate

async def get_by_name(
    db: AsyncSession, name: str
) -> Optional[DBPromptTemplate]:
    """Trả về PromptTemplate DB hoặc None nếu không có."""
    result = await db.execute(
        select(DBPromptTemplate).where(DBPromptTemplate.name == name)
    )
    return result.scalars().first()

async def list_all(
    db: AsyncSession
) -> List[DBPromptTemplate]:
    """Trả về tất cả bản ghi PromptTemplate trong DB."""
    result = await db.execute(select(DBPromptTemplate))
    return result.scalars().all()