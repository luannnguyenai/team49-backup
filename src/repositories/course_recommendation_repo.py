"""
repositories/course_recommendation_repo.py
------------------------------------------
Data access for personalized course recommendations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course import Course, CourseRecommendation
from src.repositories.base import BaseRepository


class CourseRecommendationRepository(BaseRepository[CourseRecommendation]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, CourseRecommendation)

    async def get_recommended_slugs_for_user(self, user_id: UUID) -> set[str]:
        result = await self.session.execute(
            select(Course.slug)
            .join(CourseRecommendation, CourseRecommendation.course_id == Course.id)
            .where(CourseRecommendation.user_id == user_id)
            .order_by(CourseRecommendation.rank)
        )
        return {row[0] for row in result.all()}

    async def get_slugs_by_course_ids(self, course_ids: list[str | UUID]) -> set[str]:
        if not course_ids:
            return set()

        uuid_candidates: list[UUID] = []
        canonical_candidates: list[str] = []
        for course_id in course_ids:
            if isinstance(course_id, UUID):
                uuid_candidates.append(course_id)
                continue

            normalized = str(course_id).strip()
            if not normalized:
                continue

            try:
                uuid_candidates.append(UUID(normalized))
                continue
            except ValueError:
                canonical_candidates.append(normalized.lower())

        filters = []
        if uuid_candidates:
            filters.append(Course.id.in_(uuid_candidates))
        if canonical_candidates:
            filters.append(func.lower(Course.canonical_course_id).in_(canonical_candidates))
            filters.append(func.lower(Course.slug).in_(canonical_candidates))

        if not filters:
            return set()

        result = await self.session.execute(
            select(Course.slug).where(or_(*filters))
        )
        return {row[0] for row in result.all()}

    async def delete_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            delete(CourseRecommendation).where(CourseRecommendation.user_id == user_id)
        )
