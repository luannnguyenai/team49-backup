"""
repositories/learner_mastery_kp_repo.py
---------------------------------------
Data access for LearnerMasteryKP — upsert and bulk lookup keyed by user × kp_id.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import LearnerMasteryKP
from src.repositories.base import BaseRepository


class LearnerMasteryKPRepository(BaseRepository[LearnerMasteryKP]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, LearnerMasteryKP)

    async def get_by_user_kp(self, user_id: UUID, kp_id: str) -> LearnerMasteryKP | None:
        result = await self.session.execute(
            select(LearnerMasteryKP).where(
                LearnerMasteryKP.user_id == user_id,
                LearnerMasteryKP.kp_id == kp_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: UUID, kp_id: str, **mastery_data) -> LearnerMasteryKP:
        values = {"user_id": user_id, "kp_id": kp_id, **mastery_data}
        stmt = (
            pg_insert(LearnerMasteryKP)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_learner_mastery_kp_user_kp",
                set_=mastery_data,
            )
            .returning(LearnerMasteryKP)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_get_for_user(
        self,
        user_id: UUID,
        kp_ids: list[str],
    ) -> dict[str, LearnerMasteryKP]:
        if not kp_ids:
            return {}
        result = await self.session.execute(
            select(LearnerMasteryKP).where(
                LearnerMasteryKP.user_id == user_id,
                LearnerMasteryKP.kp_id.in_(kp_ids),
            )
        )
        rows = result.scalars().all()
        return {row.kp_id: row for row in rows}
