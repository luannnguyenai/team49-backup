# KG Phase 0 — Migration + Pydantic Schemas Design

> **Historical spec:** This document is preserved for implementation history only. Legacy KG runtime code has been removed; use canonical `prerequisite_edges` and the current handoff docs for production graph work.

**Date:** 2026-04-19
**Scope:** Task 1 of Knowledge Graph module — Alembic migration + Pydantic v2 schemas  
**Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x async, Alembic, Pydantic v2, PostgreSQL 15 + pgvector

---

## 1. Constraints (must not violate)

- All new files under `src/kg/**` only. Exception: mount router in `src/api/app.py` (2 lines only).
- No duplicate tables. `modules`, `topics`, `knowledge_components`, `questions` already exist.
- No imports from `src.assessment` or `src.tutor` directly.
- All public functions: full type hints + Google-style docstrings.
- Business logic in pure functions; I/O in repository/providers.
- Alembic migration must be reversible (`upgrade` + `downgrade`).
- pgvector extension already enabled — do not CREATE EXTENSION again.
- No hardcoded secrets/URLs/paths — use `src.config.settings`.
- Phase 0 Protocol implementations: no-op or rule-based, no external API calls.

---

## 2. File Map

| File | Purpose |
|---|---|
| `alembic/versions/20260419_kg_init.py` | Create kg_concepts, kg_edges, kg_sync_state |
| `src/kg/__init__.py` | Package marker |
| `src/kg/schemas.py` | Pydantic v2 schemas for all KG types |
| `src/kg/tests/__init__.py` | Package marker |
| `src/kg/tests/test_schemas.py` | Validation fail cases + round-trip tests |

`down_revision` for migration = `"20260419_merge_final"` (current Alembic head).

---

## 3. DDL Design

### 3.1 Enum types (created in migration, dropped on downgrade)

| PG type name | Values |
|---|---|
| `node_kind_enum` | `module`, `topic`, `kc`, `concept`, `question`, `skill` |
| `edge_type_enum` | `INSTANCE_OF`, `ALIGNS_WITH`, `TRANSFERS_TO`, `REQUIRES_KC`, `DEVELOPS`, `COVERS` |
| `edge_source_enum` | `schema`, `manual`, `embedding`, `llm`, `heuristic` |
| `concept_source_enum` | `manual`, `embedding`, `llm`, `heuristic` |

### 3.2 `kg_concepts`

```sql
id                UUID        PRIMARY KEY DEFAULT gen_random_uuid()
name              TEXT        NOT NULL
description       TEXT
canonical_kc_slug VARCHAR(100)            -- soft FK → knowledge_components.slug
source            concept_source_enum NOT NULL
embedding_version INTEGER
embedding         vector(1536)            -- NULL until Phase 1 populates
is_deleted        BOOLEAN     NOT NULL DEFAULT false
created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
```

Indexes: `(canonical_kc_slug)`, `(is_deleted)`, IVFFlat on `(embedding)` deferred to Phase 1.

### 3.3 `kg_edges`

```sql
id         UUID    PRIMARY KEY DEFAULT gen_random_uuid()
src_kind   node_kind_enum  NOT NULL
src_ref    TEXT            NOT NULL
dst_kind   node_kind_enum  NOT NULL
dst_ref    TEXT            NOT NULL
type       edge_type_enum  NOT NULL
weight     FLOAT           NOT NULL DEFAULT 1.0
source     edge_source_enum NOT NULL
meta       JSONB
is_deleted BOOLEAN         NOT NULL DEFAULT false
created_at TIMESTAMPTZ     NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ     NOT NULL DEFAULT now()
```

Constraints:
- `UNIQUE (src_kind, src_ref, dst_kind, dst_ref, type)`
- `CHECK (weight >= 0.0 AND weight <= 1.0)`

Indexes: `(src_kind, src_ref)`, `(dst_kind, dst_ref)`, `(type)`, `(is_deleted)`

### 3.4 `kg_sync_state`

```sql
id           UUID    PRIMARY KEY DEFAULT gen_random_uuid()
entity_type  TEXT    NOT NULL   -- 'module','topic','kc','question'
entity_ref   TEXT    NOT NULL   -- slug
content_hash TEXT    NOT NULL   -- SHA-256 for idempotency
synced_at    TIMESTAMPTZ NOT NULL DEFAULT now()
status       TEXT    NOT NULL DEFAULT 'ok'  -- 'ok','error','skipped'
```

Constraints:
- `UNIQUE (entity_type, entity_ref)`

Indexes: `(entity_type)`, `(synced_at)`

---

## 4. Pydantic v2 Schemas (`src/kg/schemas.py`)

All models use `model_config = ConfigDict(frozen=True)`.

### Literals / Enums

```python
NodeKind     = Literal['module','topic','kc','concept','question','skill']
EdgeType     = Literal['INSTANCE_OF','ALIGNS_WITH','TRANSFERS_TO','REQUIRES_KC','DEVELOPS','COVERS']
EdgeSource   = Literal['schema','manual','embedding','llm','heuristic']
ConceptSource = Literal['manual','embedding','llm','heuristic']
```

### Models

| Model | Key fields |
|---|---|
| `KGConcept` | `id: UUID`, `name: str`, `description: str\|None`, `canonical_kc_slug: str\|None`, `source: ConceptSource`, `embedding_version: int\|None` |
| `KGEdge` | `src_kind: NodeKind`, `src_ref: str`, `dst_kind: NodeKind`, `dst_ref: str`, `type: EdgeType`, `weight: float` (0–1), `source: EdgeSource`, `meta: dict[str,Any]\|None` |
| `KCRef` | `slug: str`, `topic_slug: str`, `module_slug: str`, `name: str`, `description: str\|None` |
| `TopicRef` | `slug: str`, `module_slug: str`, `name: str`, `prerequisite_topic_slugs: list[str]` |
| `LoadedSources` | `topics: list[TopicRef]`, `kcs: list[KCRef]`, `questions: list[...]`, `bridges: BridgesDoc` |
| `SyncReport` | `created: list[str]`, `updated: list[str]`, `unchanged: list[str]`, `soft_deleted: list[str]` |
| `BridgesDoc` | `concepts: list[KGConcept]`, `instance_of: list[KGEdge]`, `transfers_to: list[KGEdge]` |

`BridgesDoc` validator: all edges in `instance_of` must have `src_kind='concept'` and `dst_kind='kc'`.

`KGEdge` validator: `weight` in `[0.0, 1.0]`.

---

## 5. Tests (`src/kg/tests/test_schemas.py`)

Coverage target: ≥ 80% of schema logic.

| Test | What it checks |
|---|---|
| `test_kg_edge_weight_out_of_range` | `weight=1.5` → `ValidationError` |
| `test_kg_edge_weight_negative` | `weight=-0.1` → `ValidationError` |
| `test_bridges_doc_invalid_instance_of_src_kind` | edge with `src_kind='topic'` in `instance_of` → `ValidationError` |
| `test_bridges_doc_invalid_instance_of_dst_kind` | edge with `dst_kind='topic'` in `instance_of` → `ValidationError` |
| `test_kg_concept_round_trip` | valid concept serializes → deserializes → equal |
| `test_kg_edge_round_trip` | valid edge serializes → deserializes → equal |
| `test_sync_report_empty` | all-empty lists is valid |
| `test_loaded_sources_round_trip` | full LoadedSources round-trip |
| `test_frozen_model_immutable` | assignment after creation raises `ValidationError` or `TypeError` |

---

## 6. Reversibility Guarantee

`downgrade()` drops tables in reverse FK order, then drops all 4 enum types.  
Running `upgrade → downgrade → upgrade` must produce identical state.

---

## 7. Out of Scope (Phase 1)

- ORM model classes for KG tables (needed for SQLAlchemy queries)
- `MasteryProvider`, repository layer, `build_kg.py` script
- Vector embedding population
- API router (`src/api/kg/`)
- Frontend components
