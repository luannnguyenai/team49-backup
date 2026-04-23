from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.exceptions import ValidationError
from src.models.learning import SessionType
from src.services import module_test_service


@pytest.mark.asyncio
async def test_start_module_test_delegates_to_canonical_helper(monkeypatch):
    expected = SimpleNamespace(session_id=uuid4())
    captured = {}

    async def fake_start(db, user_id, section_id):
        captured["args"] = (db, user_id, section_id)
        return expected

    monkeypatch.setattr(module_test_service, "_start_canonical_module_test", fake_start)

    result = await module_test_service.start_module_test(object(), uuid4(), uuid4())

    assert result is expected
    assert "args" in captured


@pytest.mark.asyncio
async def test_submit_module_test_rejects_legacy_session(monkeypatch):
    session = SimpleNamespace(
        id=uuid4(),
        canonical_section_id=None,
        completed_at=None,
        session_type=SessionType.module_test,
    )
    monkeypatch.setattr(
        module_test_service,
        "_get_module_test_session",
        AsyncMock(return_value=session),
    )

    with pytest.raises(ValidationError, match="Legacy module-test sessions are no longer supported"):
        await module_test_service.submit_module_test(
            db=object(),
            user_id=uuid4(),
            session_id=session.id,
            req=SimpleNamespace(answers=[]),
        )


@pytest.mark.asyncio
async def test_next_section_info_returns_next_sort_order():
    db = AsyncMock()
    next_section = SimpleNamespace(id=uuid4(), title="Section 2")
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: next_section)

    response = await module_test_service._next_section_info(
        db,
        SimpleNamespace(course_id=uuid4(), sort_order=1),
    )

    assert response is not None
    assert response.section_id == next_section.id
    assert response.section_title == "Section 2"
