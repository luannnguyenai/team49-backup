"""Pure alignment discovery protocols and implementations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from itertools import combinations
from typing import Protocol

from src.kg.schemas import KGEdge, LoadedSources


class AlignmentDiscoverer(Protocol):
    """Protocol for discovering KG alignment edges from loaded sources."""

    def discover(
        self,
        sources: LoadedSources,
        manual_edges: Sequence[KGEdge] = (),
    ) -> list[KGEdge]:
        """Return discovered ALIGNS_WITH edges."""


class EmbeddingProvider(Protocol):
    """Protocol for text embedding providers used by future discoverers."""

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one vector per input text."""


class WeightCalibrator(Protocol):
    """Protocol for future edge-weight calibration policies."""

    def calibrate(self, edge: KGEdge, sources: LoadedSources) -> float:
        """Return a calibrated edge weight in [0.0, 1.0]."""


class NullAlignmentDiscoverer:
    """No-op alignment discoverer."""

    def discover(
        self,
        sources: LoadedSources,
        manual_edges: Sequence[KGEdge] = (),
    ) -> list[KGEdge]:
        """Return no discovered alignments."""
        return []


class SuffixMatchDiscoverer:
    """Heuristic KC alignment by matching slug suffixes across modules."""

    weight: float = 0.7

    def discover(
        self,
        sources: LoadedSources,
        manual_edges: Sequence[KGEdge] = (),
    ) -> list[KGEdge]:
        """Discover symmetric ALIGNS_WITH edges for same-suffix KCs.

        Args:
            sources: Loaded KG source data.
            manual_edges: Existing manual edges. A manual ALIGNS_WITH edge in
                either direction suppresses heuristic output for that KC pair.

        Returns:
            Symmetric heuristic ALIGNS_WITH edges.
        """
        manual_pairs = {
            frozenset((edge.src_ref, edge.dst_ref))
            for edge in manual_edges
            if edge.type == "ALIGNS_WITH" and edge.source == "manual"
        }

        by_suffix: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for kc in sources.kcs:
            by_suffix[_suffix_after_module(kc.slug)].append((kc.slug, kc.module_slug))

        edges: list[KGEdge] = []
        for suffix in sorted(by_suffix):
            candidates = sorted(set(by_suffix[suffix]))
            for (left_slug, left_module), (right_slug, right_module) in combinations(
                candidates, 2
            ):
                if left_slug == right_slug or left_module == right_module:
                    continue
                if frozenset((left_slug, right_slug)) in manual_pairs:
                    continue
                edges.extend(
                    [
                        _alignment_edge(left_slug, right_slug, self.weight),
                        _alignment_edge(right_slug, left_slug, self.weight),
                    ]
                )
        return edges


def _suffix_after_module(kc_slug: str) -> str:
    """Return the suffix after KC-<MOD>-."""
    parts = kc_slug.split("-", maxsplit=2)
    if len(parts) == 3 and parts[0] == "KC":
        return parts[2]
    return kc_slug


def _alignment_edge(src_ref: str, dst_ref: str, weight: float) -> KGEdge:
    """Build one heuristic ALIGNS_WITH KC edge."""
    return KGEdge(
        src_kind="kc",
        src_ref=src_ref,
        dst_kind="kc",
        dst_ref=dst_ref,
        type="ALIGNS_WITH",
        weight=weight,
        source="heuristic",
    )


def get_discoverer(settings: object) -> AlignmentDiscoverer:
    """Return an alignment discoverer selected from settings.

    Recognized setting values for ``kg_alignment_discoverer`` are
    ``suffix``, ``suffix_match``, and ``suffix-match``. All other values
    default to the null discoverer.
    """
    mode = str(getattr(settings, "kg_alignment_discoverer", "none")).lower()
    if mode in {"suffix", "suffix_match", "suffix-match"}:
        return SuffixMatchDiscoverer()
    return NullAlignmentDiscoverer()
