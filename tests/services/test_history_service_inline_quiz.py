from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.learning import SelectedAnswer, SessionType
from src.services import history_service


def _make_session(*, canonical_phase: str | None):
    return SimpleNamespace(
        id=uuid4(),
        session_type=SessionType.quiz,
        started_at=history_service.datetime(2026, 4, 25, tzinfo=history_service.UTC),
        completed_at=history_service.datetime(2026, 4, 25, 0, 5, tzinfo=history_service.UTC),
        canonical_phase=canonical_phase,
        canonical_unit_id=uuid4(),
        topic_id=None,
        canonical_section_id=uuid4(),
        module_id=None,
        score_percent=66.7,
        correct_count=2,
        total_questions=3,
    )


@pytest.mark.asyncio
async def test_history_list_exposes_inline_quiz_source_and_checkpoint_from_canonical_phase(monkeypatch):
    session = _make_session(canonical_phase="inline_midpoint_quiz")

    class FakeRepo:
        async def count_sessions(self, *, filters):
            return 1

        async def fetch_history_page_canonical_only(self, *, filters, page, page_size):
            return [(session, "Backpropagation", "Optimization")]

        async def fetch_sessions_for_summary(self, *, filters):
            return [session]

    monkeypatch.setattr(history_service, "HistoryRepository", lambda db: FakeRepo())

    response = await history_service.get_history(object(), uuid4(), session_type=SessionType.quiz)

    assert response.items[0].source == "inline_video"
    assert response.items[0].checkpoint == "midpoint"


@pytest.mark.asyncio
async def test_history_list_preserves_non_inline_sessions_without_metadata(monkeypatch):
    session = _make_session(canonical_phase="mini_quiz")

    class FakeRepo:
        async def count_sessions(self, *, filters):
            return 1

        async def fetch_history_page_canonical_only(self, *, filters, page, page_size):
            return [(session, "Backpropagation", "Optimization")]

        async def fetch_sessions_for_summary(self, *, filters):
            return [session]

    monkeypatch.setattr(history_service, "HistoryRepository", lambda db: FakeRepo())

    response = await history_service.get_history(object(), uuid4(), session_type=SessionType.quiz)

    assert response.items[0].source is None
    assert response.items[0].checkpoint is None


@pytest.mark.asyncio
async def test_session_detail_exposes_inline_quiz_metadata_and_review_questions(monkeypatch):
    user_id = uuid4()
    session = _make_session(canonical_phase="inline_end_quiz")
    interaction = SimpleNamespace(
        canonical_item_id="item-1",
        sequence_position=1,
        selected_answer=SelectedAnswer.B,
        is_correct=True,
        response_time_ms=1200,
    )
    canonical_item = SimpleNamespace(
        item_id="item-1",
        unit_id="unit-1",
        question="Which choice is correct?",
        choices=["A1", "B1", "C1", "D1"],
        answer_index=1,
        question_intent="understand",
        difficulty="medium",
        explanation="Because B is correct.",
    )

    class FakeRepo:
        async def get_owned_session(self, *, user_id: str, session_id: str):
            return session

        async def fetch_session_detail_rows_canonical_only(self, session_id):
            return [(interaction, None, canonical_item, "Backpropagation")]

    monkeypatch.setattr(history_service, "HistoryRepository", lambda db: FakeRepo())

    detail = await history_service.get_session_detail(object(), user_id, session.id)

    assert detail.source == "inline_video"
    assert detail.checkpoint == "end"
    assert len(detail.questions) == 1
    assert detail.questions[0].correct_answer == "B"
