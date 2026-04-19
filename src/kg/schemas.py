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
