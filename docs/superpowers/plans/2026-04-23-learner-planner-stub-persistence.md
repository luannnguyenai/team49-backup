# Learner And Planner Stub Persistence Implementation Plan

> **Historical plan:** This document is preserved for implementation history only. Learner/planner tables now exist and runtime writes canonical state; use the current handoff docs as authority.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add six minimal persistence tables for learner KP mastery, goal preferences, waived units, and planner audit/session state without rewiring the current runtime planner.

**Architecture:** Keep the existing topic/module runtime intact and add sidecar ORM tables plus one Alembic migration. Cover the new schema with lightweight model/migration tests instead of service-level planner logic.

**Tech Stack:** Python 3.12, SQLAlchemy, Alembic, pytest, PostgreSQL

---

### Task 1: Add learner mastery KP and goal preferences

**Files:**
- Modify: `src/models/learning.py`
- Modify: `src/models/__init__.py`
- Create: `tests/test_learner_planner_stub_models.py`
- Create: `alembic/versions/20260423_learner_planner_stub_persistence.py`

- [ ] Write failing tests for `LearnerMasteryKP` and `GoalPreference`
- [ ] Run targeted tests and verify failure
- [ ] Add minimal ORM models and re-export them
- [ ] Add matching Alembic create/drop for both tables
- [ ] Run targeted tests until green
- [ ] Commit

### Task 2: Add waived units

**Files:**
- Modify: `src/models/learning.py`
- Modify: `src/models/__init__.py`
- Modify: `tests/test_learner_planner_stub_models.py`
- Modify: `alembic/versions/20260423_learner_planner_stub_persistence.py`

- [ ] Write failing tests for `WaivedUnit`
- [ ] Run targeted tests and verify failure
- [ ] Add minimal ORM model
- [ ] Extend migration for `waived_units`
- [ ] Run targeted tests until green
- [ ] Commit

### Task 3: Add planner history, rationale log, planner session state

**Files:**
- Modify: `src/models/learning.py`
- Modify: `src/models/__init__.py`
- Modify: `tests/test_learner_planner_stub_models.py`
- Modify: `alembic/versions/20260423_learner_planner_stub_persistence.py`
- Create: `tests/test_learner_planner_stub_migration.py`

- [ ] Write failing tests for `PlanHistory`, `RationaleLog`, `PlannerSessionState`
- [ ] Run targeted tests and verify failure
- [ ] Add minimal ORM models and relationships
- [ ] Extend migration for the remaining three tables
- [ ] Add migration text assertions
- [ ] Run targeted tests until green
- [ ] Commit

### Task 4: Verify schema integration

**Files:**
- Modify: none expected unless fixes are needed

- [ ] Run targeted tests for new models/migration
- [ ] Run `tests/test_alembic_heads.py`
- [ ] Fix any integration issues
- [ ] Commit only if code changed
