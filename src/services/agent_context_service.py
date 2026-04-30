from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.learning import GoalPreference
from src.models.user import User
from src.repositories.canonical_content_repo import CanonicalContentRepository


DEFAULT_AGENT_COURSES = ["CS230", "CS231n", "CS224n"]


@dataclass(frozen=True)
class AgentUserContext:
    user_id: str
    allowed_course_ids: list[str]
    selected_path_course_ids: list[str]


class AgentContextResolver:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CanonicalContentRepository(session)

    async def resolve(self, user: User) -> AgentUserContext:
        selected_course_ids: list[str] = []
        result = await self.session.execute(
            select(GoalPreference).where(GoalPreference.user_id == user.id).limit(1)
        )
        preference = result.scalar_one_or_none()
        if preference and preference.selected_course_ids:
            selected_course_ids = [str(course_id) for course_id in preference.selected_course_ids]

        if not selected_course_ids:
            selected_course_ids = DEFAULT_AGENT_COURSES[:2]

        allowed = sorted({*DEFAULT_AGENT_COURSES, *selected_course_ids})
        return AgentUserContext(
            user_id=str(user.id),
            allowed_course_ids=allowed,
            selected_path_course_ids=selected_course_ids,
        )
