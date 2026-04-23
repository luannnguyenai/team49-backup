"""
repositories/waived_unit_repo.py
--------------------------------
Data access for WaivedUnit — one audit row per user × learning unit pair.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import WaivedUnit
from src.repositories.base import BaseRepository


class WaivedUnitRepository(BaseRepository[WaivedUnit]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WaivedUnit)

    async def get_for_user_unit(self, user_id: UUID, learning_unit_id: UUID) -> WaivedUnit | None:
        result = await self.session.execute(
            select(WaivedUnit).where(
                WaivedUnit.user_id == user_id,
                WaivedUnit.learning_unit_id == learning_unit_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[WaivedUnit]:
        result = await self.session.execute(
            select(WaivedUnit)
            .where(WaivedUnit.user_id == user_id)
            .order_by(WaivedUnit.created_at.desc())
        )
        return list(result.scalars().all())

    async def upsert(self, user_id: UUID, learning_unit_id: UUID, **waive_data) -> WaivedUnit:
        values = {
            "user_id": user_id,
            "learning_unit_id": learning_unit_id,
            **waive_data,
        }
        stmt = (
            pg_insert(WaivedUnit)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_waived_units_user_unit",
                set_=waive_data,
            )
            .returning(WaivedUnit)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()
