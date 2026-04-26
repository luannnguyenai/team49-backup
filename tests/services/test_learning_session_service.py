from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.course import LearningProgressStatus
from src.services import learning_session_service


@pytest.mark.asyncio
async def test_get_resume_state_classifies_existing_planner_state(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    now = datetime(2026, 4, 24, tzinfo=UTC)

    class FakePlannerAuditRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == "canonical-learning-path"
            return SimpleNamespace(
                current_unit_id=unit_id,
                current_stage="watching",
                current_progress={"video_progress_s": 522},
                last_activity=now - timedelta(days=14),
            )

    monkeypatch.setattr(
        learning_session_service,
        "PlannerAuditRepository",
        FakePlannerAuditRepository,
    )

    result = await learning_session_service.get_resume_state("db-session", user_id, now=now)

    assert result.resume_route == "quick_review_check"
    assert result.current_unit_id == unit_id
    assert result.current_stage == "watching"
    assert result.current_progress == {"video_progress_s": 522}


@pytest.mark.asyncio
async def test_update_learning_unit_progress_persists_progress_and_session_pointer(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            assert unit_ids == [unit_id]
            return {
                unit_id: SimpleNamespace(
                    id=unit_id,
                    course_id=course_id,
                )
            }

    class FakeLearningProgressRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            FakeLearningProgressRepository.payload = payload
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def upsert_session_state(self, **payload):
            FakePlannerAuditRepository.payload = payload
            return SimpleNamespace(**payload)

    monkeypatch.setattr(
        learning_session_service,
        "CanonicalContentRepository",
        FakeCanonicalContentRepository,
    )
    monkeypatch.setattr(
        learning_session_service,
        "LearningProgressRepository",
        FakeLearningProgressRepository,
    )
    monkeypatch.setattr(
        learning_session_service,
        "PlannerAuditRepository",
        FakePlannerAuditRepository,
    )

    result = await learning_session_service.update_learning_unit_progress(
        "db-session",
        user_id=user_id,
        learning_unit_id=unit_id,
        video_progress_s=522.0,
        video_finished=False,
    )

    assert result.current_stage == "watching"
    assert FakeLearningProgressRepository.payload["status"] == LearningProgressStatus.in_progress
    assert FakeLearningProgressRepository.payload["last_position_seconds"] == 522.0
    assert FakePlannerAuditRepository.payload["current_unit_id"] == unit_id
    assert FakePlannerAuditRepository.payload["current_progress"]["video_progress_s"] == 522.0
