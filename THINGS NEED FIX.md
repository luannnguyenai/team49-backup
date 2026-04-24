# THINGS NEED FIX

Date: 2026-04-23
Branch: `rin/implement`

## Completed Baseline

These are already done and should not be reopened without a deliberate design decision:

- Canonical content is imported into DB and parity checker is `ready`.
- Product shell links to canonical units.
- Assessment, quiz, and module-test runtime are canonical-only.
- `learner_mastery_kp`, `goal_preferences`, `waived_units`, `plan_history`, `rationale_log`, and `planner_session_state` exist in ORM + DB.
- Legacy runtime tables were dropped from DB:
  - `modules`
  - `topics`
  - `knowledge_components`
  - `questions`
  - `mastery_scores`
  - `mastery_history`
  - `learning_paths`
- Legacy KG runtime package `src/kg/*` was removed.
- Legacy config allow-flags were removed.
- Frontend production build passes after canonical cutover.
- Canonical route/service regression tests pass for quiz, module-test, learning-path status, assessment mastery, and content contracts.
- Course discovery/gating Playwright e2e passes against canonical course/unit labels.
- Signed protected asset route now guards `data/courses/<course>/videos|slides|transcripts` paths.

## Remaining Work

### 1. Historical Docs Sweep

Current state:

- Runtime and DB cutover for canonical unit/section semantics is complete.
- Planner progress now writes to `learning_progress_records`.
- Skip audit now writes to `waived_units`.
- Main schema/handoff docs were refreshed.
- Runtime build/e2e smoke is green for the canonical course flow.

Needed:

- Sweep older notes/specs and mark transitional guidance as historical where needed.
- Remove any leftover instruction that still tells engineers to rely on dropped legacy curriculum/mastery tables.

Acceptance:

- New engineer reading the repo cannot mistake legacy tables for active production tables.
