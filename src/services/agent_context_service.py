from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import GoalPreference
from src.models.user import User
from src.repositories.canonical_content_repo import CanonicalContentRepository

DEFAULT_AGENT_COURSES = ["CS230", "CS231n", "CS224n"]
_CANONICAL_AGENT_COURSE_IDS = {
    course_id.casefold(): course_id for course_id in DEFAULT_AGENT_COURSES
}


def canonicalize_agent_course_ids(course_ids: list[str]) -> list[str]:
    canonicalized: list[str] = []
    seen: set[str] = set()
    for course_id in course_ids:
        normalized = _CANONICAL_AGENT_COURSE_IDS.get(str(course_id).casefold(), str(course_id))
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        canonicalized.append(normalized)
    return canonicalized


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
            selected_course_ids = canonicalize_agent_course_ids(
                [str(course_id) for course_id in preference.selected_course_ids]
            )

        if not selected_course_ids:
            selected_course_ids = DEFAULT_AGENT_COURSES[:2]

        allowed = canonicalize_agent_course_ids([*DEFAULT_AGENT_COURSES, *selected_course_ids])
        return AgentUserContext(
            user_id=str(user.id),
            allowed_course_ids=allowed,
            selected_path_course_ids=selected_course_ids,
        )
