from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.repositories.canonical_content_repo import CanonicalContentRepository


@pytest.mark.asyncio
async def test_get_linked_learning_units_skips_empty_course_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_linked_learning_units([]) == []
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_unit_kp_rows_executes_query():
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repo = CanonicalContentRepository(session)

    rows = await repo.get_unit_kp_rows(["unit-a"])

    assert rows == []
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_get_prerequisite_edges_skips_empty_kps():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_prerequisite_edges_for_kps([]) == []
    assert session.execute.await_count == 0
