"""
repositories/mastery_repo.py
------------------------------
Data access for MasteryScore — upsert via INSERT ... ON CONFLICT.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import MasteryLevel, MasteryScore
from src.repositories.base import BaseRepository


class MasteryRepository(BaseRepository[MasteryScore]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MasteryScore)

    async def get_by_user_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
        kc_id: UUID | None = None,
    ) -> MasteryScore | None:
        """Fetch by the unique (user_id, topic_id, kc_id) key."""
        stmt = select(MasteryScore).where(
            MasteryScore.user_id == user_id,
            MasteryScore.topic_id == topic_id,
            MasteryScore.kc_id == kc_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: UUID,
        topic_id: UUID,
        kc_id: UUID | None,
        **mastery_data,
    ) -> MasteryScore:
        """INSERT ... ON CONFLICT (user_id, topic_id, kc_id) DO UPDATE."""
        values = {
            "user_id": user_id,
            "topic_id": topic_id,
            "kc_id": kc_id,
            **mastery_data,
        }
        stmt = (
            pg_insert(MasteryScore)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_mastery_user_topic_kc",
                set_={k: v for k, v in mastery_data.items()},
            )
            .returning(MasteryScore)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        row = result.scalar_one()
        return row

    async def bulk_get_for_user(
        self,
        user_id: UUID,
        topic_ids: list[UUID],
    ) -> dict[UUID, MasteryScore]:
        """Fetch all mastery scores for a user across multiple topics in one query."""
        if not topic_ids:
            return {}
        result = await self.session.execute(
            select(MasteryScore).where(
                MasteryScore.user_id == user_id,
                MasteryScore.topic_id.in_(topic_ids),
                MasteryScore.kc_id.is_(None),  # topic-grain only
            )
        )
        rows = result.scalars().all()
        return {row.topic_id: row for row in rows}
