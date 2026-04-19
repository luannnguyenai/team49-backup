"""Tests for src/kg/schemas.py — validation failures and round-trips."""

import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from src.kg.schemas import (
    BridgesDoc,
    KCRef,
    KGConcept,
    KGEdge,
    LoadedSources,
    SyncReport,
    TopicRef,
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _concept(**kwargs: Any) -> dict[str, Any]:
    """Return a minimal valid KGConcept payload."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "name": "Test Concept",
        "source": "manual",
    }
    return {**defaults, **kwargs}


def _edge(**kwargs: Any) -> dict[str, Any]:
    """Return a minimal valid KGEdge payload (INSTANCE_OF concept→kc)."""
    defaults: dict[str, Any] = {
        "src_kind": "concept",
        "src_ref": "c-test-01",
        "dst_kind": "kc",
        "dst_ref": "kc-test-01",
        "type": "INSTANCE_OF",
        "weight": 0.9,
        "source": "schema",
    }
    return {**defaults, **kwargs}


# ---------------------------------------------------------------------------
# KGEdge weight validation
# ---------------------------------------------------------------------------


class TestKGEdgeWeight:
    def test_weight_above_one_raises(self) -> None:
        """weight > 1.0 must be rejected."""
        with pytest.raises(ValidationError, match="weight"):
            KGEdge(**_edge(weight=1.5))

    def test_weight_negative_raises(self) -> None:
        """Negative weight must be rejected."""
        with pytest.raises(ValidationError, match="weight"):
            KGEdge(**_edge(weight=-0.1))

    def test_weight_boundary_zero_accepted(self) -> None:
        """weight == 0.0 is the lower boundary and must be valid."""
        edge = KGEdge(**_edge(weight=0.0))
        assert edge.weight == 0.0

    def test_weight_boundary_one_accepted(self) -> None:
        """weight == 1.0 is the upper boundary and must be valid."""
        edge = KGEdge(**_edge(weight=1.0))
        assert edge.weight == 1.0


# ---------------------------------------------------------------------------
# BridgesDoc validator
# ---------------------------------------------------------------------------


class TestBridgesDocValidator:
    def _valid_doc_kwargs(self) -> dict[str, Any]:
        return {
            "concepts": [KGConcept(**_concept())],
            "instance_of": [KGEdge(**_edge())],
            "transfers_to": [],
        }

    def test_invalid_src_kind_in_instance_of_raises(self) -> None:
        """instance_of edge with src_kind != 'concept' must raise."""
        bad_edge = KGEdge(**_edge(src_kind="topic"))
        with pytest.raises(ValidationError, match="src_kind"):
            BridgesDoc(
                concepts=[KGConcept(**_concept())],
                instance_of=[bad_edge],
                transfers_to=[],
            )

    def test_invalid_dst_kind_in_instance_of_raises(self) -> None:
        """instance_of edge with dst_kind != 'kc' must raise."""
        bad_edge = KGEdge(**_edge(dst_kind="topic"))
        with pytest.raises(ValidationError, match="dst_kind"):
            BridgesDoc(
                concepts=[KGConcept(**_concept())],
                instance_of=[bad_edge],
                transfers_to=[],
            )

    def test_valid_bridges_doc_accepted(self) -> None:
        """Well-formed BridgesDoc must construct without error."""
        doc = BridgesDoc(**self._valid_doc_kwargs())
        assert len(doc.concepts) == 1
        assert len(doc.instance_of) == 1

    def test_empty_instance_of_accepted(self) -> None:
        """BridgesDoc with no instance_of edges is valid."""
        doc = BridgesDoc(concepts=[], instance_of=[], transfers_to=[])
        assert doc.instance_of == ()


# ---------------------------------------------------------------------------
# Round-trips
# ---------------------------------------------------------------------------


class TestRoundTrips:
    def test_kg_concept_round_trip(self) -> None:
        concept = KGConcept(**_concept(description="desc", canonical_kc_slug="kc-01"))
        restored = KGConcept.model_validate(concept.model_dump())
        assert concept == restored

    def test_kg_edge_round_trip(self) -> None:
        edge = KGEdge(**_edge(meta={"confidence": 0.8}))
        restored = KGEdge.model_validate(edge.model_dump())
        assert edge == restored

    def test_sync_report_all_empty_valid(self) -> None:
        report = SyncReport(created=[], updated=[], unchanged=[], soft_deleted=[])
        assert report.created == ()

    def test_loaded_sources_round_trip(self) -> None:
        concept = KGConcept(**_concept())
        edge = KGEdge(**_edge())
        bridges = BridgesDoc(concepts=[concept], instance_of=[edge], transfers_to=[])
        topic = TopicRef(
            slug="t-01",
            module_slug="m-01",
            name="Topic One",
            prerequisite_topic_slugs=["t-00"],
        )
        kc = KCRef(
            slug="kc-01",
            topic_slug="t-01",
            module_slug="m-01",
            name="KC One",
            description="desc",
        )
        sources = LoadedSources(topics=[topic], kcs=[kc], questions=[], bridges=bridges)
        restored = LoadedSources.model_validate(sources.model_dump())
        assert restored == sources


# ---------------------------------------------------------------------------
# Frozen (immutability)
# ---------------------------------------------------------------------------


class TestFrozenModels:
    def test_kg_concept_is_immutable(self) -> None:
        concept = KGConcept(**_concept())
        with pytest.raises((ValidationError, TypeError)):
            concept.name = "mutated"  # type: ignore[misc]

    def test_kg_edge_is_immutable(self) -> None:
        edge = KGEdge(**_edge())
        with pytest.raises((ValidationError, TypeError)):
            edge.weight = 0.5  # type: ignore[misc]

    def test_kc_ref_is_immutable(self) -> None:
        kc = KCRef(slug="kc-01", topic_slug="t-01", module_slug="m-01", name="KC")
        with pytest.raises((ValidationError, TypeError)):
            kc.slug = "mutated"  # type: ignore[misc]
