from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.exceptions import ConflictError, ValidationError
from src.models.course import LearningProgressStatus
from src.models.learning import SessionType
from src.services import quiz_service


class FakeDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        self.added.append(obj)

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None


def _item(item_id: str, difficulty: str = "medium"):
    return SimpleNamespace(
        item_id=item_id,
        difficulty=difficulty,
        question_intent="conceptual",
        question=f"Question {item_id}",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        explanation=None,
    )


@pytest.mark.asyncio
async def test_start_quiz_inline_midpoint_sets_metadata_and_excludes_items(monkeypatch):
    db = FakeDB()
    user_id = uuid4()
    learning_unit_id = uuid4()
    canonical_unit_id = "canonical-unit-1"
    sync_calls = []

    async def fake_get_learning_unit_or_404(db_arg, actual_learning_unit_id):
        assert db_arg is db
        assert actual_learning_unit_id == learning_unit_id
        return SimpleNamespace(id=learning_unit_id, canonical_unit_id=canonical_unit_id)

    class FakePlannerAuditRepository:
        def __init__(self, db_arg):
            assert db_arg is db

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == quiz_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=None)

    class FakeSelector:
        def __init__(self, repo):
            async def fake_get_items_for_phase(*, phase, canonical_unit_ids, limit, kp_ids=None):
                assert phase == "mini_quiz"
                assert canonical_unit_ids == [canonical_unit_id]
                assert limit >= 3
                return [
                    _item("item-a", "easy"),
                    _item("item-b", "medium"),
                    _item("item-c", "hard"),
                    _item("item-d", "medium"),
                ]

            self.repo = SimpleNamespace(get_items_for_phase=fake_get_items_for_phase)

        async def select_for_phase(self, *, phase, canonical_unit_ids, count):
            assert phase == "mini_quiz"
            assert canonical_unit_ids == [canonical_unit_id]
            assert count == 3
            return [_item("item-a", "easy"), _item("item-b", "medium"), _item("item-c", "hard")]

    async def fake_sync_quiz_progress_state(db_arg, **payload):
        assert db_arg is db
        sync_calls.append(payload)

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)
    monkeypatch.setattr(quiz_service, "PlannerAuditRepository", FakePlannerAuditRepository)
    monkeypatch.setattr(quiz_service, "CanonicalQuestionSelector", FakeSelector)
    monkeypatch.setattr(quiz_service, "_sync_quiz_progress_state", fake_sync_quiz_progress_state)

    result = await quiz_service.start_quiz(
        db,
        user_id,
        learning_unit_id,
        count=3,
        source="inline_video",
        checkpoint="midpoint",
        exclude_item_ids=["item-b"],
    )

    created_session = db.added[0]
    assert created_session.session_type == SessionType.quiz
    assert created_session.canonical_unit_id == learning_unit_id
    assert created_session.canonical_phase == "inline_midpoint_quiz"
    assert result.source == "inline_video"
    assert result.checkpoint == "midpoint"
    assert result.total_questions == 3
    assert [question.item_id for question in result.questions] == ["item-a", "item-c", "item-d"]
    assert sync_calls[0]["session_id"] == created_session.id
    assert sync_calls[0]["current_stage"] == "quiz_in_progress"
    assert sync_calls[0]["item_ids"] == ["item-a", "item-c", "item-d"]
    assert sync_calls[0]["checkpoint"] == "midpoint"


@pytest.mark.asyncio
async def test_start_quiz_inline_treats_malformed_progress_as_empty(monkeypatch):
    db = FakeDB()
    user_id = uuid4()
    learning_unit_id = uuid4()
    canonical_unit_id = "canonical-unit-1"
    sync_calls = []

    async def fake_get_learning_unit_or_404(db_arg, actual_learning_unit_id):
        assert db_arg is db
        assert actual_learning_unit_id == learning_unit_id
        return SimpleNamespace(id=learning_unit_id, canonical_unit_id=canonical_unit_id)

    class FakePlannerAuditRepository:
        def __init__(self, db_arg):
            assert db_arg is db

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == quiz_service.CANONICAL_SESSION_ID
            return SimpleNamespace(current_progress=None)

    class FakeSelector:
        def __init__(self, repo):
            self.repo = repo

        async def select_for_phase(self, *, phase, canonical_unit_ids, count):
            assert phase == "mini_quiz"
            assert canonical_unit_ids == [canonical_unit_id]
            assert count == 2
            return [_item("item-a", "easy"), _item("item-b", "medium")]

    def fake_inline_quiz_checkpoint_state(inline_quiz_state, checkpoint):
        assert inline_quiz_state == {}
        return {"active_session_id": str(uuid4())}

    async def fake_sync_quiz_progress_state(db_arg, **payload):
        assert db_arg is db
        sync_calls.append(payload)

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)
    monkeypatch.setattr(quiz_service, "PlannerAuditRepository", FakePlannerAuditRepository)
    monkeypatch.setattr(quiz_service, "CanonicalQuestionSelector", FakeSelector)
    monkeypatch.setattr(
        quiz_service,
        "_inline_quiz_checkpoint_state",
        fake_inline_quiz_checkpoint_state,
    )
    monkeypatch.setattr(quiz_service, "_sync_quiz_progress_state", fake_sync_quiz_progress_state)

    result = await quiz_service.start_quiz(
        db,
        user_id,
        learning_unit_id,
        count=2,
        source="inline_video",
        checkpoint="midpoint",
    )

    assert result.total_questions == 2
    assert [question.item_id for question in result.questions] == ["item-a", "item-b"]
    assert sync_calls[0]["checkpoint"] == "midpoint"


@pytest.mark.asyncio
async def test_start_quiz_reuses_active_inline_session_for_same_checkpoint(monkeypatch):
    db = FakeDB()
    user_id = uuid4()
    learning_unit_id = uuid4()
    existing_session_id = uuid4()
    existing_questions = [_item("item-a"), _item("item-b")]

    async def fake_get_learning_unit_or_404(db_arg, actual_learning_unit_id):
        assert db_arg is db
        assert actual_learning_unit_id == learning_unit_id
        return SimpleNamespace(id=learning_unit_id, canonical_unit_id="canonical-unit-1")

    class FakePlannerAuditRepository:
        def __init__(self, db_arg):
            assert db_arg is db

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == quiz_service.CANONICAL_SESSION_ID
            return SimpleNamespace(
                current_progress={
                    "learning_unit_id": str(learning_unit_id),
                    "inline_quiz": {
                        "midpoint": {
                            "shown": True,
                            "active_session_id": str(existing_session_id),
                            "completed_session_id": None,
                            "excluded_item_ids": ["item-z"],
                            "item_ids": ["item-a", "item-b"],
                            "answered_item_ids": ["item-a"],
                        }
                    },
                }
            )

    async def fake_get_existing_inline_quiz_session(db_arg, actual_user_id, actual_session_id):
        assert db_arg is db
        assert actual_user_id == user_id
        assert actual_session_id == existing_session_id
        return SimpleNamespace(
            id=existing_session_id,
            canonical_unit_id=learning_unit_id,
            completed_at=None,
            total_questions=2,
        )

    async def fake_get_quiz_items_by_ids(db_arg, unit, item_ids):
        assert db_arg is db
        assert unit.id == learning_unit_id
        assert item_ids == ["item-a", "item-b"]
        return existing_questions

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)
    monkeypatch.setattr(quiz_service, "PlannerAuditRepository", FakePlannerAuditRepository)
    monkeypatch.setattr(quiz_service, "_get_existing_inline_quiz_session", fake_get_existing_inline_quiz_session)
    monkeypatch.setattr(quiz_service, "_get_quiz_items_by_ids", fake_get_quiz_items_by_ids)

    result = await quiz_service.start_quiz(
        db,
        user_id,
        learning_unit_id,
        count=2,
        source="inline_video",
        checkpoint="midpoint",
    )

    assert not db.added
    assert result.session_id == existing_session_id
    assert result.total_questions == 2
    assert result.source == "inline_video"
    assert result.checkpoint == "midpoint"
    assert [question.item_id for question in result.questions] == ["item-a", "item-b"]


@pytest.mark.asyncio
async def test_start_quiz_blocks_end_checkpoint_while_midpoint_inline_quiz_is_in_progress(monkeypatch):
    db = FakeDB()
    user_id = uuid4()
    learning_unit_id = uuid4()

    async def fake_get_learning_unit_or_404(db_arg, actual_learning_unit_id):
        assert db_arg is db
        assert actual_learning_unit_id == learning_unit_id
        return SimpleNamespace(id=learning_unit_id, canonical_unit_id="canonical-unit-1")

    class FakePlannerAuditRepository:
        def __init__(self, db_arg):
            assert db_arg is db

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == quiz_service.CANONICAL_SESSION_ID
            return SimpleNamespace(
                current_progress={
                    "learning_unit_id": str(learning_unit_id),
                    "inline_quiz": {
                        "midpoint": {
                            "shown": True,
                            "active_session_id": str(uuid4()),
                            "completed_session_id": None,
                            "excluded_item_ids": [],
                            "item_ids": ["item-a", "item-b"],
                            "answered_item_ids": [],
                        }
                    },
                }
            )

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)
    monkeypatch.setattr(quiz_service, "PlannerAuditRepository", FakePlannerAuditRepository)

    with pytest.raises(ConflictError, match="midpoint"):
        await quiz_service.start_quiz(
            db,
            user_id,
            learning_unit_id,
            count=2,
            source="inline_video",
            checkpoint="end",
        )


@pytest.mark.asyncio
async def test_start_quiz_inline_end_uses_requested_count_and_nested_checkpoint_state(monkeypatch):
    db = FakeDB()
    user_id = uuid4()
    learning_unit_id = uuid4()
    canonical_unit_id = "canonical-unit-1"
    sync_calls = []

    async def fake_get_learning_unit_or_404(db_arg, actual_learning_unit_id):
        assert db_arg is db
        assert actual_learning_unit_id == learning_unit_id
        return SimpleNamespace(id=learning_unit_id, canonical_unit_id=canonical_unit_id)

    class FakePlannerAuditRepository:
        def __init__(self, db_arg):
            assert db_arg is db

        async def get_session_state(self, actual_user_id, session_id):
            assert actual_user_id == user_id
            assert session_id == quiz_service.CANONICAL_SESSION_ID
            return SimpleNamespace(
                current_progress={
                    "learning_unit_id": str(learning_unit_id),
                    "inline_quiz": {"midpoint": {"shown": True, "completed_session_id": str(uuid4())}},
                }
            )

    class FakeSelector:
        def __init__(self, repo):
            self.repo = repo

        async def select_for_phase(self, *, phase, canonical_unit_ids, count):
            assert phase == "mini_quiz"
            assert canonical_unit_ids == [canonical_unit_id]
            assert count == 5
            return [
                _item("item-a"),
                _item("item-b"),
                _item("item-c"),
                _item("item-d"),
                _item("item-e"),
            ]

    async def fake_sync_quiz_progress_state(db_arg, **payload):
        assert db_arg is db
        sync_calls.append(payload)

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)
    monkeypatch.setattr(quiz_service, "PlannerAuditRepository", FakePlannerAuditRepository)
    monkeypatch.setattr(quiz_service, "CanonicalQuestionSelector", FakeSelector)
    monkeypatch.setattr(quiz_service, "_sync_quiz_progress_state", fake_sync_quiz_progress_state)

    result = await quiz_service.start_quiz(
        db,
        user_id,
        learning_unit_id,
        count=5,
        source="inline_video",
        checkpoint="end",
    )

    created_session = db.added[0]
    assert created_session.canonical_phase == "inline_end_quiz"
    assert result.total_questions == 5
    assert result.checkpoint == "end"
    assert [question.item_id for question in result.questions] == [
        "item-a",
        "item-b",
        "item-c",
        "item-d",
        "item-e",
    ]
    assert sync_calls[0]["checkpoint"] == "end"
    assert sync_calls[0]["item_ids"] == ["item-a", "item-b", "item-c", "item-d", "item-e"]


@pytest.mark.asyncio
async def test_start_quiz_rejects_standalone_non_default_count(monkeypatch):
    async def fake_get_learning_unit_or_404(db_arg, actual_learning_unit_id):
        return SimpleNamespace(id=actual_learning_unit_id, canonical_unit_id="canonical-unit-1")

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)

    with pytest.raises(ValidationError, match="Standalone quiz"):
        await quiz_service.start_quiz(
            object(),
            uuid4(),
            uuid4(),
            count=3,
            source="standalone",
        )


@pytest.mark.asyncio
async def test_start_quiz_rejects_invalid_inline_checkpoint():
    with pytest.raises(ValidationError, match="Invalid inline quiz checkpoint"):
        await quiz_service.start_quiz(
            object(),
            uuid4(),
            uuid4(),
            source="inline_video",
            checkpoint="chapter_break",
        )


@pytest.mark.asyncio
async def test_complete_quiz_midpoint_does_not_complete_learning_unit(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    session = SimpleNamespace(
        id=uuid4(),
        canonical_unit_id=unit_id,
        canonical_phase="inline_midpoint_quiz",
        completed_at=None,
    )
    unit = SimpleNamespace(
        id=unit_id,
        course_id=uuid4(),
        title="Unit title",
        canonical_unit_id="canonical-unit-1",
    )
    rows = [
        (SimpleNamespace(is_correct=True, response_time_ms=1200), SimpleNamespace(item_id="item-a")),
        (SimpleNamespace(is_correct=False, response_time_ms=800), SimpleNamespace(item_id="item-b")),
    ]
    sync_calls = []

    class FakeDB:
        def __init__(self):
            self.added = []
            self.execute_calls = 0

        async def execute(self, stmt):
            self.execute_calls += 1
            if self.execute_calls == 1:
                return SimpleNamespace(all=lambda: rows)
            raise AssertionError("Unexpected execute call")

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    db = FakeDB()

    class FakeLearningProgressRepository:
        called = False

        def __init__(self, db_arg):
            assert db_arg is db

        async def upsert(self, **payload):
            FakeLearningProgressRepository.called = True
            return SimpleNamespace(**payload)

    class FakeWaivedUnitRepository:
        called = False

        def __init__(self, db_arg):
            assert db_arg is db

        async def delete_for_user_unit(self, actual_user_id, actual_unit_id):
            FakeWaivedUnitRepository.called = True

    async def fake_get_learning_unit_or_404(db_arg, learning_unit_id):
        assert db_arg is db
        assert learning_unit_id == unit_id
        return unit

    async def fake_mastery_percent(db_arg, actual_user_id, item_ids):
        assert db_arg is db
        assert actual_user_id == user_id
        return 50.0 if item_ids == ["item-a", "item-b"] else 0.0

    async def fake_update_kp_mastery_from_item(db_arg, **kwargs):
        return None

    async def fake_sync_quiz_progress_state(db_arg, **payload):
        assert db_arg is db
        sync_calls.append(payload)

    async def fake_canonical_kp_names(db_arg, item_ids):
        return ["KC-1"] if item_ids == ["item-b"] else []

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)
    monkeypatch.setattr(quiz_service, "_canonical_mastery_percent_for_items", fake_mastery_percent)
    monkeypatch.setattr(quiz_service, "update_kp_mastery_from_item", fake_update_kp_mastery_from_item)
    monkeypatch.setattr(quiz_service, "_sync_quiz_progress_state", fake_sync_quiz_progress_state)
    monkeypatch.setattr(quiz_service, "_canonical_kp_names", fake_canonical_kp_names)
    monkeypatch.setattr(quiz_service, "LearningProgressRepository", FakeLearningProgressRepository)
    monkeypatch.setattr(quiz_service, "WaivedUnitRepository", FakeWaivedUnitRepository)

    result = await quiz_service._complete_canonical_quiz(db, user_id, session)

    assert result.learning_path_updated is False
    assert FakeLearningProgressRepository.called is False
    assert FakeWaivedUnitRepository.called is False
    assert sync_calls[0]["current_stage"] == "watching"


@pytest.mark.asyncio
async def test_complete_quiz_end_marks_learning_unit_complete(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    session = SimpleNamespace(
        id=uuid4(),
        canonical_unit_id=unit_id,
        canonical_phase="inline_end_quiz",
        completed_at=None,
    )
    unit = SimpleNamespace(
        id=unit_id,
        course_id=uuid4(),
        title="Unit title",
        canonical_unit_id="canonical-unit-1",
    )
    rows = [
        (SimpleNamespace(is_correct=True, response_time_ms=1000), SimpleNamespace(item_id="item-a")),
    ]

    class FakeDB:
        def __init__(self):
            self.added = []
            self.execute_calls = 0

        async def execute(self, stmt):
            self.execute_calls += 1
            if self.execute_calls == 1:
                return SimpleNamespace(all=lambda: rows)
            raise AssertionError("Unexpected execute call")

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    db = FakeDB()

    class FakeLearningProgressRepository:
        payload = None

        def __init__(self, db_arg):
            assert db_arg is db

        async def upsert(self, **payload):
            FakeLearningProgressRepository.payload = payload
            return SimpleNamespace(**payload)

    class FakeWaivedUnitRepository:
        called = False

        def __init__(self, db_arg):
            assert db_arg is db

        async def delete_for_user_unit(self, actual_user_id, actual_unit_id):
            FakeWaivedUnitRepository.called = True

    async def fake_get_learning_unit_or_404(db_arg, learning_unit_id):
        return unit

    async def fake_mastery_percent(db_arg, actual_user_id, item_ids):
        return 80.0

    async def fake_update_kp_mastery_from_item(db_arg, **kwargs):
        return None

    async def fake_sync_quiz_progress_state(db_arg, **payload):
        return None

    async def fake_canonical_kp_names(db_arg, item_ids):
        return []

    monkeypatch.setattr(quiz_service, "_get_learning_unit_or_404", fake_get_learning_unit_or_404)
    monkeypatch.setattr(quiz_service, "_canonical_mastery_percent_for_items", fake_mastery_percent)
    monkeypatch.setattr(quiz_service, "update_kp_mastery_from_item", fake_update_kp_mastery_from_item)
    monkeypatch.setattr(quiz_service, "_sync_quiz_progress_state", fake_sync_quiz_progress_state)
    monkeypatch.setattr(quiz_service, "_canonical_kp_names", fake_canonical_kp_names)
    monkeypatch.setattr(quiz_service, "LearningProgressRepository", FakeLearningProgressRepository)
    monkeypatch.setattr(quiz_service, "WaivedUnitRepository", FakeWaivedUnitRepository)

    result = await quiz_service._complete_canonical_quiz(db, user_id, session)

    assert result.learning_path_updated is True
    assert FakeLearningProgressRepository.payload["status"] == LearningProgressStatus.completed
    assert FakeWaivedUnitRepository.called is True


@pytest.mark.parametrize(
    ("canonical_phase", "expected"),
    [
        ("inline_midpoint_quiz", False),
        ("inline_end_quiz", True),
        ("mini_quiz", True),
    ],
)
def test_should_complete_learning_unit_only_for_standalone_or_end_checkpoint(
    canonical_phase,
    expected,
):
    session = SimpleNamespace(canonical_phase=canonical_phase)

    assert quiz_service._should_complete_learning_unit(session) is expected
