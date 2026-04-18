"""
tests/services/test_question_selector.py
------------------------------------------
RED phase: QuestionSelector — tier prioritization + IRT ranking.
Unit tests with a MockQuestionRepository — no DB needed.
"""
import random
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.models.content import BloomLevel, DifficultyBucket, QuestionStatus
from src.services.question_selector import QuestionSelector


def make_question(
    topic_id: UUID | None = None,
    difficulty: DifficultyBucket = DifficultyBucket.easy,
    bloom: BloomLevel = BloomLevel.remember,
    a: float = 1.0,
    b: float = 0.0,
):
    return SimpleNamespace(
        id=uuid4(),
        topic_id=topic_id or uuid4(),
        difficulty_bucket=difficulty,
        bloom_level=bloom,
        status=QuestionStatus.active,
        irt_discrimination=a,
        irt_difficulty=b,
        usage_context=["quiz", "module_test", "assessment"],
    )


class MockQuestionRepo:
    def __init__(self, pool: list, interaction_map: dict[UUID, bool] | None = None):
        self.pool = pool
        self.interaction_map = interaction_map or {}

    async def get_pool_by_difficulty(self, topic_id, difficulty, usage_context):
        return [q for q in self.pool if q.difficulty_bucket == difficulty]

    async def get_pool_by_bloom(self, topic_id, bloom_levels, excluded_ids, ability, limit):
        candidates = [
            q for q in self.pool
            if q.bloom_level in bloom_levels and q.id not in excluded_ids
        ]
        return candidates[:limit]

    async def get_interaction_map(self, user_id, topic_id):
        return self.interaction_map


@pytest.mark.asyncio
async def test_tier1_never_answered_selected_first():
    """Questions chưa trả lời (Tier 1) được chọn trước."""
    random.seed(42)
    topic_id = uuid4()
    never = [make_question(topic_id=topic_id) for _ in range(3)]
    wrong = [make_question(topic_id=topic_id) for _ in range(3)]
    correct = [make_question(topic_id=topic_id) for _ in range(3)]
    interaction_map = {**{q.id: True for q in wrong}, **{q.id: False for q in correct}}

    repo = MockQuestionRepo(pool=never + wrong + correct, interaction_map=interaction_map)
    selector = QuestionSelector(repo)
    result = await selector.select_by_difficulty_slots(
        user_id=uuid4(),
        topic_id=topic_id,
        slots=[(DifficultyBucket.easy, 3)],
        usage_context="quiz",
    )
    assert len(result) == 3
    assert {q.id for q in result} == {q.id for q in never}


@pytest.mark.asyncio
async def test_tier2_ever_wrong_preferred_over_correct():
    """Tier 2 (ever_wrong) ưu tiên hơn Tier 3 (always_correct)."""
    random.seed(42)
    topic_id = uuid4()
    wrong = [make_question(topic_id=topic_id) for _ in range(2)]
    correct = [make_question(topic_id=topic_id) for _ in range(2)]
    interaction_map = {**{q.id: True for q in wrong}, **{q.id: False for q in correct}}

    repo = MockQuestionRepo(pool=wrong + correct, interaction_map=interaction_map)
    selector = QuestionSelector(repo)
    result = await selector.select_by_difficulty_slots(
        user_id=uuid4(),
        topic_id=topic_id,
        slots=[(DifficultyBucket.easy, 2)],
        usage_context="quiz",
    )
    assert {q.id for q in result} == {q.id for q in wrong}


@pytest.mark.asyncio
async def test_select_by_bloom_returns_list():
    topic_id = uuid4()
    pool = [
        make_question(topic_id=topic_id, bloom=BloomLevel.remember),
        make_question(topic_id=topic_id, bloom=BloomLevel.understand),
    ]
    repo = MockQuestionRepo(pool=pool)
    selector = QuestionSelector(repo)
    result = await selector.select_by_bloom_irt(
        user_id=uuid4(),
        topic_id=topic_id,
        slots=[([BloomLevel.remember], 1)],
        ability=0.0,
        excluded_ids=set(),
    )
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].bloom_level == BloomLevel.remember
