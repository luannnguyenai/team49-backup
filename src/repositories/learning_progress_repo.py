"""
repositories/learning_progress_repo.py
--------------------------------------
Data access for canonical learning unit progress records.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course import LearningProgressRecord
from src.repositories.base import BaseRepository


class LearningProgressRepository(BaseRepository[LearningProgressRecord]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, LearningProgressRecord)

    async def get_for_user_unit(
        self,
        user_id: UUID,
        learning_unit_id: UUID,
    ) -> LearningProgressRecord | None:
        result = await self.session.execute(
            select(LearningProgressRecord).where(
                LearningProgressRecord.user_id == user_id,
                LearningProgressRecord.learning_unit_id == learning_unit_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user_units(
        self,
        user_id: UUID,
        learning_unit_ids: list[UUID],
    ) -> dict[UUID, LearningProgressRecord]:
        if not learning_unit_ids:
            return {}
        result = await self.session.execute(
            select(LearningProgressRecord).where(
                LearningProgressRecord.user_id == user_id,
                LearningProgressRecord.learning_unit_id.in_(learning_unit_ids),
            )
        )
        rows = result.scalars().all()
        return {row.learning_unit_id: row for row in rows}

    async def upsert(
        self,
        *,
        user_id: UUID,
        course_id: UUID,
        learning_unit_id: UUID,
        **values,
    ) -> LearningProgressRecord:
        row = await self.get_for_user_unit(user_id, learning_unit_id)
        if row is None:
            row = LearningProgressRecord(
                user_id=user_id,
                course_id=course_id,
                learning_unit_id=learning_unit_id,
                **values,
            )
            self.session.add(row)
        else:
            row.course_id = course_id
            for key, value in values.items():
                setattr(row, key, value)

        await self.session.flush()
        await self.session.refresh(row)
        return row
