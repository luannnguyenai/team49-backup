"""
tests/repositories/test_session_repo.py
-----------------------------------------
RED phase: SessionRepository — get_active, get_completed_topic_ids.
"""
import pytest
from uuid import uuid4

from src.models.learning import SessionType


@pytest.mark.asyncio
async def test_session_repo_importable():
    from src.repositories.session_repo import SessionRepository  # noqa


@pytest.mark.asyncio
async def test_get_active_returns_none_for_new_user(db_session):
    """User chưa có session nào → None."""
    from src.repositories.session_repo import SessionRepository

    repo = SessionRepository(db_session)
    result = await repo.get_active(
        user_id=uuid4(),
        session_type=SessionType.quiz,
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_completed_topic_ids_returns_empty_set(db_session):
    """User chưa complete topic nào trong module → empty set."""
    from src.repositories.session_repo import SessionRepository

    repo = SessionRepository(db_session)
    result = await repo.get_completed_topic_ids(
        user_id=uuid4(),
        module_id=uuid4(),
    )
    assert isinstance(result, set)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_count_completed_quizzes_returns_zero_for_new_user(db_session):
    """User mới → quiz count = 0 cho mọi topic."""
    from src.repositories.session_repo import SessionRepository

    topic_ids = [uuid4(), uuid4()]
    repo = SessionRepository(db_session)
    result = await repo.count_completed_quizzes_per_topic(
        user_id=uuid4(),
        topic_ids=topic_ids,
    )
    assert isinstance(result, dict)
    for tid in topic_ids:
        assert result.get(tid, 0) == 0
