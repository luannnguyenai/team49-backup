# Runtime Cutover To New DB Schema Implementation Plan

> **Historical plan:** This document is preserved for implementation history only. It describes a transitional dual-write/flagged cutover; the active contract is now canonical-only and documented in `README.md` plus `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely wire the running app to the new learner/planner database tables (`goal_preferences`, `learner_mastery_kp`, `waived_units`, `plan_history`, `rationale_log`, `planner_session_state`) without deleting old data and without breaking current production flows.

**Architecture:** Use a staged cutover with compatibility preserved throughout. First add read/write ownership rules and repository helpers, then wire writes into onboarding/assessment/skip/planner flows, then selectively shift read paths to the new tables, and only after parity is verified freeze old writes. No big-bang migration, no early deletes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest

---

## Cutover rules

- **Do not delete old data before cutover.**
- **Do not dual-write silently.** Every temporary dual-write must be explicit and documented.
- **New tables become authoritative one flow at a time.**
- **Old tables remain compatibility surfaces until parity is verified.**
- **Each phase must end with a verification step and commit.**

## Source-of-truth targets

By the end of this plan, the intended authoritative ownership should be:

- user goal/profile for planning → `goal_preferences`
- learner KP mastery → `learner_mastery_kp`
- skip/waive audit → `waived_units`
- planner run snapshot → `plan_history`
- planner explanation per unit → `rationale_log`
- planner counters/session memory → `planner_session_state`
- unit resume state → `learning_progress_records`

Compatibility-only after cutover:

- `mastery_scores`
- `learning_paths`
- `questions`
- `topics`
- `modules`

## File structure

### Files to modify

- `src/models/learning.py`
- `src/repositories/mastery_repo.py`
- `src/repositories/user_repo.py`
- `src/repositories/interaction_repo.py`
- `src/services/auth_service.py`
- `src/services/assessment_service.py`
- `src/services/quiz_service.py`
- `src/services/recommendation_engine.py`
- `src/routers/learning_path.py`
- `src/schemas/auth.py`
- `src/schemas/learning.py`
- `src/schemas/learning_path.py`
- `src/config.py`
- `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`

### Files to create

- `src/repositories/goal_preference_repo.py`
- `src/repositories/waived_unit_repo.py`
- `src/repositories/planner_audit_repo.py`
- `src/repositories/learner_mastery_kp_repo.py`
- `src/services/planner_audit_service.py`
- `tests/repositories/test_goal_preference_repo.py`
- `tests/repositories/test_waived_unit_repo.py`
- `tests/repositories/test_planner_audit_repo.py`
- `tests/repositories/test_learner_mastery_kp_repo.py`
- `tests/services/test_auth_goal_preferences.py`
- `tests/services/test_quiz_mastery_kp_write.py`
- `tests/services/test_skip_waive_audit.py`
- `tests/services/test_planner_audit_write.py`
- `docs/superpowers/specs/2026-04-23-runtime-cutover-handoff.md`

## Phase 0: Safety and observability first

### Task 0.1: Freeze cutover ownership in docs

**Files:**
- Modify: `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`
- Create: `docs/superpowers/specs/2026-04-23-runtime-cutover-handoff.md`

- [ ] Document which runtime flow owns writes to each new table.
- [ ] Document which old tables remain read-compatible during transition.
- [ ] Document temporary dual-write policy if used.
- [ ] Commit docs only.

### Task 0.2: Add feature flags for staged cutover

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

- [ ] Add flags such as:
  - `write_goal_preferences_enabled`
  - `write_learner_mastery_kp_enabled`
  - `write_waived_units_enabled`
  - `write_planner_audit_enabled`
  - `read_goal_preferences_enabled`
  - `read_learner_mastery_kp_enabled`
- [ ] Default write flags to `false` unless explicitly enabled in the environment.
- [ ] Run config tests.
- [ ] Commit.

Current status:
- Done
- Commit: `ae24665` `feat: add cutover flags and planner stub repositories`

## Phase 1: Repository layer for new tables

### Task 1.1: Add goal preference repository

**Files:**
- Create: `src/repositories/goal_preference_repo.py`
- Test: `tests/repositories/test_goal_preference_repo.py`

- [ ] Write failing tests for:
  - upsert by `user_id`
  - get by `user_id`
  - update `selected_course_ids`
- [ ] Run test and verify fail.
- [ ] Implement minimal repository.
- [ ] Re-run tests.
- [ ] Commit.

### Task 1.2: Add learner mastery KP repository

**Files:**
- Create: `src/repositories/learner_mastery_kp_repo.py`
- Test: `tests/repositories/test_learner_mastery_kp_repo.py`

- [ ] Write failing tests for:
  - upsert by `(user_id, kp_id)`
  - bulk fetch by `user_id`
  - safe update of `theta_mu/theta_sigma/mastery_mean_cached`
- [ ] Run test and verify fail.
- [ ] Implement minimal repository.
- [ ] Re-run tests.
- [ ] Commit.

### Task 1.3: Add waived unit repository

**Files:**
- Create: `src/repositories/waived_unit_repo.py`
- Test: `tests/repositories/test_waived_unit_repo.py`

- [ ] Write failing tests for:
  - add waived record
  - list by `user_id`
  - idempotent upsert on `(user_id, learning_unit_id)`
- [ ] Run test and verify fail.
- [ ] Implement minimal repository.
- [ ] Re-run tests.
- [ ] Commit.

### Task 1.4: Add planner audit repository

**Files:**
- Create: `src/repositories/planner_audit_repo.py`
- Test: `tests/repositories/test_planner_audit_repo.py`

- [ ] Write failing tests for:
  - create `plan_history`
  - create `rationale_log` rows for a plan
  - upsert `planner_session_state`
- [ ] Run test and verify fail.
- [ ] Implement minimal repository.
- [ ] Re-run tests.
- [ ] Commit.

Current status for Phase 1:
- Done
- Commit: `ae24665` `feat: add cutover flags and planner stub repositories`

## Phase 2: Write-path cutover

### Task 2.1: Wire onboarding to `goal_preferences`

**Files:**
- Modify: `src/services/auth_service.py`
- Modify: `src/schemas/auth.py`
- Modify: `src/repositories/user_repo.py` if needed
- Test: `tests/services/test_auth_goal_preferences.py`

- [ ] Write failing tests showing onboarding persists:
  - goal weights
  - selected course ids
  - preferred learning scope metadata
- [ ] Run test and verify fail.
- [ ] Under feature flag, write onboarding data to `goal_preferences`.
- [ ] Keep existing `users` fields unchanged for compatibility.
- [ ] Re-run tests.
- [ ] Commit.

Current status:
- Done in compatibility mode
- `update_onboarding()` now writes a legacy onboarding snapshot into `goal_preferences`
- `selected_course_ids` intentionally remains `null` until onboarding becomes course-first

### Task 2.2: Wire assessment/quiz mastery updates to `learner_mastery_kp`

**Files:**
- Modify: `src/services/assessment_service.py`
- Modify: `src/services/quiz_service.py`
- Modify: `src/repositories/mastery_repo.py` only if compatibility helpers are needed
- Test: `tests/services/test_quiz_mastery_kp_write.py`

- [ ] Write failing tests proving a scored interaction can update `learner_mastery_kp`.
- [ ] Use `item_kp_map` / existing item-KP mapping bridge where available.
- [ ] Under feature flag, write to `learner_mastery_kp`.
- [ ] Do **not** stop writing old `mastery_scores` yet unless parity is already checked.
- [ ] Re-run tests.
- [ ] Commit.

Current status:
- Not started by design
- Blocked on missing authoritative runtime bridge from topic/KC grain to canonical `kp_id`

### Task 2.3: Wire skip flow to `waived_units`

**Files:**
- Modify: `src/services/recommendation_engine.py`
- Modify: `src/routers/learning_path.py`
- Test: `tests/services/test_skip_waive_audit.py`

- [ ] Write failing tests that a confirmed skip/waive action creates a `waived_units` row.
- [ ] Require:
  - `learning_unit_id`
  - evidence items if available
  - `mastery_lcb_at_waive` if computed
  - `skip_quiz_score` if applicable
- [ ] Under feature flag, persist `waived_units`.
- [ ] Keep compatibility behavior in `learning_paths` during transition.
- [ ] Re-run tests.
- [ ] Commit.

Current status:
- Not started by design
- Blocked on missing authoritative runtime bridge from topic-grain skip flow to `learning_unit_id`

### Task 2.4: Wire planner writes to audit tables

**Files:**
- Create: `src/services/planner_audit_service.py`
- Modify: `src/services/recommendation_engine.py` or planner entry point in use
- Test: `tests/services/test_planner_audit_write.py`

- [ ] Write failing tests for:
  - creating `plan_history`
  - writing `rationale_log`
  - updating `planner_session_state`
- [ ] Run test and verify fail.
- [ ] Under feature flag, add audit writes around planner generation.
- [ ] Ensure planner can still return its old response shape.
- [ ] Re-run tests.
- [ ] Commit.

Current status:
- Done in compatibility mode
- `generate_learning_path()` now writes topic-grain audit rows into:
  - `plan_history`
  - `rationale_log`
  - `planner_session_state`

## Phase 3: Read-path cutover

### Task 3.1: Read goals from `goal_preferences`

**Files:**
- Modify: planner/service entry points
- Test: extend `tests/services/test_auth_goal_preferences.py` or planner tests

- [ ] Make planner read `goal_preferences` when `read_goal_preferences_enabled=true`.
- [ ] Fallback to old runtime heuristics only if the new row is missing.
- [ ] Document exact fallback behavior.
- [ ] Commit.

### Task 3.2: Read learner mastery from `learner_mastery_kp`

**Files:**
- Modify: planner/assessment read paths
- Test: extend `tests/services/test_quiz_mastery_kp_write.py`

- [ ] Make planner/assessor read `learner_mastery_kp` when `read_learner_mastery_kp_enabled=true`.
- [ ] Explicitly define fallback to old `mastery_scores`.
- [ ] Do not delete or stop updating `mastery_scores` until parity is checked.
- [ ] Commit.

### Task 3.3: Read skip decisions from `waived_units`

**Files:**
- Modify: planner/service entry points
- Test: extend `tests/services/test_skip_waive_audit.py`

- [ ] Use `waived_units` to filter or mark skippable units.
- [ ] Keep `learning_paths.action = skip` as compatibility output only until old consumers are migrated.
- [ ] Commit.

## Phase 4: Parity verification and freeze old writes

### Task 4.1: Add parity checks

**Files:**
- Create/modify verification utilities
- Potentially create tests under `tests/services/` or `tests/repositories/`

- [ ] Compare old vs new read results for:
  - sampled user mastery
  - skip decisions
  - planner output counts
- [ ] Record accepted divergence and explain it.
- [ ] Commit parity tooling if code is added.

### Task 4.2: Freeze old writes selectively

**Files:**
- Modify only after parity is accepted

- [ ] Stop writing compatibility tables one flow at a time:
  - first `learning_paths` for skip audit if `waived_units` is authoritative
  - later `mastery_scores` once `learner_mastery_kp` is trusted
- [ ] Keep read fallback until confidence is high.
- [ ] Commit per flow freeze.

## Phase 5: Final handoff and cleanup gates

### Task 5.1: Produce integrator handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-04-23-runtime-cutover-handoff.md`
- Modify: `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`

- [ ] Document:
  - which feature flag is on/off
  - which tables are authoritative
  - which compatibility writes remain
  - which deprecations are now safe
- [ ] Commit docs.

### Task 5.2: Only after production soak, consider deletions

**Files:**
- Future migrations only, not part of immediate cutover

- [ ] Archive or delete old tables only after:
  - read path cutover is complete
  - write path cutover is complete
  - rollback window has passed

## Acceptance criteria

- [ ] The app still runs throughout the cutover.
- [ ] No old data is deleted before parity.
- [ ] New tables receive authoritative writes in their intended flows.
- [ ] Read paths can be switched by feature flag.
- [ ] Planner and learner audit data is preserved.
- [ ] An engineer integrating the code later can follow the docs without guessing ownership.
