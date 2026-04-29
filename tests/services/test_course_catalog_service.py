from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import src.database as database
from src.services import course_catalog_service


@pytest.mark.asyncio
async def test_list_course_catalog_recommended_falls_back_to_goal_preference_course_ids(monkeypatch):
    user_id = uuid4()
    fallback_course_id = str(uuid4())
    rows = [
        {
            "id": fallback_course_id,
            "slug": "cs231n",
            "title": "CS231n",
            "short_description": "Vision",
            "status": "ready",
            "cover_image_url": None,
            "hero_badge": None,
        },
        {
            "id": str(uuid4()),
            "slug": "cs224n",
            "title": "CS224n",
            "short_description": "NLP",
            "status": "ready",
            "cover_image_url": None,
            "hero_badge": None,
        },
    ]

    monkeypatch.setattr(course_catalog_service, "_list_catalog_from_db", AsyncMock(return_value=rows))
    monkeypatch.setattr(course_catalog_service, "_get_course_progress_percents", AsyncMock(return_value={}))
    monkeypatch.setattr(
        course_catalog_service,
        "_get_recommended_course_slugs",
        AsyncMock(return_value={"cs231n"}),
    )

    response = await course_catalog_service.list_course_catalog(
        view="recommended",
        include_unavailable=True,
        user=SimpleNamespace(id=user_id),
    )

    assert [item.slug for item in response.items] == ["cs231n"]
    assert all(item.is_recommended for item in response.items)


@pytest.mark.asyncio
async def test_list_course_catalog_all_annotates_recommended_flags_from_shared_resolver(monkeypatch):
    user_id = uuid4()
    rows = [
        {
            "id": str(uuid4()),
            "slug": "cs231n",
            "title": "CS231n",
            "short_description": "Vision",
            "status": "ready",
            "cover_image_url": None,
            "hero_badge": None,
        },
        {
            "id": str(uuid4()),
            "slug": "cs224n",
            "title": "CS224n",
            "short_description": "NLP",
            "status": "ready",
            "cover_image_url": None,
            "hero_badge": None,
        },
    ]

    monkeypatch.setattr(course_catalog_service, "_list_catalog_from_db", AsyncMock(return_value=rows))
    monkeypatch.setattr(course_catalog_service, "_get_course_progress_percents", AsyncMock(return_value={}))
    monkeypatch.setattr(
        course_catalog_service,
        "_get_recommended_course_slugs",
        AsyncMock(return_value={"cs224n"}),
    )

    response = await course_catalog_service.list_course_catalog(
        view="all",
        include_unavailable=True,
        user=SimpleNamespace(id=user_id),
    )

    flags = {item.slug: item.is_recommended for item in response.items}
    assert flags == {"cs231n": False, "cs224n": True}


@pytest.mark.asyncio
async def test_get_recommended_course_slugs_falls_back_from_goal_preference_course_ids(monkeypatch):
    user_id = uuid4()
    goal_course_id = str(uuid4())

    class FakeSessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeRecommendationRepo:
        def __init__(self, session):
            self.session = session

        async def get_recommended_slugs_for_user(self, requested_user_id):
            assert requested_user_id == user_id
            return set()

        async def get_slugs_by_course_ids(self, course_ids):
            assert course_ids == [goal_course_id]
            return {"cs231n"}

    class FakeGoalPreferenceRepo:
        def __init__(self, session):
            self.session = session

        async def get_by_user_id(self, requested_user_id):
            assert requested_user_id == user_id
            return SimpleNamespace(selected_course_ids=[goal_course_id])

    monkeypatch.setattr(database, "async_session_factory", lambda: FakeSessionContext())
    monkeypatch.setattr(
        course_catalog_service,
        "CourseRecommendationRepository",
        FakeRecommendationRepo,
    )
    monkeypatch.setattr(
        course_catalog_service,
        "GoalPreferenceRepository",
        FakeGoalPreferenceRepo,
        raising=False,
    )

    result = await course_catalog_service._get_recommended_course_slugs(user_id)

    assert result == {"cs231n"}
