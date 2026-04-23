# Production DB Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the database toward a production-ready source-of-truth split where canonical content, learner KP mastery, skip audit, and planner audit have first-class tables, while old runtime tables remain as compatibility surfaces until cutover is complete.

**Architecture:** Do this as a staged database-first migration. First finish schema landing zones, then materialize canonical JSONL into real DB tables, then add backfill/import paths, then hand off explicit read/write cutover contracts to the engineer wiring services and routers. Avoid big-bang replacement of the current topic/module runtime.

**Tech Stack:** PostgreSQL, SQLAlchemy, Alembic, Python 3.12, canonical JSONL artifacts under `data/final_artifacts/cs224n_cs231n_v1/canonical/`

---

## Scope of this plan

Plan này ưu tiên:

- database schema
- migration order
- backfill/import strategy
- contract handoff cho người nối code

Plan này **không** giả định rằng cùng một người sẽ:

- sửa service/router
- nối frontend
- cắt read/write paths trong runtime

## File Structure

### Files that already define the current state

- `src/models/content.py`
- `src/models/course.py`
- `src/models/learning.py`
- `src/models/store.py`
- `alembic/versions/20260423_learner_planner_stub_persistence.py`
- `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`
- `docs/superpowers/specs/2026-04-23-production-db-evolution-design.md`
- `data/final_artifacts/cs224n_cs231n_v1/canonical/manifest.json`

### Files expected to be created in later implementation work

- ORM models for:
  - `concepts_kp`
  - `unit_kp_map`
  - `question_bank`
  - `item_calibration`
  - `item_phase_map`
  - `item_kp_map`
  - `prerequisite_edges`
  - `pruned_edges`
- Alembic migrations for those tables
- importer/backfill scripts
- validation checks for DB row counts vs canonical manifest

## Migration principles

1. **Canonical JSONL is the ingestion contract, not the long-term source-of-truth.**
2. **Compatibility tables stay until read/write cutover is complete.**
3. **Backfill is idempotent.**
4. **Audit tables are not optional.**
5. **No silent dual-write.**

## Phase plan

### Task 1: Freeze authoritative ownership table-by-table

**Files:**
- Review: `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`
- Review: `docs/superpowers/specs/2026-04-23-production-db-evolution-design.md`
- Update when needed: handoff docs only

- [ ] Confirm the authoritative table for each concern:
  - goal selection → `goal_preferences`
  - KP mastery → `learner_mastery_kp`
  - skip audit → `waived_units`
  - planner run → `plan_history`
  - planner explainability → `rationale_log`
  - planner transient state → `planner_session_state`
  - unit progress/resume → `learning_progress_records`
  - concept graph → `concepts_kp`
  - Q-matrix → `item_kp_map`
  - prerequisite graph → `prerequisite_edges`
- [ ] Record any deviations explicitly in docs before any service integration starts.
- [ ] Commit documentation-only changes if ownership decisions move.

### Task 2: Materialize canonical content layer in PostgreSQL

**Files:**
- Create: new ORM models under `src/models/`
- Create: new Alembic migration(s)
- Create: tests for model existence / Alembic shape

- [ ] Add ORM tables for:
  - `concepts_kp`
  - `unit_kp_map`
  - `question_bank`
  - `item_calibration`
  - `item_phase_map`
  - `item_kp_map`
  - `prerequisite_edges`
  - `pruned_edges`
- [ ] Preserve canonical provenance fields needed for audit:
  - `source_file`
  - `provenance`
  - `review_status` where applicable
  - `p5_trace` or equivalent adjudication trace
- [ ] Add indexes around:
  - `kp_id`
  - `unit_id`
  - `item_id`
  - `(source_kp_id, target_kp_id)`
- [ ] Ensure the schema can hold nullable reserve fields such as:
  - embeddings
  - edge strength
  - bidirectional score
  - future calibration timestamps
- [ ] Commit after the migration and model tests pass.

### Task 3: Build DB import/backfill from canonical JSONL

**Files:**
- Create: importer/backfill script(s)
- Create: tests or verification scripts against canonical counts
- Read: `data/final_artifacts/cs224n_cs231n_v1/canonical/manifest.json`

- [ ] Implement import order that respects dependencies:
  1. `courses` projection or course mapping
  2. `concepts_kp`
  3. `units`
  4. `unit_kp_map`
  5. `question_bank`
  6. `item_calibration`
  7. `item_phase_map`
  8. `item_kp_map`
  9. `prerequisite_edges`
  10. `pruned_edges`
- [ ] Make reruns idempotent with deterministic upsert keys.
- [ ] Verify DB row counts against canonical manifest counts.
- [ ] Fail loudly if FK-like references do not resolve.
- [ ] Commit importer scripts and verification utilities.

### Task 4: Define compatibility mapping for old runtime tables

**Files:**
- Create or update: migration notes / integration handoff docs
- Review: `src/models/content.py`
- Review: `src/models/learning.py`

- [ ] Define how old runtime tables coexist during transition:
  - `mastery_scores` remains compatibility only
  - `learning_paths` remains compatibility only
  - `questions` remains compatibility only
  - `topics/modules` remain compatibility only
- [ ] Define explicit “do not write here for new features” rules.
- [ ] Define whether read adapters or DB views will be used during cutover.
- [ ] Commit the compatibility note when finalized.

### Task 5: Prepare learner/planner write contracts

**Files:**
- Review: `src/models/learning.py`
- Create/update: handoff docs for integrator

- [ ] Define write contracts:
  - onboarding writes `goal_preferences`
  - assessor writes `learner_mastery_kp`
  - skip verification writes `waived_units`
  - planner writes `plan_history`
  - planner writes `rationale_log`
  - planner updates `planner_session_state`
- [ ] For each contract, document:
  - trigger event
  - required payload
  - idempotency key or uniqueness rule
  - whether old tables are also written during transition
- [ ] Commit documentation-only changes.

### Task 6: Handoff package for the code integrator

**Files:**
- Update: `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`
- Update: `docs/superpowers/specs/2026-04-23-production-db-evolution-design.md`
- Update or create: one concise integration checklist doc if needed

- [ ] Produce a short checklist the integrator can follow:
  - which tables to read
  - which tables to write
  - which legacy tables not to touch
  - required migration ordering
  - required count/consistency checks
- [ ] Ensure no table ownership is ambiguous by the end of the handoff.
- [ ] Commit the handoff docs.

## Acceptance criteria

This production DB improvement track is ready for the next engineer when:

- [ ] all learner/planner stub tables exist in DB schema
- [ ] canonical content graph tables exist in DB schema
- [ ] canonical JSONL can be imported into DB reproducibly
- [ ] authoritative ownership is documented table-by-table
- [ ] compatibility tables are clearly marked as transitional
- [ ] an integrator can wire services without guessing which table is the source-of-truth

## Explicit non-goals for the DB-only phase

- no service-layer cutover
- no router rewiring
- no frontend changes
- no silent backfill into old runtime tables
- no deprecation/removal of legacy tables yet

## Integrator handoff notes

The next engineer should not start from runtime code and infer the database shape. They should start from:

1. `docs/superpowers/specs/2026-04-23-production-db-evolution-design.md`
2. `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`
3. canonical manifest/counts under `data/final_artifacts/cs224n_cs231n_v1/canonical/`

Then wire code in this order:

1. read from new authoritative tables
2. write to new authoritative tables
3. keep compatibility writes only where explicitly documented
4. remove or freeze old paths only after parity is proven
