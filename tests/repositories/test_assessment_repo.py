"""
tests/repositories/test_assessment_repo.py
------------------------------------------
RED phase: AssessmentRepository — assessment-specific DB access helpers.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4


@pytest.mark.asyncio
async def test_assessment_repo_importable():
    from src.repositories.assessment_repo import AssessmentRepository  # noqa


@pytest.mark.asyncio
async def test_get_max_global_sequence_defaults_to_zero():
    from src.repositories.assessment_repo import AssessmentRepository

    session = AsyncMock()
    result = Mock()
    result.scalar.return_value = None
    session.execute.return_value = result

    repo = AssessmentRepository(session)
    max_pos = await repo.get_max_global_sequence(uuid4())

    assert max_pos == 0


@pytest.mark.asyncio
async def test_get_assessment_session_returns_none_for_missing_session():
    from src.repositories.assessment_repo import AssessmentRepository

    session = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    repo = AssessmentRepository(session)
    found = await repo.get_assessment_session(user_id=uuid4(), session_id=uuid4())

    assert found is None


@pytest.mark.asyncio
async def test_get_kc_name_map_returns_empty_dict_for_no_ids():
    from src.repositories.assessment_repo import AssessmentRepository

    session = AsyncMock()
    repo = AssessmentRepository(session)

    assert await repo.get_kc_name_map([]) == {}
