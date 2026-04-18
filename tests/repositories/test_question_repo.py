"""
tests/repositories/test_question_repo.py
-----------------------------------------
RED phase: QuestionRepository — data access layer for questions.
"""
from uuid import uuid4

import pytest
import pytest_asyncio

from src.models.content import (
    BloomLevel,
    CorrectAnswer,
    DifficultyBucket,
    Module,
    Question,
    QuestionStatus,
    Topic,
)


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


@pytest.mark.asyncio
async def test_get_pool_by_bloom_filters_to_assessment_usage_context(db_session):
    """Assessment pool không được lẫn question chỉ dành cho quiz/module_test."""
    from src.repositories.question_repo import QuestionRepository

    module = Module(
        name="Module",
        description="",
        order_index=1,
        prerequisite_module_ids=[],
    )
    db_session.add(module)
    await db_session.flush()

    topic = Topic(
        module_id=module.id,
        name="Topic",
        description="",
        order_index=1,
        prerequisite_topic_ids=[],
    )
    db_session.add(topic)
    await db_session.flush()

    def make_question(item_id: str, usage_context):
        return Question(
            item_id=item_id,
            version=1,
            status=QuestionStatus.active,
            topic_id=topic.id,
            module_id=module.id,
            bloom_level=BloomLevel.remember,
            difficulty_bucket=DifficultyBucket.easy,
            stem_text=f"Stem {item_id}",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer=CorrectAnswer.A,
            usage_context=usage_context,
        )

    assessment_question = make_question("ITEM-ASSESSMENT", ["assessment"])
    generic_question = make_question("ITEM-GENERIC", None)
    quiz_only_question = make_question("ITEM-QUIZ", ["quiz"])
    db_session.add_all([assessment_question, generic_question, quiz_only_question])
    await db_session.flush()

    repo = QuestionRepository(db_session)
    result = await repo.get_pool_by_bloom(
        topic_id=topic.id,
        bloom_levels=[BloomLevel.remember],
        excluded_ids=set(),
        ability=0.0,
        limit=10,
    )

    result_ids = {question.id for question in result}
    assert assessment_question.id in result_ids
    assert generic_question.id in result_ids
    assert quiz_only_question.id not in result_ids
