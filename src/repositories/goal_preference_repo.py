"""
repositories/goal_preference_repo.py
------------------------------------
Data access for GoalPreference — single row per user with upsert semantics.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import GoalPreference
from src.repositories.base import BaseRepository


class GoalPreferenceRepository(BaseRepository[GoalPreference]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, GoalPreference)

    async def get_by_user_id(self, user_id: UUID) -> GoalPreference | None:
        result = await self.session.execute(
            select(GoalPreference).where(GoalPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_for_user(self, user_id: UUID, **goal_data) -> GoalPreference:
        values = {"user_id": user_id, **goal_data}
        stmt = (
            pg_insert(GoalPreference)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[GoalPreference.user_id],
                set_=goal_data,
            )
            .returning(GoalPreference)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()
