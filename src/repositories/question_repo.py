"""
repositories/question_repo.py
------------------------------
Data access for Question, aggregating interaction history for tier selection.
"""

import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import RECENT_ASSESSMENT_LOOKBACK
from src.models.content import BloomLevel, DifficultyBucket, Question, QuestionStatus
from src.models.learning import Interaction, Session, SessionType
from src.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Question)

    async def get_pool_by_difficulty(
        self,
        topic_id: UUID,
        difficulty: DifficultyBucket,
        usage_context: str,
    ) -> list[Question]:
        """Active questions for topic + difficulty that include the usage_context."""
        result = await self.session.execute(
            select(Question).where(
                Question.topic_id == topic_id,
                Question.difficulty_bucket == difficulty,
                Question.status == QuestionStatus.active,
            )
        )
        questions = result.scalars().all()
        # Filter by usage_context (JSON array field)
        return [
            q for q in questions
            if q.usage_context is None or usage_context in q.usage_context
        ]

    async def get_pool_by_bloom(
        self,
        topic_id: UUID,
        bloom_levels: list[BloomLevel],
        excluded_ids: set[UUID],
        ability: float,
        limit: int,
    ) -> list[Question]:
        """IRT-ordered candidates for assessment — 2PL information function ordering."""
        result = await self.session.execute(
            select(Question).where(
                Question.topic_id == topic_id,
                Question.bloom_level.in_(bloom_levels),
                Question.status == QuestionStatus.active,
                Question.id.notin_(excluded_ids) if excluded_ids else True,
            )
        )
        candidates = result.scalars().all()
        # Sort by 2PL information: I(θ) ∝ a²·P(1-P), higher = better discrimination at ability
        return sorted(candidates, key=lambda q: _irt_information(q, ability), reverse=True)[:limit]

    async def get_interaction_map(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> dict[UUID, bool]:
        """Return {question_id: ever_wrong} for questions user has attempted in topic."""
        result = await self.session.execute(
            select(Interaction.question_id, func.bool_or(~Interaction.is_correct).label("ever_wrong"))
            .join(Question, Interaction.question_id == Question.id)
            .where(
                Interaction.user_id == user_id,
                Question.topic_id == topic_id,
            )
            .group_by(Interaction.question_id)
        )
        return {row.question_id: row.ever_wrong for row in result}

    async def get_recent_assessment_ids(
        self,
        user_id: UUID,
        lookback: int = RECENT_ASSESSMENT_LOOKBACK,
    ) -> set[UUID]:
        """Question IDs from the last N assessment sessions for this user."""
        # Get IDs of the last N assessment sessions
        session_result = await self.session.execute(
            select(Session.id)
            .where(
                Session.user_id == user_id,
                Session.session_type == SessionType.assessment,
                Session.completed_at.isnot(None),
            )
            .order_by(Session.completed_at.desc())
            .limit(lookback)
        )
        session_ids = [row[0] for row in session_result]

        if not session_ids:
            return set()

        q_result = await self.session.execute(
            select(Interaction.question_id).where(
                Interaction.session_id.in_(session_ids)
            )
        )
        return {row[0] for row in q_result}


def _irt_information(q: Question, ability: float) -> float:
    """2PL item information at given ability level."""
    a = q.irt_discrimination or 1.0
    b = q.irt_difficulty or 0.0
    p = 1.0 / (1.0 + math.exp(-a * (ability - b)))
    return a * a * p * (1.0 - p)
