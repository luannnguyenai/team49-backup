from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.exceptions import ForbiddenError
from src.models.course import LearningProgressStatus
from src.models.learning import PathAction, PathStatus
from src.schemas.learning_path import PathItemResponse
from src.services import recommendation_engine


@pytest.mark.asyncio
async def test_generate_learning_path_uses_canonical_branch(monkeypatch):
    captured = {}

    async def fake_generate_canonical_path(db, user, request):
        captured["called"] = True
        return "canonical-response"

    monkeypatch.setattr(recommendation_engine, "_generate_canonical_learning_path", fake_generate_canonical_path)

    result = await recommendation_engine.generate_learning_path(object(), object(), object())

    assert result == "canonical-response"
    assert captured["called"] is True


def test_path_item_response_allows_canonical_unit_without_legacy_topic_fields():
    item = PathItemResponse(
        id=uuid4(),
        learning_unit_id=uuid4(),
        learning_unit_title="Unit 1",
        section_title="Section 1",
        action=PathAction.deep_practice,
        estimated_hours=0.5,
        order_index=0,
        week_number=None,
        status=PathStatus.pending,
        canonical_unit_id="local::lecture01::seg1",
    )

    assert item.learning_unit_title == "Unit 1"
    assert item.section_title == "Section 1"
    assert item.canonical_unit_id == "local::lecture01::seg1"


@pytest.mark.asyncio
async def test_get_learning_path_reads_latest_canonical_plan(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()

    class FakePlannerAuditRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_latest_plan_for_user(self, actual_user_id, *, trigger=None):
            assert actual_user_id == user_id
            assert trigger == "generate_canonical_learning_path"
            return SimpleNamespace(
                recommended_path_json=[
                    {
                        "learning_unit_id": str(unit_id),
                        "canonical_unit_id": "cs231n::u1",
                        "action": "deep_practice",
                        "estimated_hours": 0.5,
                        "order_index": 2,
                    }
                ]
            )

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, learning_unit_ids):
            assert learning_unit_ids == [unit_id]
            return {
                unit_id: SimpleNamespace(
                    id=unit_id,
                    title="Convolution Basics",
                    section_id=uuid4(),
                )
            }

        async def get_sections_by_ids(self, section_ids):
            return {section_ids[0]: SimpleNamespace(id=section_ids[0], title="CNN Section")}

    async def fake_status_map(*args, **kwargs):
        return {unit_id: PathStatus.completed}

    monkeypatch.setattr(recommendation_engine, "PlannerAuditRepository", FakePlannerAuditRepository)
    monkeypatch.setattr(recommendation_engine, "CanonicalContentRepository", FakeCanonicalContentRepository)
    monkeypatch.setattr(recommendation_engine, "_get_canonical_path_status_map", fake_status_map)

    rows = await recommendation_engine.get_learning_path("db-session", user_id)

    lp, learning_unit_title, section_title = rows[0]
    assert lp.id == unit_id
    assert lp.learning_unit_id == unit_id
    assert lp.canonical_unit_id == "cs231n::u1"
    assert lp.action == PathAction.deep_practice
    assert lp.status == PathStatus.completed
    assert learning_unit_title == "Convolution Basics"
    assert section_title == "CNN Section"


@pytest.mark.asyncio
async def test_get_learning_path_timeline_groups_canonical_non_skip_items(monkeypatch):
    user_id = uuid4()

    async def fake_get_rows(db, actual_user_id):
        assert db == "db-session"
        assert actual_user_id == user_id
        return [
            (
                SimpleNamespace(
                    action=PathAction.deep_practice,
                    week_number=None,
                    order_index=0,
                ),
                "Unit 1",
                "canonical_unit",
            ),
            (
                SimpleNamespace(
                    action=PathAction.skip,
                    week_number=None,
                    order_index=1,
                ),
                "Unit 2",
                "canonical_unit",
            ),
        ]

    monkeypatch.setattr(recommendation_engine, "_get_canonical_learning_path_rows", fake_get_rows)

    grouped = await recommendation_engine.get_learning_path_timeline("db-session", user_id)

    assert sorted(grouped) == [1]
    assert grouped[1][0][1] == "Unit 1"


@pytest.mark.asyncio
async def test_update_path_status_writes_progress_and_waive(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    now = datetime.now(UTC)

    class FakePlannerAuditRepository:
        session_state_payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_latest_plan_for_user(self, actual_user_id, *, trigger=None):
            assert actual_user_id == user_id
            assert trigger == "generate_canonical_learning_path"
            return SimpleNamespace(
                id=uuid4(),
                recommended_path_json=[{"learning_unit_id": str(unit_id)}],
            )

        async def upsert_session_state(self, **payload):
            FakePlannerAuditRepository.session_state_payload = payload
            return SimpleNamespace(**payload)

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, learning_unit_ids):
            assert learning_unit_ids == [unit_id]
            return {
                unit_id: SimpleNamespace(
                    id=unit_id,
                    course_id=course_id,
                    canonical_unit_id="cs231n::u1",
                )
            }

    class FakeLearningProgressRepository:
        upsert_payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            FakeLearningProgressRepository.upsert_payload = payload
            return SimpleNamespace(completed_at=None, last_opened_at=now)

    class FakeWaivedUnitRepository:
        upsert_payload = None
        deleted = None

        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            FakeWaivedUnitRepository.upsert_payload = payload
            return SimpleNamespace(**payload)

        async def delete_for_user_unit(self, actual_user_id, learning_unit_id):
            FakeWaivedUnitRepository.deleted = (actual_user_id, learning_unit_id)

    async def fake_build_waive_evidence(db, *, user_id, canonical_unit_id):
        assert db == "db-session"
        assert canonical_unit_id == "cs231n::u1"
        return 0.82, [{"type": "kp_mastery_snapshot", "kp_id": "kp-1"}]

    async def fake_latest_quiz_score_percent(db, *, user_id, learning_unit_id):
        assert db == "db-session"
        assert learning_unit_id == unit_id
        return 88.0

    monkeypatch.setattr(recommendation_engine, "PlannerAuditRepository", FakePlannerAuditRepository)
    monkeypatch.setattr(recommendation_engine, "CanonicalContentRepository", FakeCanonicalContentRepository)
    monkeypatch.setattr(recommendation_engine, "LearningProgressRepository", FakeLearningProgressRepository)
    monkeypatch.setattr(recommendation_engine, "WaivedUnitRepository", FakeWaivedUnitRepository)
    monkeypatch.setattr(recommendation_engine, "_build_waive_evidence", fake_build_waive_evidence)
    monkeypatch.setattr(
        recommendation_engine,
        "_latest_quiz_score_percent",
        fake_latest_quiz_score_percent,
    )

    result = await recommendation_engine.update_path_status(
        db="db-session",
        user_id=user_id,
        path_id=unit_id,
        new_status=PathStatus.skipped,
    )

    assert result.learning_unit_id == unit_id
    assert result.status == PathStatus.skipped
    assert FakeLearningProgressRepository.upsert_payload["status"] == LearningProgressStatus.skipped
    assert FakeWaivedUnitRepository.upsert_payload["mastery_lcb_at_waive"] == 0.82
    assert FakeWaivedUnitRepository.upsert_payload["skip_quiz_score"] == 88.0
    assert FakePlannerAuditRepository.session_state_payload is not None
    assert FakePlannerAuditRepository.session_state_payload["current_unit_id"] == unit_id
    assert FakePlannerAuditRepository.session_state_payload["current_stage"] == "between_units"
    assert FakePlannerAuditRepository.session_state_payload["current_progress"]["status"] == "skipped"
    assert FakePlannerAuditRepository.session_state_payload["last_activity"] is not None


@pytest.mark.asyncio
async def test_update_path_status_rejects_skip_without_mastery_or_skip_quiz(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()

    class FakePlannerAuditRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_latest_plan_for_user(self, actual_user_id, *, trigger=None):
            assert actual_user_id == user_id
            return SimpleNamespace(
                id=uuid4(),
                recommended_path_json=[{"learning_unit_id": str(unit_id)}],
            )

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, learning_unit_ids):
            return {
                unit_id: SimpleNamespace(
                    id=unit_id,
                    course_id=course_id,
                    canonical_unit_id="cs231n::u1",
                )
            }

    class FakeLearningProgressRepository:
        touched = False

        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            FakeLearningProgressRepository.touched = True

    class FakeWaivedUnitRepository:
        touched = False

        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            FakeWaivedUnitRepository.touched = True

        async def delete_for_user_unit(self, actual_user_id, learning_unit_id):
            FakeWaivedUnitRepository.touched = True

    async def fake_build_waive_evidence(db, *, user_id, canonical_unit_id):
        return 0.42, [{"type": "kp_mastery_snapshot", "kp_id": "kp-1"}]

    async def fake_latest_quiz_score_percent(db, *, user_id, learning_unit_id):
        return 70.0

    monkeypatch.setattr(recommendation_engine, "PlannerAuditRepository", FakePlannerAuditRepository)
    monkeypatch.setattr(recommendation_engine, "CanonicalContentRepository", FakeCanonicalContentRepository)
    monkeypatch.setattr(recommendation_engine, "LearningProgressRepository", FakeLearningProgressRepository)
    monkeypatch.setattr(recommendation_engine, "WaivedUnitRepository", FakeWaivedUnitRepository)
    monkeypatch.setattr(recommendation_engine, "_build_waive_evidence", fake_build_waive_evidence)
    monkeypatch.setattr(
        recommendation_engine,
        "_latest_quiz_score_percent",
        fake_latest_quiz_score_percent,
    )

    with pytest.raises(ForbiddenError):
        await recommendation_engine.update_path_status(
            db="db-session",
            user_id=user_id,
            path_id=unit_id,
            new_status=PathStatus.skipped,
        )

    assert FakeLearningProgressRepository.touched is False
    assert FakeWaivedUnitRepository.touched is False
