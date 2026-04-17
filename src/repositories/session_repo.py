"""
repositories/session_repo.py
-----------------------------
Data access for Session — active session lookup and completion tracking.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import Interaction, Session, SessionType
from src.models.content import Topic
from src.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Session)

    async def get_active(
        self,
        user_id: UUID,
        session_type: SessionType,
    ) -> Session | None:
        """Return the most recent incomplete session of the given type, or None."""
        result = await self.session.execute(
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.session_type == session_type,
                Session.completed_at.is_(None),
            )
            .order_by(Session.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_completed_topic_ids(
        self,
        user_id: UUID,
        module_id: UUID,
    ) -> set[UUID]:
        """Topic IDs where the user has at least one completed quiz session."""
        result = await self.session.execute(
            select(Session.topic_id)
            .join(Topic, Session.topic_id == Topic.id)
            .where(
                Session.user_id == user_id,
                Session.session_type == SessionType.quiz,
                Session.completed_at.isnot(None),
                Topic.module_id == module_id,
            )
            .distinct()
        )
        return {row[0] for row in result if row[0] is not None}

    async def count_completed_quizzes_per_topic(
        self,
        user_id: UUID,
        topic_ids: list[UUID],
    ) -> dict[UUID, int]:
        """Return {topic_id: completed_quiz_count} for each topic in the list."""
        if not topic_ids:
            return {}
        result = await self.session.execute(
            select(Session.topic_id, func.count(Session.id).label("cnt"))
            .where(
                Session.user_id == user_id,
                Session.session_type == SessionType.quiz,
                Session.completed_at.isnot(None),
                Session.topic_id.in_(topic_ids),
            )
            .group_by(Session.topic_id)
        )
        counts = {row.topic_id: row.cnt for row in result}
        return counts
