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

    selected_course_ids = ["course_cs224n", "course_cs231n"]
    payload = OnboardingRequest(
        known_unit_ids=[uuid.uuid4()],
        desired_section_ids=[uuid.uuid4(), uuid.uuid4()],
        selected_course_ids=selected_course_ids,
        available_hours_per_week=6.5,
        target_deadline=date(2026, 6, 1),
        preferred_method=PreferredMethod.video,
    )

    result = await auth_service.update_onboarding(db, user, payload)

    assert result.is_onboarded is True
    assert captured["user_id"] == user.id
    assert captured["selected_course_ids"] == selected_course_ids
    assert captured["goal_weights_json"]["available_hours_per_week"] == 6.5
    assert captured["goal_weights_json"]["preferred_method"] == "video"
    assert captured["goal_weights_json"]["desired_section_count"] == 2
    assert captured["goal_weights_json"]["known_unit_count"] == 1
    assert "desired_section_ids" in captured["notes"]
    assert "legacy_desired_module_ids" not in captured["notes"]


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
        known_unit_ids=[],
        desired_section_ids=[],
        selected_course_ids=[],
        available_hours_per_week=4,
        target_deadline=date(2026, 6, 1),
        preferred_method=PreferredMethod.reading,
    )

    result = await auth_service.update_onboarding(db, user, payload)

    assert result.is_onboarded is True


def test_onboarding_request_accepts_legacy_aliases_temporarily():
    known_unit_id = uuid.uuid4()
    desired_section_id = uuid.uuid4()

    payload = OnboardingRequest(
        known_topic_ids=[known_unit_id],
        desired_module_ids=[desired_section_id],
        available_hours_per_week=4,
        target_deadline=date(2026, 6, 1),
        preferred_method=PreferredMethod.reading,
    )

    assert payload.known_unit_ids == [known_unit_id]
    assert payload.desired_section_ids == [desired_section_id]
