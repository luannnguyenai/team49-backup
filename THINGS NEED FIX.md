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

## Remaining Work

### 1. Historical Docs Sweep

Current state:

- Runtime and DB cutover for canonical unit/section semantics is complete.
- Planner progress now writes to `learning_progress_records`.
- Skip audit now writes to `waived_units`.
- Main schema/handoff docs were refreshed.

Needed:

- Sweep older notes/specs and mark transitional guidance as historical where needed.
- Remove any leftover instruction that still tells engineers to rely on dropped legacy curriculum/mastery tables.

Acceptance:

- New engineer reading the repo cannot mistake legacy tables for active production tables.
