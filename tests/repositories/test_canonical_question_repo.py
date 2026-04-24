from unittest.mock import AsyncMock, Mock

import pytest

from src.repositories.canonical_question_repo import CanonicalQuestionRepository


@pytest.mark.asyncio
async def test_get_items_for_phase_executes_join_query():
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    repo = CanonicalQuestionRepository(session)
    rows = await repo.get_items_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=["unit-a"],
        limit=5,
    )

    assert rows == []
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_get_items_for_phase_returns_empty_without_units():
    session = AsyncMock()

    repo = CanonicalQuestionRepository(session)
    rows = await repo.get_items_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=[],
        limit=5,
    )

    assert rows == []
    assert session.execute.await_count == 0
