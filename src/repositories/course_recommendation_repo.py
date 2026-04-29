"""
repositories/course_recommendation_repo.py
------------------------------------------
Data access for personalized course recommendations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
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

        result = await self.session.execute(
            select(Course.slug).where(Course.id.in_(course_ids))
        )
        return {row[0] for row in result.all()}

    async def delete_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            delete(CourseRecommendation).where(CourseRecommendation.user_id == user_id)
        )
