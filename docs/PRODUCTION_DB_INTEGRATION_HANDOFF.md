# Production DB Integration Handoff

Date: 2026-04-24
Branch: `rin/implement`

## Purpose

This document is the handoff contract for the engineer who will wire backend services to the production database model.

It answers four questions:

- which tables are authoritative
- which old tables are compatibility-only
- which writes are already safely connected
- what order to use when cutting runtime code over to the new schema

This handoff does not require frontend/UI changes.

## Current Implementation Status

Implemented and committed:

- learner/planner sidecar ORM tables and migration
- canonical content ORM tables and migration
- canonical JSONL importer with manifest validation and post-import DB count verification
- canonical-only assessment / quiz / module-test runtime reads-writes
- canonical quiz/module-test/history contracts renamed to `learning_unit_id` / `section_id`
- canonical planner progress writes via `learning_progress_records`
- canonical skip/waive audit writes via `waived_units`
- hard drop migration for legacy curriculum/mastery/planner tables
- canonical history filtering and subject rendering for section/unit-backed sessions

Key files:

- `src/models/learning.py`
- `src/models/canonical.py`
- `src/config.py`
- `src/repositories/goal_preference_repo.py`
- `src/repositories/learner_mastery_kp_repo.py`
- `src/repositories/learning_progress_repo.py`
- `src/repositories/waived_unit_repo.py`
- `src/repositories/planner_audit_repo.py`
- `src/scripts/pipeline/import_canonical_artifacts_to_db.py`
- `alembic/versions/20260423_learner_planner_stub_persistence.py`
- `alembic/versions/20260423_canonical_content_tables.py`
- `alembic/versions/20260424_learning_progress_skipped.py`

## Canonical Bootstrap Status

Validated on local Postgres on 2026-04-24:

- `uv run alembic upgrade head` reached `20260424_lp_skipped (head)`
- `PYTHONPATH=. uv run python src/scripts/pipeline/export_canonical_artifacts.py`
- `PYTHONPATH=. uv run python src/scripts/pipeline/import_canonical_artifacts_to_db.py`
- `PYTHONPATH=. uv run python src/scripts/pipeline/import_product_shell_to_db.py`
- `uv run python -m src.scripts.pipeline.check_canonical_runtime_parity`

Observed parity status after import:

- `status = ready`
- `linked_units = 295`
- `unlinked_units = 0`
- `missing_question_phase_maps = 0`
- `missing_question_kp_maps = 0`
- `canonical_interaction_count = 0`
- `canonical_planner_plan_count = 0`

Observed legacy-drop verification after migration:

- `modules = false`
- `topics = false`
- `knowledge_components = false`
- `questions = false`
- `mastery_scores = false`
- `mastery_history = false`
- `learning_paths = false`

Additional runtime verification on 2026-04-24:

- `npm --prefix frontend run type-check`
- `npm --prefix frontend run build`
- `uv run pytest tests/contract tests/services/test_quiz_canonical_cutover.py tests/services/test_module_test_canonical_cutover.py tests/services/test_recommendation_engine_canonical_cutover.py tests/services/test_assessment_canonical_mastery_cutover.py -q`
- `FRONTEND_PORT=3001 npm --prefix frontend run test:e2e -- course-discovery.spec.ts course-gating.spec.ts`

Observed results:

- Frontend production build passes.
- Canonical route/service regression set passes: `44 passed`.
- Canonical course discovery/gating e2e passes: `7 passed`.

Important contract corrections now enforced in code and DB:

- `concepts_kp.difficulty_level` is numeric `Float`
- `units.difficulty` is numeric `Float`
- `item_calibration.difficulty_prior` is numeric `Float`
- canonical exporter accepts both:
  - `suitability_by_phase`
  - legacy `eligible_phases + recommended_phase + phase_weight_multipliers`
- protected course assets under `data/courses/<course>/videos|slides|transcripts` require signed `/data/...` URLs
- quiz/module-test route contracts expose canonical `learning_unit_id` / `section_id` payloads and do not expose `correct_answer` in start responses

## Migration Order

Run database migrations first:

```bash
alembic upgrade head
```

Validate the canonical bundle before importing:

```bash
PYTHONPATH=. python src/scripts/pipeline/import_canonical_artifacts_to_db.py --validate-only
```

Import canonical content into PostgreSQL:

```bash
PYTHONPATH=. python src/scripts/pipeline/import_canonical_artifacts_to_db.py
```

The importer is idempotent. It upserts by deterministic natural keys and verifies DB row counts against `data/final_artifacts/cs224n_cs231n_v1/canonical/manifest.json` after import.

Expected canonical counts:

- `concepts_kp`: 470
- `units`: 295
- `unit_kp_map`: 767
- `question_bank`: 985
- `item_calibration`: 985
- `item_phase_map`: 6838
- `item_kp_map`: 1171
- `prerequisite_edges`: 79
- `pruned_edges`: 34

## Authoritative Table Matrix

Use these tables as the long-term source of truth:

- Account identity: `users`
- Course catalog shell: `courses`
- Product hierarchy: `course_sections`, `learning_units`
- Runtime resume/progress: `learning_progress_records`
- Goal selection and planner preferences: `goal_preferences`
- KP mastery state: `learner_mastery_kp`
- Skip/waive evidence: `waived_units`
- Planner run snapshot: `plan_history`
- Planner explainability: `rationale_log`
- Planner session counters: `planner_session_state`
- Global KP catalog: `concepts_kp`
- Unit-to-KP coverage: `unit_kp_map`
- Authored assessment items: `question_bank`
- Item calibration and IRT priors: `item_calibration`
- Item phase suitability: `item_phase_map`
- Q-matrix baseline: `item_kp_map`
- Final prerequisite graph: `prerequisite_edges`
- Pruned prerequisite audit: `pruned_edges`

## Compatibility-Only Tables

These tables remain in production runtime after the hard cutover:

- `sessions`
- `interactions`
- legacy tutor tables in `src/models/store.py`

Notes:

- `sessions` and `interactions` are still authoritative shared runtime tables, but now canonical fields are the only supported product path.
- `topic_id`, `module_id`, and `question_id` remain nullable compatibility columns only; they no longer have active FK links to dropped legacy tables.
- Do not reintroduce any new feature write/read path against dropped legacy tables.

## Feature Flags

Current flags live in `src/config.py`:

- `write_goal_preferences_enabled`
- `write_learner_mastery_kp_enabled`
- `write_waived_units_enabled`
- `write_planner_audit_enabled`
- `read_goal_preferences_enabled`
- `read_learner_mastery_kp_enabled`
- `read_canonical_questions_enabled`
- `write_canonical_interactions_enabled`
- `read_canonical_planner_enabled`

Legacy allow/deny flags have been removed because the fallback tables no longer exist.

## Write Contracts

### Onboarding Goal Preferences

Target table: `goal_preferences`

Current writer:

- `src/services/auth_service.py:update_onboarding`

Current status:

- Writes a course-first goal snapshot when `write_goal_preferences_enabled=true`.
- Frontend onboarding sends `known_unit_ids`, `desired_section_ids`, and explicit `selected_course_ids`.
- Backend still accepts temporary aliases `known_topic_ids` and `desired_module_ids` for compatibility, but new clients must not use them.

Required final payload:

- `user_id`
- `selected_course_ids`
- `goal_weights_json`
- `goal_embedding`
- `goal_embedding_version`
- `derived_from_course_set_hash`
- optional `notes`

Idempotency:

- one row per user
- uniqueness: `goal_preferences.user_id`

Integration note:

- Onboarding must write explicit course choices to `selected_course_ids`.
- Do not encode selected goals only through section/unit IDs; planner scope is course-first.

### Learner KP Mastery

Target table: `learner_mastery_kp`

Current writer:

- `src/services/canonical_mastery_service.py:update_kp_mastery_from_item`
- called from canonical assessment submit when `write_canonical_interactions_enabled=true` and `write_learner_mastery_kp_enabled=true`

Required final payload:

- `user_id`
- `kp_id`
- `theta_mu`
- `theta_sigma`
- `mastery_mean_cached`
- `n_items_observed`
- `updated_by`

Idempotency:

- one row per `(user_id, kp_id)`
- uniqueness: `uq_learner_mastery_kp_user_kp`

Correct input sources:

- answer events from runtime interaction logs
- `question_bank.item_id`
- `item_kp_map.item_id -> kp_id`
- `item_calibration` for IRT priors/calibrated parameters

Integration note:

- Do not map legacy `topic_id` directly to fake `kp_id`.
- Canonical mastery writes require `canonical_item_id`, then resolve KP through `item_kp_map`.
- If a caller only has a topic-level result, treat it as an unsupported legacy signal; do not recreate `mastery_scores`.

### Waived Units

Target table: `waived_units`

Current writer:

- `src/services/recommendation_engine.py:update_path_status`

Required final payload:

- `user_id`
- `learning_unit_id`
- `evidence_items`
- `mastery_lcb_at_waive`
- `skip_quiz_score`

Idempotency:

- one row per `(user_id, learning_unit_id)`
- uniqueness: `uq_waived_units_user_unit`

Correct input sources:

- skip verification result
- evidence item IDs from `question_bank`
- KP mastery lower-confidence-bound at waive time
- optional skip quiz score

Integration note:

- A skipped legacy `learning_paths` topic is not enough to create a `waived_units` row.
- Runtime now writes `evidence_items` from KP mastery snapshots and optional latest quiz score.
- Only write `waived_units` when the runtime can identify the actual `learning_units.id`.

### Planner Audit

Target tables:

- `plan_history`
- `rationale_log`
- `planner_session_state`

Current writer:

- `src/services/recommendation_engine.py:generate_learning_path`

Current status:

- Canonical branch is the active production path.
- `generate_learning_path` writes planner audit into `plan_history`, `rationale_log`, `planner_session_state`.
- `update_path_status` writes learner execution state into `learning_progress_records`.
- Quiz completion also marks the unit `completed` in `learning_progress_records` and clears stale waive audit rows.

Required final `plan_history` payload:

- `user_id`
- `parent_plan_id`
- `trigger`
- `recommended_path_json`
- `goal_snapshot_json`
- `weights_used_json`

Required final `rationale_log` payload:

- `plan_history_id`
- `learning_unit_id`
- `rank`
- `reason_code`
- `term_breakdown_json`
- `rationale_text`

Required final `planner_session_state` payload:

- `user_id`
- `session_id`
- `last_plan_history_id`
- `bridge_chain_depth`
- `consecutive_bridge_count`
- `current_unit_id`
- `current_stage`: `watching | quiz_in_progress | post_quiz | between_units`
- `current_progress`: JSON payload for partial video/quiz progress
- `last_activity`
- `state_json`

Integration note:

- New planner implementations should rank canonical/product `learning_units`, not legacy `topics`.
- Every planner response should have a corresponding `plan_history` row and rationale rows.
- Use `planner_session_state` for sticky constraints such as bridge chain depth rather than recomputing only from the latest path.
- Public runtime/frontend contracts should now use `learning_unit_id` and `section_id` on quiz/module-test/history surfaces.

## Read Contracts

### Planner Reads

Planner should read:

- learner goals from `goal_preferences`
- current KP mastery from `learner_mastery_kp`
- unit content shell from `learning_units`
- unit-KP coverage from `unit_kp_map`
- prerequisite graph from `prerequisite_edges`
- existing progress/resume from `learning_progress_records`
- active abandon/resume pointer from `planner_session_state.current_unit_id/current_stage/current_progress`
- waived/skipped units from `waived_units`

Planner reads should apply mastery staleness on-read before computing skip/review/deep-practice thresholds. Do not overwrite `learner_mastery_kp` just because a user was inactive; inflate uncertainty for the current decision and let new review evidence update the stored posterior.

Planner should not infer future production behavior from:

- `learning_paths` alone
- `topics.prerequisite_topic_ids`
- `mastery_scores` alone

### Assessor Reads

Assessor should read:

- item content from `question_bank`
- item-to-KP mapping from `item_kp_map`
- item phase suitability from `item_phase_map`
- item priors/calibration from `item_calibration`
- current KP mastery from `learner_mastery_kp`

Question ownership must be preserved through joins:

- lecture/unit ownership comes from `question_bank.course_id`, `question_bank.lecture_id`, `question_bank.unit_id`, and `question_bank.source_ref`
- assessor/usage ownership comes from `item_phase_map.phase`, with allowed phases such as `placement`, `mini_quiz`, `skip_verification`, `bridge_check`, `final_quiz`, `transfer`, and `review`
- KP evidence ownership comes from `item_kp_map.item_id -> kp_id`
- history/detail ownership for canonical attempts comes from `interactions.canonical_item_id -> question_bank.item_id`

Do not infer assessor usage from `question_bank` alone. A question can be valid for multiple phases, so runtime item selection must join `question_bank` with `item_phase_map` and filter by the active assessor phase.

Assessor should update:

- `learner_mastery_kp`

### Resume / Progress Reads

Resume UI and backend should keep using:

- `learning_progress_records` for durable unit status and last video position
- `planner_session_state` for active session pointer and partial quiz/video state
- `sessions` + `interactions` for answered quiz evidence

Do not replace progress records with planner audit tables. Planner audit explains recommendations; progress records represent actual user activity. Partial answered quiz items must remain in `interactions` even if the abandoned quiz gate is later invalidated and regenerated.

Resume policy:

- `< 24h`: resume current unit/quiz seamlessly; partial quiz may continue with remaining items.
- `1-7 days`: show welcome-back context from latest plan/progress.
- `7-30 days`: run a short `item_phase_map.phase='review'` check over recent high-mastery KP before trusting old mastery.
- `> 30 days`: offer placement-lite or partial recalibration.

## Required Consistency Checks

Before enabling new read paths, verify:

- every `question_bank.primary_kp_id` exists in `concepts_kp`
- every `item_kp_map.kp_id` exists in `concepts_kp`
- every `item_kp_map.item_id` exists in `question_bank`
- every `unit_kp_map.unit_id` exists in `units`
- every `unit_kp_map.kp_id` exists in `concepts_kp`
- every `prerequisite_edges.source_kp_id` and `target_kp_id` exists in `concepts_kp`
- DB row counts match canonical manifest after import

The current importer validates columns/counts and verifies post-import row counts. FK constraints cover the canonical DB relationships once tables are migrated.

## Known Transitional Gaps

These are intentional gaps, not missing UI work:

- Temporary onboarding aliases for `known_topic_ids` and `desired_module_ids` remain only to avoid breaking old clients; frontend uses the course-first contract.
- `planner_session_state.current_progress` stores the resume pointer, but frontend resume UI has not been wired yet.
- `learner_mastery_kp` uses bootstrap scoring unless a calibration job has produced trusted item parameters.
- Historical docs may still mention pre-cutover tables and must be treated as archive unless refreshed.

## Do Not Do

- Do not fabricate `kp_id` from `topic_id`.
- Do not fabricate `learning_unit_id` from legacy path rows.
- Do not reintroduce dropped runtime tables such as `modules`, `topics`, `questions`, `mastery_scores`, or `learning_paths`.
- Do not claim production IRT/BKT accuracy until calibration has actually run and been validated.

## Freeze/Delete Policy

Detailed legacy cleanup ownership and task order live in `docs/LEGACY_SCHEMA_CLEANUP_PLAN.md`.

Historical note: the runtime legacy tables were dropped by `20260423_drop_legacy` after parity checks passed. This section now acts as a regression guard: future work should not add new production reads/writes back to dropped schemas.

Run the parity report with:

```bash
PYTHONPATH=. python src/scripts/pipeline/check_canonical_runtime_parity.py
```

## Minimal Next Backend Tasks

1. Run `alembic upgrade head` in the target PostgreSQL environment.
2. Import canonical content with `src/scripts/pipeline/import_canonical_artifacts_to_db.py`.
3. Backfill product links with `src/scripts/pipeline/backfill_product_canonical_links.py --apply`.
4. Run parity check with `src/scripts/pipeline/check_canonical_runtime_parity.py`.
5. Remove temporary onboarding aliases after external clients have migrated to `known_unit_ids` / `desired_section_ids`.
6. Enable read/write flags only after parity checks pass.
