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
