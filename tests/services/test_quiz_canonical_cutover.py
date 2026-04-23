from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.exceptions import ValidationError
from src.models.learning import SessionType
from src.services import quiz_service


@pytest.mark.asyncio
async def test_start_quiz_delegates_to_canonical_helper(monkeypatch):
    expected = SimpleNamespace(session_id=uuid4())
    captured = {}

    async def fake_start(db, user_id, topic_id):
        captured["args"] = (db, user_id, topic_id)
        return expected

    monkeypatch.setattr(quiz_service, "_start_canonical_quiz", fake_start)

    result = await quiz_service.start_quiz(object(), uuid4(), uuid4())

    assert result is expected
    assert "args" in captured


@pytest.mark.asyncio
async def test_answer_question_rejects_legacy_session(monkeypatch):
    session = SimpleNamespace(
        id=uuid4(),
        canonical_unit_id=None,
        completed_at=None,
        session_type=SessionType.quiz,
    )
    monkeypatch.setattr(quiz_service, "_get_quiz_session", AsyncMock(return_value=session))

    with pytest.raises(ValidationError, match="Legacy quiz sessions are no longer supported"):
        await quiz_service.answer_question(
            db=object(),
            user_id=uuid4(),
            session_id=session.id,
            req=SimpleNamespace(question_id=uuid4(), selected_answer="A", response_time_ms=None),
        )


@pytest.mark.asyncio
async def test_get_quiz_history_reads_canonical_unit_titles():
    db = AsyncMock()
    session_id = uuid4()
    unit_id = uuid4()
    session = SimpleNamespace(
        id=session_id,
        canonical_unit_id=unit_id,
        score_percent=80.0,
        correct_count=8,
        total_questions=10,
        completed_at=None,
        started_at=datetime.now(UTC),
    )
    db.execute.return_value = SimpleNamespace(all=lambda: [(session, "CNN basics")])

    response = await quiz_service.get_quiz_history(db, uuid4())

    assert response.total == 1
    assert response.items[0].topic_id == unit_id
    assert response.items[0].topic_name == "CNN basics"
