"""Pydantic v2 schemas for the Knowledge Graph module.

All models are immutable (frozen=True). No I/O — pure data containers.
"""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

# ---------------------------------------------------------------------------
# Literal type aliases
# ---------------------------------------------------------------------------

NodeKind = Literal["module", "topic", "kc", "concept", "question", "skill"]
EdgeType = Literal[
    "INSTANCE_OF", "ALIGNS_WITH", "TRANSFERS_TO", "REQUIRES_KC", "DEVELOPS", "COVERS"
]
EdgeSource = Literal["schema", "manual", "embedding", "llm", "heuristic"]
ConceptSource = Literal["manual", "embedding", "llm", "heuristic"]


# ---------------------------------------------------------------------------
# Node schemas
# ---------------------------------------------------------------------------


class KGConcept(BaseModel):
    """A concept node in the Knowledge Graph.

    Args:
        id: Stable UUID for this concept.
        name: Human-readable concept name.
        description: Optional longer explanation.
        canonical_kc_slug: Slug of the KnowledgeComponent this concept maps to.
        source: How this concept was produced.
        embedding_version: Version tag of the embedding model used (None = not embedded).
    """

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    canonical_kc_slug: str | None = None
    source: ConceptSource
    embedding_version: int | None = None


# ---------------------------------------------------------------------------
# Edge schemas
# ---------------------------------------------------------------------------


class KGEdge(BaseModel):
    """A directed, typed edge between two KG nodes.

    Args:
        src_kind: Node kind of the source.
        src_ref: Slug or UUID string identifying the source node.
        dst_kind: Node kind of the destination.
        dst_ref: Slug or UUID string identifying the destination node.
        type: Semantic relationship type.
        weight: Edge strength in [0.0, 1.0].
        source: How this edge was produced.
        meta: Arbitrary extra data (e.g. confidence scores).
    """

    model_config = ConfigDict(frozen=True)

    src_kind: NodeKind
    src_ref: str
    dst_kind: NodeKind
    dst_ref: str
    type: EdgeType
    weight: float
    source: EdgeSource
    meta: dict[str, Any] | None = None

    @field_validator("weight")
    @classmethod
    def _validate_weight(cls, v: float) -> float:
        """Ensure weight is in the closed interval [0.0, 1.0]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"weight must be between 0.0 and 1.0, got {v}")
        return v


# ---------------------------------------------------------------------------
# Loader output schemas
# ---------------------------------------------------------------------------


class KCRef(BaseModel):
    """Flattened reference to a KnowledgeComponent — loader output.

    Args:
        slug: Unique KC identifier.
        topic_slug: Parent topic slug.
        module_slug: Grandparent module slug.
        name: Display name.
        description: Optional explanation.
    """

    model_config = ConfigDict(frozen=True)

    slug: str
    topic_slug: str
    module_slug: str
    name: str
    description: str | None = None


class TopicRef(BaseModel):
    """Flattened reference to a Topic — loader output.

    Args:
        slug: Unique topic identifier.
        module_slug: Parent module slug.
        name: Display name.
        prerequisite_topic_slugs: Ordered tuple of prerequisite topic slugs.
    """

    model_config = ConfigDict(frozen=True)

    slug: str
    module_slug: str
    name: str
    prerequisite_topic_slugs: tuple[str, ...]


class BridgesDoc(BaseModel):
    """Parsed and validated kg_bridges.yaml document.

    Args:
        concepts: Concept nodes declared in the bridges file.
        instance_of: Edges asserting concept→kc membership.
        transfers_to: Edges asserting transfer-of-learning between nodes.
    """

    model_config = ConfigDict(frozen=True)

    concepts: tuple[KGConcept, ...]
    instance_of: tuple[KGEdge, ...]
    transfers_to: tuple[KGEdge, ...]

    @field_validator("instance_of")
    @classmethod
    def _validate_instance_of_edges(cls, edges: tuple[KGEdge, ...]) -> tuple[KGEdge, ...]:
        """All instance_of edges must go from concept → kc."""
        for edge in edges:
            if edge.src_kind != "concept":
                raise ValueError(
                    f'instance_of edges must have src_kind="concept", got "{edge.src_kind}"'
                )
            if edge.dst_kind != "kc":
                raise ValueError(
                    f'instance_of edges must have dst_kind="kc", got "{edge.dst_kind}"'
                )
        return edges


class LoadedSources(BaseModel):
    """All data loaded from source files by the KG builder.

    Args:
        topics: All topic references from curriculum data.
        kcs: All KC references from curriculum data.
        questions: Raw question dicts (typed further in Phase 1).
        bridges: Parsed bridges YAML document.
    """

    model_config = ConfigDict(frozen=True)

    topics: tuple[TopicRef, ...]
    kcs: tuple[KCRef, ...]
    questions: tuple[dict[str, Any], ...]
    bridges: BridgesDoc


# ---------------------------------------------------------------------------
# Sync result schema
# ---------------------------------------------------------------------------


class SyncReport(BaseModel):
    """Summary of a KG sync operation.

    Args:
        created: Entity refs that were inserted.
        updated: Entity refs that were updated (hash changed).
        unchanged: Entity refs that required no change.
        soft_deleted: Entity refs that were marked is_deleted=true.
    """

    model_config = ConfigDict(frozen=True)

    created: tuple[str, ...]
    updated: tuple[str, ...]
    unchanged: tuple[str, ...]
    soft_deleted: tuple[str, ...]
