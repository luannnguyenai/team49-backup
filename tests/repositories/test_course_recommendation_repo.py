"""
tests/repositories/test_course_recommendation_repo.py
-----------------------------------------------------
RED phase: CourseRecommendationRepository — personalized catalog data access.
"""

import pytest
from unittest.mock import AsyncMock, Mock


@pytest.mark.asyncio
async def test_course_recommendation_repo_importable():
    from src.repositories.course_recommendation_repo import CourseRecommendationRepository  # noqa


@pytest.mark.asyncio
async def test_get_recommended_slugs_for_user_returns_empty_set_for_new_user():
    from src.repositories.course_recommendation_repo import CourseRecommendationRepository

    session = AsyncMock()
    result = Mock()
    result.all.return_value = []
    session.execute.return_value = result

    repo = CourseRecommendationRepository(session)
    result = await repo.get_recommended_slugs_for_user("user-1")

    assert result == set()


@pytest.mark.asyncio
async def test_get_recommended_slugs_for_user_returns_ranked_course_slugs():
    from src.repositories.course_recommendation_repo import CourseRecommendationRepository

    session = AsyncMock()
    result = Mock()
    result.all.return_value = [("cs231n",), ("cs224n",)]
    session.execute.return_value = result

    repo = CourseRecommendationRepository(session)
    result = await repo.get_recommended_slugs_for_user("user-1")

    assert result == {"cs231n", "cs224n"}
