"""Pure Knowledge Graph builder.

No database, filesystem, or discoverer orchestration belongs here. The builder
only maps already-loaded sources into concept and edge objects.
"""

from __future__ import annotations

from typing import Iterable

import networkx as nx
from pydantic import BaseModel, ConfigDict

from src.kg.schemas import KGConcept, KGEdge, LoadedSources, TopicRef


class CycleError(ValueError):
    """Raised when topic prerequisites contain a cycle."""


class BuildResult(BaseModel):
    """Pure build output for KG sync/storage layers."""

    model_config = ConfigDict(frozen=True)

    concepts: tuple[KGConcept, ...]
    edges: tuple[KGEdge, ...]


def _cycle_chain(graph: nx.DiGraph) -> list[str]:
    """Return a readable node chain for the first directed cycle."""
    cycle = nx.find_cycle(graph, orientation="original")
    if not cycle:
        return []
    chain = [cycle[0][0]]
    chain.extend(edge[1] for edge in cycle)
    return [str(node) for node in chain]


def _validate_topic_requires_dag(topics: Iterable[TopicRef]) -> None:
    """Validate topic prerequisites from LoadedSources as a DAG."""
    graph = nx.DiGraph()
    for topic in topics:
        graph.add_node(topic.slug)
        for prerequisite in topic.prerequisite_topic_slugs:
            graph.add_edge(prerequisite, topic.slug)

    if not nx.is_directed_acyclic_graph(graph):
        chain = " -> ".join(_cycle_chain(graph))
        raise CycleError(f"REQUIRES topic prerequisite cycle detected: {chain}")


def build_concepts(sources: LoadedSources) -> list[KGConcept]:
    """Build P0 concept nodes from kg_bridges.yaml only."""
    return list(sources.bridges.concepts)


def _manual_instance_of_edges(sources: LoadedSources) -> list[KGEdge]:
    """Map bridge INSTANCE_OF edges to storage orientation kc -> concept."""
    return [
        KGEdge(
            src_kind="kc",
            src_ref=edge.dst_ref,
            dst_kind="concept",
            dst_ref=edge.src_ref,
            type="INSTANCE_OF",
            weight=edge.weight,
            source="manual",
            meta=edge.meta,
        )
        for edge in sources.bridges.instance_of
    ]


def _manual_transfer_edges(sources: LoadedSources) -> list[KGEdge]:
    """Map bridge TRANSFERS_TO edges to manual topic -> topic edges."""
    return [
        KGEdge(
            src_kind=edge.src_kind,
            src_ref=edge.src_ref,
            dst_kind=edge.dst_kind,
            dst_ref=edge.dst_ref,
            type="TRANSFERS_TO",
            weight=edge.weight,
            source="manual",
            meta=edge.meta,
        )
        for edge in sources.bridges.transfers_to
    ]


def build_edges(sources: LoadedSources) -> list[KGEdge]:
    """Build P0 KG edges from loaded sources.

    P0 emits only manual bridges:
    - INSTANCE_OF as kc -> concept
    - TRANSFERS_TO as topic -> topic

    REQUIRES_KC, DEVELOPS, and COVERS are intentionally empty in P0.
    Topic prerequisite DAG validation reads from sources.topics, not emitted
    edges, because topic-level prerequisites are stored in the unified schema.
    """
    _validate_topic_requires_dag(sources.topics)
    return [*_manual_instance_of_edges(sources), *_manual_transfer_edges(sources)]


def build(sources: LoadedSources) -> BuildResult:
    """Build concepts and edges from loaded KG sources."""
    return BuildResult(concepts=build_concepts(sources), edges=build_edges(sources))
