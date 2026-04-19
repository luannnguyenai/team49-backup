"""Tests for deterministic KG next-topic ranking."""

from __future__ import annotations

import uuid

import pytest

from src.kg.schemas import KGEdge, KCNode, TopicNode
from tests.kg.test_service_path import FakeKGService, FakeMasteryProvider


class RecentFakeKGService(FakeKGService):
    def __init__(self, *args, recent: set[str] | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recent = recent or set()

    async def _load_recent_topic_slugs(self, user_id: uuid.UUID) -> set[str]:
        return self._recent


@pytest.mark.asyncio
async def test_rank_next_is_deterministic_and_uses_readiness_transfer_and_freshness() -> None:
    user_id = uuid.uuid4()
    service = RecentFakeKGService(
        topics=[
            TopicNode(
                slug="foundation",
                module_slug="mini_nlp",
                name="Foundation",
                prerequisite_topic_slugs=(),
                estimated_hours_beginner=2.0,
                estimated_hours_review=1.0,
            ),
            TopicNode(
                slug="transfer_candidate",
                module_slug="mini_cv",
                name="Transfer Candidate",
                prerequisite_topic_slugs=("foundation",),
                estimated_hours_beginner=2.0,
                estimated_hours_review=1.0,
            ),
            TopicNode(
                slug="cold_candidate",
                module_slug="mini_cv",
                name="Cold Candidate",
                prerequisite_topic_slugs=("foundation",),
                estimated_hours_beginner=2.0,
                estimated_hours_review=1.0,
            ),
            TopicNode(
                slug="recent_candidate",
                module_slug="mini_cv",
                name="Recent Candidate",
                prerequisite_topic_slugs=("foundation",),
                estimated_hours_beginner=2.0,
                estimated_hours_review=1.0,
            ),
        ],
        kcs=[
            KCNode(
                slug="KC-NLP-self-attention",
                topic_slug="foundation",
                module_slug="mini_nlp",
                name="Self-Attention",
            ),
            KCNode(
                slug="KC-CV-self-attention",
                topic_slug="transfer_candidate",
                module_slug="mini_cv",
                name="Self-Attention",
            ),
        ],
        edges=[
            KGEdge(
                src_kind="kc",
                src_ref="KC-NLP-self-attention",
                dst_kind="kc",
                dst_ref="KC-CV-self-attention",
                type="ALIGNS_WITH",
                weight=0.7,
                source="heuristic",
            )
        ],
        mastery=FakeMasteryProvider(
            topic_mastery={
                "foundation": 0.9,
                "transfer_candidate": 0.1,
                "cold_candidate": 0.1,
                "recent_candidate": 0.1,
            },
            kc_mastery={"KC-NLP-self-attention": 0.9},
        ),
        recent={"recent_candidate"},
    )

    first = await service.rank_next(user_id=user_id, candidate_limit=3)
    second = await service.rank_next(user_id=user_id, candidate_limit=3)

    assert [candidate.topic_slug for candidate in first] == [
        "transfer_candidate",
        "cold_candidate",
        "recent_candidate",
    ]
    assert first == second
    assert first[0].transfer_boost == 0.7
    assert first[-1].freshness_penalty == 1.0
