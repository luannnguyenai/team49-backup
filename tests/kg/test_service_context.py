"""Tests for KG topic context retrieval."""

from __future__ import annotations

import uuid

import pytest

from src.kg.schemas import KGEdge, KCNode, TopicNode
from tests.kg.test_service_path import FakeKGService, FakeMasteryProvider


@pytest.mark.asyncio
async def test_get_topic_context_returns_prereqs_siblings_and_transfers() -> None:
    service = FakeKGService(
        topics=[
            TopicNode(
                slug="nlp_transformers",
                module_slug="mini_nlp",
                name="NLP Transformers",
                prerequisite_topic_slugs=(),
                estimated_hours_beginner=8.0,
                estimated_hours_review=3.0,
            ),
            TopicNode(
                slug="cv_attention_transformers",
                module_slug="mini_cv",
                name="CV Attention",
                prerequisite_topic_slugs=("nlp_transformers",),
                estimated_hours_beginner=10.0,
                estimated_hours_review=4.0,
            ),
        ],
        kcs=[
            KCNode(
                slug="KC-NLP-self-attention",
                topic_slug="nlp_transformers",
                module_slug="mini_nlp",
                name="Self-Attention",
            ),
            KCNode(
                slug="KC-CV-self-attention",
                topic_slug="cv_attention_transformers",
                module_slug="mini_cv",
                name="Self-Attention",
            ),
        ],
        edges=[
            KGEdge(
                src_kind="concept",
                src_ref=str(uuid.uuid4()),
                dst_kind="kc",
                dst_ref="KC-NLP-self-attention",
                type="INSTANCE_OF",
                weight=1.0,
                source="manual",
            ),
            KGEdge(
                src_kind="concept",
                src_ref="CON-self-attention",
                dst_kind="kc",
                dst_ref="KC-CV-self-attention",
                type="INSTANCE_OF",
                weight=1.0,
                source="manual",
            ),
            KGEdge(
                src_kind="concept",
                src_ref="CON-self-attention",
                dst_kind="kc",
                dst_ref="KC-NLP-self-attention",
                type="INSTANCE_OF",
                weight=1.0,
                source="manual",
            ),
            KGEdge(
                src_kind="topic",
                src_ref="nlp_transformers",
                dst_kind="topic",
                dst_ref="cv_attention_transformers",
                type="TRANSFERS_TO",
                weight=0.95,
                source="manual",
            ),
        ],
        mastery=FakeMasteryProvider(),
    )

    context = await service.get_topic_context("cv_attention_transformers", hops=2)

    assert context.topic.slug == "cv_attention_transformers"
    assert [topic.slug for topic in context.prereqs] == ["nlp_transformers"]
    assert [kc.slug for kc in context.kcs] == ["KC-CV-self-attention"]
    assert [kc.slug for kc in context.sibling_kcs] == ["KC-NLP-self-attention"]
    assert [(edge.src_ref, edge.dst_ref) for edge in context.transfers] == [
        ("nlp_transformers", "cv_attention_transformers")
    ]


@pytest.mark.asyncio
async def test_get_topic_context_raises_for_missing_topic() -> None:
    service = FakeKGService(
        topics=[],
        kcs=[],
        edges=[],
        mastery=FakeMasteryProvider(),
    )

    with pytest.raises(KeyError):
        await service.get_topic_context("missing")
