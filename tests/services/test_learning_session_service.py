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

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == learning_session_service.CANONICAL_SESSION_ID
            return None

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


@pytest.mark.asyncio
async def test_update_learning_unit_progress_merges_inline_quiz_into_existing_progress(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    existing_progress = {
        "learning_unit_id": str(unit_id),
        "video_progress_s": 300.0,
        "inline_quiz": {
            "midpoint": {
                "shown": True,
                "active_session_id": str(uuid4()),
                "completed_session_id": None,
                "excluded_item_ids": ["item-a"],
                "item_ids": ["item-a", "item-b"],
                "answered_item_ids": ["item-a"],
            }
        },
        "preserved_flag": True,
    }

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
        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == learning_session_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=existing_progress)

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
        watch_percent=0.75,
        inline_quiz={
            "midpoint": {
                "completed_session_id": str(uuid4()),
                "active_session_id": None,
                "answered_item_ids": ["item-a", "item-b"],
            },
            "end": {
                "shown": True,
                "active_session_id": str(uuid4()),
                "completed_session_id": None,
                "excluded_item_ids": ["item-x"],
            },
        },
    )

    assert result.current_stage == "quiz_in_progress"
    assert result.current_progress["video_progress_s"] == 522.0
    assert result.current_progress["watch_percent"] == 0.75
    assert result.current_progress["preserved_flag"] is True
    assert result.current_progress["inline_quiz"]["midpoint"]["shown"] is True
    assert result.current_progress["inline_quiz"]["midpoint"]["excluded_item_ids"] == ["item-a"]
    assert result.current_progress["inline_quiz"]["midpoint"]["active_session_id"] is None
    assert result.current_progress["inline_quiz"]["midpoint"]["completed_session_id"] is not None
    assert result.current_progress["inline_quiz"]["midpoint"]["answered_item_ids"] == [
        "item-a",
        "item-b",
    ]
    assert result.current_progress["inline_quiz"]["end"]["shown"] is True
    assert result.current_progress["inline_quiz"]["end"]["active_session_id"] is not None
    assert result.current_progress["inline_quiz"]["end"]["excluded_item_ids"] == ["item-x"]


@pytest.mark.asyncio
async def test_update_learning_unit_progress_ignores_malformed_inline_quiz_checkpoint_payloads(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    existing_progress = {
        "learning_unit_id": str(unit_id),
        "inline_quiz": {
            "midpoint": {
                "shown": True,
                "active_session_id": str(uuid4()),
                "completed_session_id": None,
                "excluded_item_ids": ["item-a"],
            }
        },
    }

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            assert unit_ids == [unit_id]
            return {unit_id: SimpleNamespace(id=unit_id, course_id=course_id)}

    class FakeLearningProgressRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == learning_session_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=existing_progress)

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
        video_progress_s=120.0,
        video_finished=False,
        inline_quiz={
            "midpoint": "bad-payload",
            "end": {"shown": True, "active_session_id": str(uuid4())},
            "bonus": {"shown": True},
        },
    )

    assert result.current_stage == "quiz_in_progress"
    assert result.current_progress["inline_quiz"]["midpoint"]["excluded_item_ids"] == ["item-a"]
    assert result.current_progress["inline_quiz"]["midpoint"]["active_session_id"] is not None
    assert result.current_progress["inline_quiz"]["end"]["shown"] is True
    assert "bonus" not in result.current_progress["inline_quiz"]


@pytest.mark.asyncio
async def test_update_learning_unit_progress_keeps_watching_when_video_finished_without_completed_end_quiz(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    existing_progress = {
        "learning_unit_id": str(unit_id),
        "inline_quiz": {
            "midpoint": {
                "shown": True,
                "active_session_id": None,
                "completed_session_id": str(uuid4()),
            }
        },
    }

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            return {unit_id: SimpleNamespace(id=unit_id, course_id=course_id)}

    class FakeLearningProgressRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            return SimpleNamespace(current_progress=existing_progress)

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
        video_progress_s=600.0,
        video_finished=True,
    )

    assert result.current_stage == "watching"


@pytest.mark.asyncio
async def test_update_learning_unit_progress_treats_completed_end_quiz_runtime_state_as_lesson_complete(
    monkeypatch,
):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    existing_progress = {
        "learning_unit_id": str(unit_id),
        "inline_quiz": {
            "end": {
                "shown": True,
                "active_session_id": None,
                "completed_session_id": str(uuid4()),
            }
        },
    }

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            assert unit_ids == [unit_id]
            return {unit_id: SimpleNamespace(id=unit_id, course_id=course_id)}

    class FakeLearningProgressRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_for_user_unit(self, actual_user_id, actual_learning_unit_id):
            assert actual_user_id == user_id
            assert actual_learning_unit_id == unit_id
            return None

        async def upsert(self, **payload):
            FakeLearningProgressRepository.payload = payload
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == learning_session_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=existing_progress)

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
        video_progress_s=420.0,
        video_finished=False,
        watch_percent=0.71,
    )

    assert result.current_stage == "post_quiz"
    assert FakeLearningProgressRepository.payload["status"] == LearningProgressStatus.completed
    assert FakeLearningProgressRepository.payload["completed_at"] is not None


@pytest.mark.asyncio
async def test_update_learning_unit_progress_ignores_completed_end_quiz_runtime_state_from_different_unit(
    monkeypatch,
):
    user_id = uuid4()
    completed_unit_id = uuid4()
    current_unit_id = uuid4()
    course_id = uuid4()
    existing_progress = {
        "learning_unit_id": str(completed_unit_id),
        "quiz_id": str(uuid4()),
        "quiz_phase": "inline_end_quiz",
        "items_answered": ["item-a"],
        "items_remaining": ["item-b"],
        "score_percent": 88.0,
        "completed_at": "2026-04-20T00:00:00+00:00",
        "inline_quiz": {
            "end": {
                "shown": True,
                "active_session_id": None,
                "completed_session_id": str(uuid4()),
            }
        },
    }

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            assert unit_ids == [current_unit_id]
            return {current_unit_id: SimpleNamespace(id=current_unit_id, course_id=course_id)}

    class FakeLearningProgressRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_for_user_unit(self, actual_user_id, actual_learning_unit_id):
            assert actual_user_id == user_id
            assert actual_learning_unit_id == current_unit_id
            return None

        async def upsert(self, **payload):
            FakeLearningProgressRepository.payload = payload
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == learning_session_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=existing_progress)

        async def upsert_session_state(self, **payload):
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
        learning_unit_id=current_unit_id,
        video_progress_s=180.0,
        video_finished=False,
    )

    assert result.current_stage == "watching"
    assert FakeLearningProgressRepository.payload["status"] == LearningProgressStatus.in_progress
    assert FakeLearningProgressRepository.payload["completed_at"] is None
    assert result.current_progress == {
        "learning_unit_id": str(current_unit_id),
        "video_progress_s": 180.0,
        "video_finished": False,
    }


@pytest.mark.asyncio
async def test_update_learning_unit_progress_preserves_existing_completed_at_after_final_quiz_completion(
    monkeypatch,
):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    original_completed_at = datetime(2026, 4, 20, tzinfo=UTC)
    existing_progress = {
        "learning_unit_id": str(unit_id),
        "inline_quiz": {
            "end": {
                "shown": True,
                "active_session_id": None,
                "completed_session_id": str(uuid4()),
            }
        },
    }

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            assert unit_ids == [unit_id]
            return {unit_id: SimpleNamespace(id=unit_id, course_id=course_id)}

    class FakeLearningProgressRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_for_user_unit(self, actual_user_id, actual_learning_unit_id):
            assert actual_user_id == user_id
            assert actual_learning_unit_id == unit_id
            return SimpleNamespace(completed_at=original_completed_at)

        async def upsert(self, **payload):
            FakeLearningProgressRepository.payload = payload
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == learning_session_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=existing_progress)

        async def upsert_session_state(self, **payload):
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
        video_progress_s=510.0,
        video_finished=False,
    )

    assert result.current_stage == "post_quiz"
    assert FakeLearningProgressRepository.payload["status"] == LearningProgressStatus.completed
    assert FakeLearningProgressRepository.payload["completed_at"] == original_completed_at


@pytest.mark.asyncio
async def test_update_learning_unit_progress_preserves_completed_progress_row_without_runtime_end_quiz_state(
    monkeypatch,
):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    original_completed_at = datetime(2026, 4, 21, tzinfo=UTC)
    existing_progress = {
        "learning_unit_id": str(unit_id),
        "video_progress_s": 120.0,
        "inline_quiz": "malformed-inline-state",
    }

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            assert unit_ids == [unit_id]
            return {unit_id: SimpleNamespace(id=unit_id, course_id=course_id)}

    class FakeLearningProgressRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_for_user_unit(self, actual_user_id, actual_learning_unit_id):
            assert actual_user_id == user_id
            assert actual_learning_unit_id == unit_id
            return SimpleNamespace(
                status=LearningProgressStatus.completed,
                completed_at=original_completed_at,
            )

        async def upsert(self, **payload):
            FakeLearningProgressRepository.payload = payload
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == learning_session_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=existing_progress)

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
        video_progress_s=240.0,
        video_finished=False,
    )

    assert result.current_stage == "post_quiz"
    assert FakeLearningProgressRepository.payload["status"] == LearningProgressStatus.completed
    assert FakeLearningProgressRepository.payload["completed_at"] == original_completed_at
    assert result.current_progress["learning_unit_id"] == str(unit_id)
    assert result.current_progress["video_progress_s"] == 240.0
    assert result.current_progress["video_finished"] is False
