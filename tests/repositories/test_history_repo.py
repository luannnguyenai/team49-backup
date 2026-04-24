"""
tests/repositories/test_history_repo.py
---------------------------------------
RED phase: HistoryRepository — read-model access for history pages and details.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.models.learning import SessionType


@pytest.mark.asyncio
async def test_history_repo_importable():
    from src.repositories.history_repo import HistoryRepository  # noqa


@pytest.mark.asyncio
async def test_count_sessions_returns_scalar_total():
    from src.repositories.history_repo import HistoryRepository

    session = AsyncMock()
    result = Mock()
    result.scalar.return_value = 7
    session.execute.return_value = result

    repo = HistoryRepository(session)
    total = await repo.count_sessions(filters=[])

    assert total == 7


@pytest.mark.asyncio
async def test_get_owned_session_returns_none_when_session_missing():
    from src.repositories.history_repo import HistoryRepository

    session = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    repo = HistoryRepository(session)
    owned = await repo.get_owned_session(user_id=uuid4(), session_id=uuid4())

    assert owned is None


@pytest.mark.asyncio
async def test_fetch_session_detail_rows_canonical_only_does_not_require_legacy_question_join():
    from src.repositories.history_repo import HistoryRepository

    session = AsyncMock()
    result = Mock()
    row = ("interaction", "canonical_item")
    result.all.return_value = [row]
    session.execute.return_value = result

    repo = HistoryRepository(session)
    rows = await repo.fetch_session_detail_rows_canonical_only(uuid4())

    assert rows == [("interaction", None, "canonical_item", None)]


@pytest.mark.asyncio
async def test_fetch_history_page_canonical_only_returns_sessions_without_legacy_labels():
    from src.repositories.history_repo import HistoryRepository

    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = ["session"]
    session.execute.return_value = result

    repo = HistoryRepository(session)
    rows = await repo.fetch_history_page_canonical_only(filters=[], page=1, page_size=20)

    assert rows == [("session", None, None)]
