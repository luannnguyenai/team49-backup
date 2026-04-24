# Phase 01: KG DB Foundation

## Goal

Make the graph build pipeline depend on authoritative database state rather than recommendation-critical bootstrap files.

This phase exists to answer one question cleanly:

How does the recommendation engine get a stable graph representation of course and learning structure from the database?

## Why This Phase Comes First

The current KG subsystem already has:

- graph tables
- sync logic
- read services
- mastery provider plumbing

But the current course recommendation path still depends on bootstrap files and partial ingestion. That creates two conflicting realities:

- graph logic in DB and KG tables
- course logic in repo JSON bootstrap files

That split must be removed before a serious backend recommendation engine is built.

## Scope

This phase covers:

- DB-first loading inputs for graph build
- explicit sync boundaries
- source-of-truth mapping for graph build inputs
- removal of hidden recommendation-time dependence on file loaders for graph-critical entities

This phase does **not** yet implement a new recommendation engine.

## Current Modules To Reuse

- [src/kg/pipeline.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/pipeline.py:17)
- [src/kg/repository.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/repository.py:192)
- [src/kg/router.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/router.py:61)
- [src/kg/providers.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/providers.py:29)
- [src/services/course_bootstrap_service.py](/D:/VSCODE/VINAI/A20-App-049/src/services/course_bootstrap_service.py:27)
- [src/services/ingestion.py](/D:/VSCODE/VINAI/A20-App-049/src/services/ingestion.py:101)

## New And Modified Modules

### Modify

- `src/kg/loader.py`
  Add DB-backed loaders for topics, KCs, questions, courses, and explicit bridge rows.
- `src/kg/pipeline.py`
  Accept DB-first source loading and phase-aware build modes without assuming file-only sources.
- `src/kg/router.py`
  Expose health and sync behavior that clearly reflects DB-backed source loading.
- `src/services/course_bootstrap_service.py`
  Reduce its role to import/bootstrap only, not recommendation-critical runtime graph source.
- `src/services/ingestion.py`
  Add course metadata import entry points if missing.

### Add

- `src/kg/course_loader.py`
  Dedicated loader for course runtime entities and course-to-topic mappings.
- `src/kg/source_snapshot.py`
  Small typed snapshot models for DB-loaded graph build inputs.
- `tests/kg/test_db_loader.py`
  Unit tests for DB-first source extraction.
- `tests/kg/test_pipeline_db_build.py`
  Integration tests for sync from DB sources into KG tables.

## Recommended File Responsibilities

- `src/kg/loader.py`
  Owns composition of all build sources.
- `src/kg/course_loader.py`
  Owns course-specific DB reads and normalization.
- `src/kg/source_snapshot.py`
  Owns typed intermediate snapshots passed to builder logic.
- `src/kg/pipeline.py`
  Orchestrates load, build, discover, sync.

Keep course loading separate from generic KG loading so later course-aware graph work does not bloat the base loader.

## Data Model Direction

This phase should make the following DB entities explicit graph inputs:

- modules
- topics
- knowledge_components
- questions
- courses
- course overview metadata
- course-unit mappings

If course-to-topic or course-to-KC mappings do not exist yet, this phase must define where they will come from:

- normalized join tables if available
- derived mappings from unit metadata
- explicit import-time mapping tables if neither exists

Do not hide this behind implicit heuristics.

## Build Workflow

### Target Workflow

1. Read published learning entities from DB.
2. Normalize them into typed snapshot structs.
3. Hand snapshots to the graph builder.
4. Generate graph nodes and edges.
5. Run optional discovery only for configured phases.
6. Sync to `kg_concepts`, `kg_edges`, and `kg_sync_state`.

### Guardrails

- No recommendation-critical graph path should depend on runtime file reads.
- Sync must remain idempotent.
- Generated sources may soft-delete stale rows.
- Manual sources must not be auto-deleted.

## API And CLI Surface

This phase may keep the existing `/kg/sync` route, but must make its semantics clearer:

- sync reads DB-backed source-of-truth entities
- sync is safe to rerun
- sync reports created, updated, unchanged, soft-deleted rows

If a CLI sync script exists or is added later, it must call the same pipeline.

## Testing Plan

### Unit Tests

- DB loader returns expected topics, KCs, and courses from seeded rows.
- Loader excludes unpublished or deleted entities.
- Loader output is deterministic for stable DB rows.
- Sync state hashing changes only when normalized content changes.

### Integration Tests

- Running the pipeline inserts expected KG concepts and edges.
- Re-running with no data change yields mostly `unchanged`.
- Removing an auto-generated input soft-deletes stale graph rows.
- Manual bridge rows survive later syncs.

### Regression Tests

- Recommendation-critical graph paths do not call bootstrap file loaders.
- KG sync remains valid when bootstrap files are absent but DB rows exist.

## Suggested Commit Slices

1. `feat: add db-backed kg source snapshot models`
2. `feat: add db-backed kg course loader`
3. `feat: wire db-backed loading into kg pipeline`
4. `test: cover kg db loader and sync behavior`
5. `docs: clarify kg sync source-of-truth boundaries`

## Done When

- KG can be rebuilt from DB-backed learning and course entities.
- Recommendation-critical graph data no longer depends on runtime file loaders.
- Sync is deterministic and idempotent.
- Tests prove DB-first graph materialization works.
