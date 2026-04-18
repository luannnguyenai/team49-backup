"""
repositories/assessment_repo.py
-------------------------------
Assessment-specific data access helpers used by assessment_service.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.content import KnowledgeComponent, Question, Topic
from src.models.learning import Interaction, MasteryScore, Session, SessionType


class AssessmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_topics_by_ids(self, topic_ids: list[uuid.UUID]) -> list[Topic]:
        result = await self.session.execute(select(Topic).where(Topic.id.in_(topic_ids)))
        return result.scalars().all()

    async def get_answered_question_rows(
        self,
        user_id: uuid.UUID,
    ) -> list[tuple[uuid.UUID, bool]]:
        result = await self.session.execute(
            select(Interaction.question_id, Interaction.is_correct)
            .where(Interaction.user_id == user_id)
            .distinct(Interaction.question_id)
        )
        return result.all()

    async def get_questions_by_ids(
        self,
        question_ids: list[uuid.UUID],
    ) -> list[Question]:
        result = await self.session.execute(
            select(Question).where(Question.id.in_(question_ids))
        )
        return result.scalars().all()

    async def get_max_global_sequence(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.max(Interaction.global_sequence_position)).where(
                Interaction.user_id == user_id
            )
        )
        return result.scalar() or 0

    async def get_assessment_session(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> Session | None:
        result = await self.session.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
                Session.session_type == SessionType.assessment,
            )
        )
        return result.scalar_one_or_none()

    async def get_session_question_rows(
        self,
        session_id: uuid.UUID,
    ) -> list[tuple[Interaction, Question]]:
        result = await self.session.execute(
            select(Interaction, Question)
            .join(Question, Interaction.question_id == Question.id)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.sequence_position)
        )
        return result.all()

    async def get_mastery_score(
        self,
        *,
        user_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> MasteryScore | None:
        result = await self.session.execute(
            select(MasteryScore).where(
                MasteryScore.user_id == user_id,
                MasteryScore.topic_id == topic_id,
                MasteryScore.kc_id.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_topic_map(
        self,
        topic_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Topic]:
        rows = await self.get_topics_by_ids(topic_ids)
        return {topic.id: topic for topic in rows}

    async def get_kc_name_map(
        self,
        kc_ids: list[uuid.UUID],
    ) -> dict[str, str]:
        if not kc_ids:
            return {}
        result = await self.session.execute(
            select(KnowledgeComponent).where(KnowledgeComponent.id.in_(kc_ids))
        )
        return {str(kc.id): kc.name for kc in result.scalars().all()}
