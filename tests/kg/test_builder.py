"""Tests for pure KG builder behavior."""

import pytest

from src.kg.builder import CycleError, build, build_concepts, build_edges
from src.kg.hashing import canonical_hash
from src.kg.schemas import BridgesDoc, KCRef, KGConcept, KGEdge, LoadedSources, TopicRef


def _concept() -> KGConcept:
    return KGConcept(
        id="11111111-1111-4111-8111-111111111111",
        name="Self-Attention",
        canonical_kc_slug="KC-NLP-self-attention",
        source="manual",
    )


def _bridge_sources(*, cycle: bool = False) -> LoadedSources:
    prereq_cv = ("nlp_transformers",) if not cycle else ("nlp_transformers",)
    prereq_nlp = () if not cycle else ("cv_attention_transformers",)
    concept = _concept()
    return LoadedSources(
        topics=[
            TopicRef(
                slug="nlp_transformers",
                module_slug="mini_nlp",
                name="NLP Transformers",
                prerequisite_topic_slugs=prereq_nlp,
            ),
            TopicRef(
                slug="cv_attention_transformers",
                module_slug="mini_cv",
                name="CV Attention",
                prerequisite_topic_slugs=prereq_cv,
            ),
        ],
        kcs=[
            KCRef(
                slug="KC-NLP-self-attention",
                topic_slug="nlp_transformers",
                module_slug="mini_nlp",
                name="Self-Attention NLP",
            ),
            KCRef(
                slug="KC-CV-self-attention",
                topic_slug="cv_attention_transformers",
                module_slug="mini_cv",
                name="Self-Attention CV",
            ),
        ],
        questions=[],
        bridges=BridgesDoc(
            concepts=[concept],
            instance_of=[
                KGEdge(
                    src_kind="concept",
                    src_ref="CON-self-attention",
                    dst_kind="kc",
                    dst_ref="KC-NLP-self-attention",
                    type="INSTANCE_OF",
                    weight=1.0,
                    source="schema",
                ),
                KGEdge(
                    src_kind="concept",
                    src_ref="CON-self-attention",
                    dst_kind="kc",
                    dst_ref="KC-CV-self-attention",
                    type="INSTANCE_OF",
                    weight=1.0,
                    source="schema",
                ),
            ],
            transfers_to=[
                KGEdge(
                    src_kind="topic",
                    src_ref="nlp_transformers",
                    dst_kind="topic",
                    dst_ref="cv_attention_transformers",
                    type="TRANSFERS_TO",
                    weight=0.95,
                    source="schema",
                    meta={"reason": "CON-self-attention overlap"},
                )
            ],
        ),
    )


def test_build_counts_and_manual_edge_orientation() -> None:
    """P0 builder emits bridge concepts plus manual INSTANCE_OF and TRANSFERS_TO edges."""
    result = build(_bridge_sources())

    assert len(result.concepts) == 1
    assert len(result.edges) == 3
    assert [edge.type for edge in result.edges].count("INSTANCE_OF") == 2
    assert [edge.type for edge in result.edges].count("TRANSFERS_TO") == 1

    instance = result.edges[0]
    assert instance.src_kind == "kc"
    assert instance.src_ref == "KC-NLP-self-attention"
    assert instance.dst_kind == "concept"
    assert instance.dst_ref == "CON-self-attention"
    assert instance.source == "manual"


def test_build_concepts_only_uses_bridges() -> None:
    """P0 does not auto-derive concepts from KCs or questions."""
    concepts = build_concepts(_bridge_sources())

    assert concepts == [_concept()]


def test_requires_topic_prerequisite_cycle_raises_chain() -> None:
    """Topic prerequisites in sources must be a DAG."""
    with pytest.raises(CycleError, match="nlp_transformers.*cv_attention_transformers"):
        build_edges(_bridge_sources(cycle=True))


def test_build_is_idempotent() -> None:
    """Running the pure builder twice over the same sources must be identical."""
    sources = _bridge_sources()

    assert canonical_hash(build(sources).model_dump(mode="json")) == canonical_hash(
        build(sources).model_dump(mode="json")
    )
