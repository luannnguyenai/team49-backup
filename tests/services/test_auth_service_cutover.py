import uuid
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from src.models.user import PreferredMethod, User
from src.schemas.auth import OnboardingRequest


@pytest.mark.asyncio
async def test_update_onboarding_writes_goal_preferences_when_flag_enabled(monkeypatch):
    from src.services import auth_service

    user = User(
        email=f"{uuid.uuid4()}@example.com",
        full_name="Onboarding User",
        hashed_password="hashed",
    )
    db = AsyncMock()
    db.add = Mock()

    captured = {}

    class FakeGoalPreferenceRepository:
        def __init__(self, session):
            assert session is db

        async def upsert_for_user(self, **kwargs):
            captured.update(kwargs)
            return Mock()

    monkeypatch.setattr(auth_service.settings, "write_goal_preferences_enabled", True)
    monkeypatch.setattr(auth_service, "GoalPreferenceRepository", FakeGoalPreferenceRepository)

    payload = OnboardingRequest(
        known_topic_ids=[uuid.uuid4()],
        desired_module_ids=[uuid.uuid4(), uuid.uuid4()],
        available_hours_per_week=6.5,
        target_deadline=date(2026, 6, 1),
        preferred_method=PreferredMethod.video,
    )

    result = await auth_service.update_onboarding(db, user, payload)

    assert result.is_onboarded is True
    assert captured["user_id"] == user.id
    assert captured["selected_course_ids"] is None
    assert captured["goal_weights_json"]["available_hours_per_week"] == 6.5
    assert captured["goal_weights_json"]["preferred_method"] == "video"
    assert captured["goal_weights_json"]["legacy_desired_module_count"] == 2
    assert "legacy_desired_module_ids" in captured["notes"]


@pytest.mark.asyncio
async def test_update_onboarding_skips_goal_preferences_when_flag_disabled(monkeypatch):
    from src.services import auth_service

    user = User(
        email=f"{uuid.uuid4()}@example.com",
        full_name="Onboarding User",
        hashed_password="hashed",
    )
    db = AsyncMock()
    db.add = Mock()

    class FakeGoalPreferenceRepository:
        def __init__(self, session):
            raise AssertionError("GoalPreferenceRepository should not be used when flag is off")

    monkeypatch.setattr(auth_service.settings, "write_goal_preferences_enabled", False)
    monkeypatch.setattr(auth_service, "GoalPreferenceRepository", FakeGoalPreferenceRepository)

    payload = OnboardingRequest(
        known_topic_ids=[],
        desired_module_ids=[],
        available_hours_per_week=4,
        target_deadline=date(2026, 6, 1),
        preferred_method=PreferredMethod.reading,
    )

    result = await auth_service.update_onboarding(db, user, payload)

    assert result.is_onboarded is True
