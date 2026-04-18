"""
tests/repositories/test_question_repo.py
-----------------------------------------
RED phase: QuestionRepository — data access layer for questions.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from src.models.content import DifficultyBucket, BloomLevel, QuestionStatus


# ---------------------------------------------------------------------------
# Tests — will FAIL until QuestionRepository is implemented
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_question_repo_importable():
    """QuestionRepository phải importable."""
    from src.repositories.question_repo import QuestionRepository  # noqa


@pytest.mark.asyncio
async def test_get_pool_by_difficulty_returns_only_active(db_session):
    """get_pool_by_difficulty chỉ trả về questions có status=active."""
    from src.repositories.question_repo import QuestionRepository

    repo = QuestionRepository(db_session)
    questions = await repo.get_pool_by_difficulty(
        topic_id=uuid4(),
        difficulty=DifficultyBucket.easy,
        usage_context="quiz",
    )
    assert isinstance(questions, list)
    for q in questions:
        assert q.status == QuestionStatus.active
        assert q.difficulty_bucket == DifficultyBucket.easy


@pytest.mark.asyncio
async def test_get_interaction_map_returns_empty_for_new_user(db_session):
    """User chưa có interaction nào → map trống."""
    from src.repositories.question_repo import QuestionRepository

    repo = QuestionRepository(db_session)
    result = await repo.get_interaction_map(
        user_id=uuid4(),
        topic_id=uuid4(),
    )
    assert isinstance(result, dict)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_recent_assessment_ids_returns_empty_for_new_user(db_session):
    """User chưa có assessment nào → empty set."""
    from src.repositories.question_repo import QuestionRepository

    repo = QuestionRepository(db_session)
    result = await repo.get_recent_assessment_ids(user_id=uuid4())
    assert isinstance(result, set)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_pool_by_bloom_returns_list(db_session):
    """get_pool_by_bloom trả về list (có thể rỗng nếu không có data)."""
    from src.repositories.question_repo import QuestionRepository

    repo = QuestionRepository(db_session)
    result = await repo.get_pool_by_bloom(
        topic_id=uuid4(),
        bloom_levels=[BloomLevel.remember, BloomLevel.understand],
        excluded_ids=set(),
        ability=0.0,
        limit=10,
    )
    assert isinstance(result, list)
