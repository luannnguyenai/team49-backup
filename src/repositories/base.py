"""
repositories/base.py
---------------------
Generic BaseRepository[T] — all concrete repos inherit from this.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: UUID) -> T | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def create(self, **data) -> T:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: UUID) -> None:
        obj = await self.get_by_id(id)
        if obj:
            await self.session.delete(obj)
