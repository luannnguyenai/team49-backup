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
        prerequisite_topic_slugs: Ordered list of prerequisite topic slugs.
    """

    model_config = ConfigDict(frozen=True)

    slug: str
    module_slug: str
    name: str
    prerequisite_topic_slugs: list[str]


class BridgesDoc(BaseModel):
    """Parsed and validated kg_bridges.yaml document.

    Args:
        concepts: Concept nodes declared in the bridges file.
        instance_of: Edges asserting concept→kc membership.
        transfers_to: Edges asserting transfer-of-learning between nodes.
    """

    model_config = ConfigDict(frozen=True)

    concepts: list[KGConcept]
    instance_of: list[KGEdge]
    transfers_to: list[KGEdge]

    @field_validator("instance_of")
    @classmethod
    def _validate_instance_of_edges(cls, edges: list[KGEdge]) -> list[KGEdge]:
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
