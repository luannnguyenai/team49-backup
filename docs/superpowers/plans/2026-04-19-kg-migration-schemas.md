# KG Phase 0 — Migration + Pydantic Schemas Implementation Plan

> **Historical plan:** This document is preserved for implementation history only. Legacy KG runtime code has been removed; use canonical `prerequisite_edges` and the current handoff docs for production graph work.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the Alembic migration for 3 KG tables and the full Pydantic v2 schema layer for the Knowledge Graph module.

**Architecture:** New package `src/kg/` holds all KG business logic; Alembic migration adds `kg_concepts`, `kg_edges`, `kg_sync_state` to PostgreSQL; Pydantic schemas are pure immutable data containers (no I/O, no ORM). Tests live in `tests/kg/` following the project's `testpaths = ["tests"]` convention.

**Tech Stack:** Python 3.11, Pydantic v2, SQLAlchemy 2.x (Alembic op API), PostgreSQL 15 + pgvector (extension already enabled), pytest

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/kg/__init__.py` | Package marker |
| Create | `src/kg/schemas.py` | All KG Pydantic v2 types |
| Create | `tests/kg/__init__.py` | Test package marker |
| Create | `tests/kg/test_schemas.py` | Schema validation + round-trip tests |
| Create | `alembic/versions/20260419_kg_init.py` | Migration: create/drop 3 KG tables |

**Do not touch any other file.**

---

## Task 1: Scaffold `src/kg/` Package

**Files:**
- Create: `src/kg/__init__.py`
- Create: `tests/kg/__init__.py`

- [ ] **Step 1: Create package markers**

```bash
mkdir -p src/kg tests/kg
touch src/kg/__init__.py tests/kg/__init__.py
```

- [ ] **Step 2: Verify structure**

```bash
ls src/kg/ tests/kg/
```

Expected output:
```
src/kg/:
__init__.py

tests/kg/:
__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add src/kg/__init__.py tests/kg/__init__.py
git commit -m "chore: scaffold src/kg package and tests/kg directory"
```

---

## Task 2: Write Failing Tests for Pydantic Schemas

**Files:**
- Create: `tests/kg/test_schemas.py`

- [ ] **Step 1: Write the test file**

Create `tests/kg/test_schemas.py` with this exact content:

```python
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
```

- [ ] **Step 2: Run tests — expect ImportError (module doesn't exist yet)**

```bash
pytest tests/kg/test_schemas.py -v 2>&1 | head -30
```

Expected: `ImportError: No module named 'src.kg.schemas'` — confirms tests are wired correctly.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/kg/test_schemas.py
git commit -m "test(kg): add failing schema validation and round-trip tests"
```

---

## Task 3: Implement `src/kg/schemas.py`

**Files:**
- Create: `src/kg/schemas.py`

- [ ] **Step 1: Write the schemas module**

Create `src/kg/schemas.py` with this exact content:

```python
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


class LoadedSources(BaseModel):
    """All data loaded from source files by the KG builder.

    Args:
        topics: All topic references from curriculum data.
        kcs: All KC references from curriculum data.
        questions: Raw question dicts (typed further in Phase 1).
        bridges: Parsed bridges YAML document.
    """

    model_config = ConfigDict(frozen=True)

    topics: list[TopicRef]
    kcs: list[KCRef]
    questions: list[dict[str, Any]]
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

    created: list[str]
    updated: list[str]
    unchanged: list[str]
    soft_deleted: list[str]
```

- [ ] **Step 2: Run tests — expect all pass**

```bash
pytest tests/kg/test_schemas.py -v
```

Expected output (all green):
```
tests/kg/test_schemas.py::TestKGEdgeWeight::test_weight_above_one_raises PASSED
tests/kg/test_schemas.py::TestKGEdgeWeight::test_weight_negative_raises PASSED
tests/kg/test_schemas.py::TestKGEdgeWeight::test_weight_boundary_zero_accepted PASSED
tests/kg/test_schemas.py::TestKGEdgeWeight::test_weight_boundary_one_accepted PASSED
tests/kg/test_schemas.py::TestBridgesDocValidator::test_invalid_src_kind_in_instance_of_raises PASSED
tests/kg/test_schemas.py::TestBridgesDocValidator::test_invalid_dst_kind_in_instance_of_raises PASSED
tests/kg/test_schemas.py::TestBridgesDocValidator::test_valid_bridges_doc_accepted PASSED
tests/kg/test_schemas.py::TestBridgesDocValidator::test_empty_instance_of_accepted PASSED
tests/kg/test_schemas.py::TestRoundTrips::test_kg_concept_round_trip PASSED
tests/kg/test_schemas.py::TestRoundTrips::test_kg_edge_round_trip PASSED
tests/kg/test_schemas.py::TestRoundTrips::test_sync_report_all_empty_valid PASSED
tests/kg/test_schemas.py::TestRoundTrips::test_loaded_sources_round_trip PASSED
tests/kg/test_schemas.py::TestFrozenModels::test_kg_concept_is_immutable PASSED
tests/kg/test_schemas.py::TestFrozenModels::test_kg_edge_is_immutable PASSED
tests/kg/test_schemas.py::TestFrozenModels::test_kc_ref_is_immutable PASSED

15 passed
```

If any test fails, fix `src/kg/schemas.py` only — do not change the test file.

- [ ] **Step 3: Check coverage**

```bash
pytest tests/kg/test_schemas.py --cov=src/kg/schemas --cov-report=term-missing
```

Expected: `TOTAL` line shows ≥ 80% coverage.

- [ ] **Step 4: Commit**

```bash
git add src/kg/schemas.py
git commit -m "feat(kg): add Pydantic v2 schemas for KG module"
```

---

## Task 4: Alembic Migration — Create KG Tables

**Files:**
- Create: `alembic/versions/20260419_kg_init.py`

- [ ] **Step 1: Write the migration file**

Create `alembic/versions/20260419_kg_init.py` with this exact content:

```python
"""Create Knowledge Graph tables: kg_concepts, kg_edges, kg_sync_state.

Revision ID: 20260419_kg_init
Revises: 20260419_merge_final
Create Date: 2026-04-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import UserDefinedType

revision: str = "20260419_kg_init"
down_revision: str = "20260419_merge_final"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NODE_KIND = ("module", "topic", "kc", "concept", "question", "skill")
_EDGE_TYPE = (
    "INSTANCE_OF", "ALIGNS_WITH", "TRANSFERS_TO",
    "REQUIRES_KC", "DEVELOPS", "COVERS",
)
_EDGE_SOURCE = ("schema", "manual", "embedding", "llm", "heuristic")
_CONCEPT_SOURCE = ("manual", "embedding", "llm", "heuristic")


class _Vector(UserDefinedType):
    """Inline vector type wrapper for pgvector — migration use only.

    Args:
        dim: Embedding dimensionality (e.g. 1536 for text-embedding-ada-002).
    """

    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: object) -> str:
        """Return the PostgreSQL column type string."""
        return f"vector({self.dim})"


def upgrade() -> None:
    """Create kg_concepts, kg_edges, kg_sync_state with all indexes and constraints."""
    bind = op.get_bind()

    # Create enum types (checkfirst prevents errors on repeated runs)
    sa.Enum(*_NODE_KIND, name="node_kind_enum").create(bind, checkfirst=True)
    sa.Enum(*_EDGE_TYPE, name="edge_type_enum").create(bind, checkfirst=True)
    sa.Enum(*_EDGE_SOURCE, name="edge_source_enum").create(bind, checkfirst=True)
    sa.Enum(*_CONCEPT_SOURCE, name="concept_source_enum").create(bind, checkfirst=True)

    # ------------------------------------------------------------------ kg_concepts
    op.create_table(
        "kg_concepts",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("canonical_kc_slug", sa.String(100), nullable=True),
        sa.Column(
            "source",
            sa.Enum(*_CONCEPT_SOURCE, name="concept_source_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("embedding_version", sa.Integer(), nullable=True),
        sa.Column("embedding", _Vector(1536), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_kg_concepts_canonical_kc_slug", "kg_concepts", ["canonical_kc_slug"])
    op.create_index("ix_kg_concepts_is_deleted", "kg_concepts", ["is_deleted"])

    # ------------------------------------------------------------------ kg_edges
    op.create_table(
        "kg_edges",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "src_kind",
            sa.Enum(*_NODE_KIND, name="node_kind_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("src_ref", sa.Text(), nullable=False),
        sa.Column(
            "dst_kind",
            sa.Enum(*_NODE_KIND, name="node_kind_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("dst_ref", sa.Text(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(*_EDGE_TYPE, name="edge_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column(
            "source",
            sa.Enum(*_EDGE_SOURCE, name="edge_source_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("meta", JSONB(), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "src_kind", "src_ref", "dst_kind", "dst_ref", "type",
            name="uq_kg_edges_src_dst_type",
        ),
        sa.CheckConstraint("weight >= 0.0 AND weight <= 1.0", name="ck_kg_edges_weight"),
    )
    op.create_index("ix_kg_edges_src", "kg_edges", ["src_kind", "src_ref"])
    op.create_index("ix_kg_edges_dst", "kg_edges", ["dst_kind", "dst_ref"])
    op.create_index("ix_kg_edges_type", "kg_edges", ["type"])
    op.create_index("ix_kg_edges_is_deleted", "kg_edges", ["is_deleted"])

    # ------------------------------------------------------------------ kg_sync_state
    op.create_table(
        "kg_sync_state",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_ref", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "synced_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="'ok'"),
        sa.UniqueConstraint("entity_type", "entity_ref", name="uq_kg_sync_state_entity"),
    )
    op.create_index("ix_kg_sync_state_entity_type", "kg_sync_state", ["entity_type"])
    op.create_index("ix_kg_sync_state_synced_at", "kg_sync_state", ["synced_at"])


def downgrade() -> None:
    """Drop all KG tables and enum types in reverse order."""
    op.drop_table("kg_sync_state")
    op.drop_table("kg_edges")
    op.drop_table("kg_concepts")

    bind = op.get_bind()
    sa.Enum(name="concept_source_enum").drop(bind, checkfirst=True)
    sa.Enum(name="edge_source_enum").drop(bind, checkfirst=True)
    sa.Enum(name="edge_type_enum").drop(bind, checkfirst=True)
    sa.Enum(name="node_kind_enum").drop(bind, checkfirst=True)
```

- [ ] **Step 2: Upgrade to new head**

```bash
alembic upgrade head
```

Expected: Migration runs without error. Last line should be:
```
INFO  [alembic.runtime.migration] Running upgrade 20260419_merge_final -> 20260419_kg_init, Create Knowledge Graph tables: kg_concepts, kg_edges, kg_sync_state.
```

If you see `ERROR`: check DB connection in `.env` (`DATABASE_URL`) and that pgvector extension is active (`SELECT * FROM pg_extension WHERE extname='vector';`).

- [ ] **Step 3: Downgrade one step**

```bash
alembic downgrade -1
```

Expected:
```
INFO  [alembic.runtime.migration] Running downgrade 20260419_kg_init -> 20260419_merge_final, Create Knowledge Graph tables...
```

Verify tables are gone:
```bash
alembic current
```

Expected: `20260419_merge_final (head)`

- [ ] **Step 4: Re-upgrade (idempotency check)**

```bash
alembic upgrade head
```

Expected: Same success as Step 2. No errors about duplicate types or tables.

- [ ] **Step 5: Verify current head**

```bash
alembic current
```

Expected: `20260419_kg_init (head)`

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/20260419_kg_init.py
git commit -m "feat(kg): add Alembic migration for kg_concepts, kg_edges, kg_sync_state"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ `alembic/versions/20260419_kg_init.py` — Task 4
- ✅ `kg_concepts`, `kg_edges`, `kg_sync_state` DDL — Task 4 Step 1
- ✅ pgvector extension NOT re-created (already enabled by schema_v1 migration)
- ✅ Indexes + CHECK constraints per design — Task 4 Step 1
- ✅ `upgrade()` + `downgrade()` — Task 4 Step 1
- ✅ `NodeKind`, `EdgeType`, `EdgeSource`, `ConceptSource` Literals — Task 3 Step 1
- ✅ `KGConcept`, `KGEdge`, `KCRef`, `TopicRef`, `LoadedSources`, `SyncReport`, `BridgesDoc` — Task 3 Step 1
- ✅ `model_config = ConfigDict(frozen=True)` on all models — Task 3 Step 1
- ✅ `BridgesDoc` validator for `instance_of` edges — Task 3 Step 1
- ✅ `test_schemas.py` validation fail cases + round-trip — Task 2 Step 1
- ✅ `down_revision = "20260419_merge_final"` — Task 4 Step 1

**Path adjustment documented:** All `app/kg/` → `src/kg/`, `app/kg/tests/` → `tests/kg/` (due to `testpaths = ["tests"]` in `pyproject.toml`).
