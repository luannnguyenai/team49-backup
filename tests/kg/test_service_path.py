"""Tests for KG learning path service behavior."""

from __future__ import annotations

import uuid

import pytest

from src.kg.schemas import KGEdge, KCNode, TopicNode
from src.kg.service import KGService


class FakeMasteryProvider:
    def __init__(
        self,
        topic_mastery: dict[str, float] | None = None,
        kc_mastery: dict[str, float] | None = None,
    ) -> None:
        self.topic_mastery = topic_mastery or {}
        self.kc_mastery = kc_mastery or {}

    async def get_topic_mastery(self, user_id: uuid.UUID) -> dict[str, float]:
        return self.topic_mastery

    async def get_kc_mastery(self, user_id: uuid.UUID) -> dict[str, float]:
        return self.kc_mastery


class FakeKGService(KGService):
    def __init__(
        self,
        *,
        topics: list[TopicNode],
        kcs: list[KCNode],
        edges: list[KGEdge],
        mastery: FakeMasteryProvider,
    ) -> None:
        super().__init__(session_factory=None, mastery=mastery, repo=None)
        self._topics = {topic.slug: topic for topic in topics}
        self._kcs = kcs
        self._edges = edges

    async def _load_topics_map(self) -> dict[str, TopicNode]:
        return self._topics

    async def _load_kcs(self) -> list[KCNode]:
        return self._kcs

    async def _load_edges(self) -> list[KGEdge]:
        return self._edges


@pytest.mark.asyncio
async def test_build_path_applies_cross_module_shortcut_hours() -> None:
    user_id = uuid.uuid4()
    topics = [
        TopicNode(
            slug="cv_attention_transformers",
            module_slug="mini_cv",
            name="CV Attention",
            prerequisite_topic_slugs=(),
            estimated_hours_beginner=10.0,
            estimated_hours_review=4.0,
        ),
        TopicNode(
            slug="nlp_transformers",
            module_slug="mini_nlp",
            name="NLP Transformers",
            prerequisite_topic_slugs=(),
            estimated_hours_beginner=8.0,
            estimated_hours_review=3.0,
        ),
    ]
    kcs = [
        KCNode(
            slug="KC-CV-self-attention",
            topic_slug="cv_attention_transformers",
            module_slug="mini_cv",
            name="Self-Attention",
        ),
        KCNode(
            slug="KC-NLP-self-attention",
            topic_slug="nlp_transformers",
            module_slug="mini_nlp",
            name="Self-Attention",
        ),
    ]
    edges = [
        KGEdge(
            src_kind="kc",
            src_ref="KC-NLP-self-attention",
            dst_kind="kc",
            dst_ref="KC-CV-self-attention",
            type="ALIGNS_WITH",
            weight=0.7,
            source="heuristic",
        )
    ]

    baseline = FakeKGService(
        topics=topics,
        kcs=kcs,
        edges=[],
        mastery=FakeMasteryProvider(
            topic_mastery={"cv_attention_transformers": 0.0},
            kc_mastery={"KC-NLP-self-attention": 0.9},
        ),
    )
    shortcut = FakeKGService(
        topics=topics,
        kcs=kcs,
        edges=edges,
        mastery=FakeMasteryProvider(
            topic_mastery={"cv_attention_transformers": 0.0},
            kc_mastery={"KC-NLP-self-attention": 0.9},
        ),
    )

    baseline_path = await baseline.build_path(
        user_id=user_id,
        target_topics=["cv_attention_transformers"],
        hours_per_week=20.0,
    )
    shortcut_path = await shortcut.build_path(
        user_id=user_id,
        target_topics=["cv_attention_transformers"],
        hours_per_week=20.0,
    )

    baseline_topic = baseline_path.weeks[0].topics[0]
    shortcut_topic = shortcut_path.weeks[0].topics[0]
    assert baseline_topic.hours == 10.0
    assert shortcut_topic.hours == 4.0
    assert shortcut_topic.mode == "review"
    assert shortcut_topic.shortcuts == ("KC-NLP-self-attention -> KC-CV-self-attention",)


@pytest.mark.asyncio
async def test_build_path_expands_prereq_chain_in_topological_order() -> None:
    user_id = uuid.uuid4()
    service = FakeKGService(
        topics=[
            TopicNode(
                slug="linear_algebra",
                module_slug="mini_math",
                name="Linear Algebra",
                prerequisite_topic_slugs=(),
                estimated_hours_beginner=2.0,
                estimated_hours_review=1.0,
            ),
            TopicNode(
                slug="vectors",
                module_slug="mini_math",
                name="Vectors",
                prerequisite_topic_slugs=("linear_algebra",),
                estimated_hours_beginner=2.0,
                estimated_hours_review=1.0,
            ),
            TopicNode(
                slug="attention",
                module_slug="mini_nlp",
                name="Attention",
                prerequisite_topic_slugs=("vectors",),
                estimated_hours_beginner=2.0,
                estimated_hours_review=1.0,
            ),
        ],
        kcs=[],
        edges=[],
        mastery=FakeMasteryProvider(),
    )

    path = await service.build_path(
        user_id=user_id,
        target_topics=["attention"],
        hours_per_week=20.0,
    )

    assert [topic.slug for topic in path.weeks[0].topics] == [
        "linear_algebra",
        "vectors",
        "attention",
    ]
