"""
services/question_selector.py
-------------------------------
Consolidated question selection logic, eliminating duplication across
quiz_service, assessment_service, and module_test_service.

Priority tiers for difficulty-based selection:
    Tier 1: Never-answered questions
    Tier 2: Ever-wrong questions
    Tier 3: Always-correct questions

IRT-based selection for assessment uses 2PL item information function.
"""

import math
import random
from uuid import UUID

from src.constants import IRT_CANDIDATE_MULTIPLIER
from src.models.content import BloomLevel, DifficultyBucket, Question


class QuestionSelector:
    """Thin selection layer over QuestionRepository."""

    def __init__(self, repo):
        self.repo = repo

    async def select_by_difficulty_slots(
        self,
        user_id: UUID,
        topic_id: UUID,
        slots: list[tuple[DifficultyBucket, int]],
        usage_context: str,
        excluded_ids: set[UUID] | frozenset[UUID] = frozenset(),
    ) -> list[Question]:
        """Pick questions per (difficulty, count) slot using tier priority."""
        interaction_map = await self.repo.get_interaction_map(user_id, topic_id)
        results: list[Question] = []
        for difficulty, count in slots:
            pool = await self.repo.get_pool_by_difficulty(topic_id, difficulty, usage_context)
            pool = [q for q in pool if q.id not in excluded_ids]
            tier1 = [q for q in pool if q.id not in interaction_map]
            tier2 = [q for q in pool if q.id in interaction_map and interaction_map[q.id]]
            tier3 = [q for q in pool if q.id in interaction_map and not interaction_map[q.id]]
            results += _sample_with_priority([tier1, tier2, tier3], count)
        random.shuffle(results)
        return results

    async def select_by_bloom_irt(
        self,
        user_id: UUID,
        topic_id: UUID,
        slots: list[tuple[list[BloomLevel], int]],
        ability: float,
        excluded_ids: set[UUID],
    ) -> list[Question]:
        """Pick IRT-optimal questions per (bloom_levels, count) slot."""
        results: list[Question] = []
        for bloom_levels, count in slots:
            candidates = await self.repo.get_pool_by_bloom(
                topic_id, bloom_levels, excluded_ids, ability, count * IRT_CANDIDATE_MULTIPLIER
            )
            results += _rank_by_irt_information(candidates, ability)[:count]
        return results


def _sample_with_priority(tiers: list[list[Question]], count: int) -> list[Question]:
    """Fill `count` slots from tiers in order, sampling within each tier."""
    picked: list[Question] = []
    remaining = count
    for tier in tiers:
        if remaining <= 0:
            break
        if len(tier) <= remaining:
            picked.extend(tier)
            remaining -= len(tier)
        else:
            picked.extend(random.sample(tier, remaining))
            remaining = 0
    return picked


def _rank_by_irt_information(questions: list[Question], ability: float) -> list[Question]:
    """Sort questions by 2PL item information at the given ability level (desc)."""
    return sorted(questions, key=lambda q: _irt_information(q, ability), reverse=True)


def _irt_information(q: Question, ability: float) -> float:
    a = q.irt_discrimination or 1.0
    b = q.irt_difficulty or 0.0
    p = 1.0 / (1.0 + math.exp(-a * (ability - b)))
    return a * a * p * (1.0 - p)
