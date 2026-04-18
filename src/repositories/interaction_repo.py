"""
repositories/interaction_repo.py
----------------------------------
Data access for Interaction — bulk creation and session retrieval.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.content import Question
from src.models.learning import Interaction
from src.repositories.base import BaseRepository


class InteractionRepository(BaseRepository[Interaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Interaction)

    async def bulk_create_placeholders(
        self,
        session_id: UUID,
        user_id: UUID,
        questions: list[Question],
    ) -> list[Interaction]:
        """Create placeholder Interaction rows (is_correct=False) for each question."""
        next_global = await self.get_next_global_sequence(user_id)
        interactions = []
        for i, q in enumerate(questions):
            obj = Interaction(
                session_id=session_id,
                user_id=user_id,
                question_id=q.id,
                sequence_position=i + 1,
                global_sequence_position=next_global + i,
                is_correct=False,
            )
            self.session.add(obj)
            interactions.append(obj)
        await self.session.flush()
        return interactions

    async def get_by_session(self, session_id: UUID) -> list[Interaction]:
        result = await self.session.execute(
            select(Interaction)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.sequence_position)
        )
        return list(result.scalars().all())

    async def get_next_global_sequence(self, user_id: UUID) -> int:
        """Return the next available global_sequence_position for this user."""
        result = await self.session.execute(
            select(func.max(Interaction.global_sequence_position)).where(
                Interaction.user_id == user_id
            )
        )
        max_pos = result.scalar_one_or_none()
        return (max_pos or 0) + 1
