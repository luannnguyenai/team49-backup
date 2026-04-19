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
