"""
repositories/history_repo.py
----------------------------
Read-model data access for unified learning history.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import QuestionBankItem
from src.models.course import CourseSection, LearningUnit
from src.models.learning import Interaction, Session

HistoryDetailRow = tuple[Interaction, None, QuestionBankItem | None, None]


class HistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_sessions(self, *, filters: list) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Session).where(*filters)
        )
        return result.scalar() or 0

    async def fetch_history_page_canonical_only(
        self,
        *,
        filters: list,
        page: int,
        page_size: int,
    ) -> list[tuple[Session, str | None, str | None]]:
        result = await self.session.execute(
            select(Session, LearningUnit.title, CourseSection.title)
            .outerjoin(LearningUnit, Session.canonical_unit_id == LearningUnit.id)
            .outerjoin(CourseSection, Session.canonical_section_id == CourseSection.id)
            .where(*filters)
            .order_by(Session.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.all()

    async def fetch_sessions_for_summary(self, *, filters: list) -> list[Session]:
        result = await self.session.execute(
            select(Session).where(*filters).order_by(Session.started_at.asc())
        )
        return result.scalars().all()

    async def get_owned_session(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> Session | None:
        result = await self.session.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def fetch_session_detail_rows_canonical_only(
        self,
        session_id: uuid.UUID,
    ) -> list[HistoryDetailRow]:
        result = await self.session.execute(
            select(
                Interaction,
                QuestionBankItem,
            )
            .outerjoin(QuestionBankItem, Interaction.canonical_item_id == QuestionBankItem.item_id)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.sequence_position)
        )
        return [
            (interaction, None, canonical_item, None)
            for interaction, canonical_item in result.all()
        ]
