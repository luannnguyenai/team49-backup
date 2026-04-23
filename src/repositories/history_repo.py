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
from src.models.content import KnowledgeComponent, Module, Question, Topic
from src.models.learning import Interaction, Session


class HistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_sessions(self, *, filters: list) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Session).where(*filters)
        )
        return result.scalar() or 0

    async def fetch_history_page(
        self,
        *,
        filters: list,
        page: int,
        page_size: int,
    ) -> list[tuple[Session, str | None, str | None]]:
        result = await self.session.execute(
            select(
                Session,
                Topic.name.label("topic_name"),
                Module.name.label("module_name"),
            )
            .outerjoin(Topic, Session.topic_id == Topic.id)
            .outerjoin(
                Module,
                (Session.module_id == Module.id) | (Topic.module_id == Module.id),
            )
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

    async def fetch_session_detail_rows(
        self,
        session_id: uuid.UUID,
    ) -> list[tuple[Interaction, Question | None, QuestionBankItem | None, str | None]]:
        result = await self.session.execute(
            select(
                Interaction,
                Question,
                QuestionBankItem,
                Topic.name.label("topic_name"),
            )
            .outerjoin(Question, Interaction.question_id == Question.id)
            .outerjoin(QuestionBankItem, Interaction.canonical_item_id == QuestionBankItem.item_id)
            .outerjoin(Topic, Question.topic_id == Topic.id)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.sequence_position)
        )
        return result.all()

    async def resolve_kc_names(self, kc_ids: list[uuid.UUID]) -> dict[str, str]:
        if not kc_ids:
            return {}
        result = await self.session.execute(
            select(KnowledgeComponent).where(KnowledgeComponent.id.in_(kc_ids))
        )
        return {str(kc.id): kc.name for kc in result.scalars().all()}
