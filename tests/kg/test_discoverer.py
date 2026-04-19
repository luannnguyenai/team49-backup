"""Tests for pure KG alignment discoverers."""

from src.kg.discoverer import NullAlignmentDiscoverer, SuffixMatchDiscoverer, get_discoverer
from src.kg.schemas import BridgesDoc, KCRef, KGEdge, LoadedSources, TopicRef


def _sources_with_suffix_matches() -> LoadedSources:
    return LoadedSources(
        topics=[
            TopicRef(slug="cv_topic", module_slug="mini_cv", name="CV", prerequisite_topic_slugs=[]),
            TopicRef(
                slug="nlp_topic",
                module_slug="mini_nlp",
                name="NLP",
                prerequisite_topic_slugs=[],
            ),
        ],
        kcs=[
            KCRef(
                slug="KC-CV-self-attention",
                topic_slug="cv_topic",
                module_slug="mini_cv",
                name="CV Attention",
            ),
            KCRef(
                slug="KC-NLP-self-attention",
                topic_slug="nlp_topic",
                module_slug="mini_nlp",
                name="NLP Attention",
            ),
            KCRef(
                slug="KC-CV-only",
                topic_slug="cv_topic",
                module_slug="mini_cv",
                name="CV Only",
            ),
        ],
        questions=[],
        bridges=BridgesDoc(concepts=[], instance_of=[], transfers_to=[]),
    )


def test_null_alignment_discoverer_returns_empty() -> None:
    """Null discoverer is a no-op implementation."""
    assert NullAlignmentDiscoverer().discover(_sources_with_suffix_matches()) == []


def test_suffix_match_emits_symmetric_alignment_edges() -> None:
    """Matching suffixes in different modules produce heuristic ALIGNS_WITH twins."""
    edges = SuffixMatchDiscoverer().discover(_sources_with_suffix_matches())

    assert len(edges) == 2
    assert {(edge.src_ref, edge.dst_ref) for edge in edges} == {
        ("KC-CV-self-attention", "KC-NLP-self-attention"),
        ("KC-NLP-self-attention", "KC-CV-self-attention"),
    }
    assert {edge.type for edge in edges} == {"ALIGNS_WITH"}
    assert {edge.source for edge in edges} == {"heuristic"}
    assert {edge.weight for edge in edges} == {0.7}


def test_suffix_match_respects_manual_alignment() -> None:
    """Heuristic alignment must not duplicate a manually supplied alignment."""
    manual = [
        KGEdge(
            src_kind="kc",
            src_ref="KC-NLP-self-attention",
            dst_kind="kc",
            dst_ref="KC-CV-self-attention",
            type="ALIGNS_WITH",
            weight=1.0,
            source="manual",
        )
    ]

    assert SuffixMatchDiscoverer().discover(_sources_with_suffix_matches(), manual_edges=manual) == []


def test_suffix_match_does_not_emit_self_loops() -> None:
    """Duplicate suffixes in the same module must not create self-loops or same-module edges."""
    sources = LoadedSources(
        topics=[
            TopicRef(slug="cv_topic", module_slug="mini_cv", name="CV", prerequisite_topic_slugs=[]),
        ],
        kcs=[
            KCRef(slug="KC-CV-shared", topic_slug="cv_topic", module_slug="mini_cv", name="A"),
            KCRef(slug="KC-CV-shared", topic_slug="cv_topic", module_slug="mini_cv", name="B"),
        ],
        questions=[],
        bridges=BridgesDoc(concepts=[], instance_of=[], transfers_to=[]),
    )

    assert SuffixMatchDiscoverer().discover(sources) == []


def test_get_discoverer_factory_defaults_to_null() -> None:
    """Factory defaults to the null discoverer when settings do not request suffix matching."""

    class Settings:
        kg_alignment_discoverer = "none"

    assert isinstance(get_discoverer(Settings()), NullAlignmentDiscoverer)
