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

### 1. Frontend Semantic Cleanup

Current state:

- Backend routes are canonical-only.
- Some request/response names still use legacy labels for compatibility:
  - quiz `topic_id`
  - module-test `module_id`
  - history filter `module_id`

Needed:

- Rename frontend/runtime contracts toward:
  - `learningUnitId`
  - `sectionId`
  - `canonicalUnitIds`
- Keep UI visuals unchanged.

Acceptance:

- No frontend code treats `topicId/moduleId` as legacy curriculum tables.
- Route params and local storage keys reflect section/unit semantics.

### 2. Assessment/Quiz/Module-Test Contract Polish

Current state:

- Runtime logic is canonical-only.
- API shape still preserves some compatibility naming.

Needed:

- Decide final public contract names and migrate schemas/docs consistently.
- Add API contract tests for:
  - assessment start/submit/results
  - quiz start/answer/complete/history
  - module-test start/submit/results

Acceptance:

- Backend schemas, frontend types, and docs use the same canonical terminology.

### 3. Skip/Waive Runtime Wiring

Current state:

- `waived_units` table exists.
- Runtime skip policy is not wired end-to-end yet.

Needed:

- Define the production skip decision point.
- Write `waived_units` with:
  - `learning_unit_id`
  - `evidence_items`
  - `mastery_lcb_at_waive`
  - `skip_quiz_score` when applicable

Acceptance:

- Skip decisions are auditable without any legacy planner table.

### 4. Planner Progress Runtime

Current state:

- Planner generation/list/timeline use canonical planner audit.
- Path status updates still intentionally stop short of a full canonical progress write model.

Needed:

- Decide canonical status/progress source-of-truth for learner plan execution.
- Wire update flow without recreating `learning_paths`.

Acceptance:

- Progress updates are persisted in a canonical table or canonical audit structure.

### 5. Docs Sweep

Current state:

- Main schema/handoff docs were refreshed.
- Older plans/spec notes still mention transitional legacy paths.

Needed:

- Sweep docs/specs/notes and mark them clearly as historical where needed.
- Remove instructions that tell engineers to rely on legacy curriculum/mastery tables.

Acceptance:

- New engineer reading the repo cannot mistake legacy tables for active production tables.
