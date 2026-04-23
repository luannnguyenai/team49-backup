# Production DB Integration Handoff

Date: 2026-04-23
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
- safe write flags for the first cutover paths
- compatibility writes for onboarding goal snapshots and planner audit snapshots

Key files:

- `src/models/learning.py`
- `src/models/canonical.py`
- `src/config.py`
- `src/repositories/goal_preference_repo.py`
- `src/repositories/learner_mastery_kp_repo.py`
- `src/repositories/waived_unit_repo.py`
- `src/repositories/planner_audit_repo.py`
- `src/scripts/pipeline/import_canonical_artifacts_to_db.py`
- `alembic/versions/20260423_learner_planner_stub_persistence.py`
- `alembic/versions/20260423_canonical_content_tables.py`

## Canonical Bootstrap Status

Validated on local Postgres on 2026-04-23:

- `uv run alembic upgrade head` reached `20260423_item_cal_prior (head)`
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

Important contract corrections now enforced in code and DB:

- `concepts_kp.difficulty_level` is numeric `Float`
- `units.difficulty` is numeric `Float`
- `item_calibration.difficulty_prior` is numeric `Float`
- canonical exporter accepts both:
  - `suitability_by_phase`
  - legacy `eligible_phases + recommended_phase + phase_weight_multipliers`

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

These tables can remain during transition, but new production features should not treat them as the long-term source of truth:

- `modules`
- `topics`
- `knowledge_components`
- `questions`
- `sessions`
- `interactions`
- `mastery_scores`
- `mastery_history`
- `learning_paths`
- legacy tutor tables in `src/models/store.py`

Do not remove them until read/write parity is proven. Do not add new semantics to them if the new schema already has a table for that concern.

## Feature Flags

Current flags live in `src/config.py`:

- `write_goal_preferences_enabled`
- `write_learner_mastery_kp_enabled`
- `write_waived_units_enabled`
- `write_planner_audit_enabled`
- `read_goal_preferences_enabled`
- `read_learner_mastery_kp_enabled`

Cutover rule:

- Write flags can be enabled first for audit/sidecar writes.
- Read flags should only be enabled after the target table has been backfilled and verified.
- Avoid silent dual-write. If a flow writes both old and new tables, document the old write as compatibility and define which read path wins.

## Write Contracts

### Onboarding Goal Preferences

Target table: `goal_preferences`

Current writer:

- `src/services/auth_service.py:update_onboarding`

Current status:

- Already writes a compatibility snapshot when `write_goal_preferences_enabled=true`.
- This is not the final course-first goal contract yet unless `selected_course_ids` is populated by the integration/onboarding layer.

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

- Final onboarding should write explicit course choices to `selected_course_ids`.
- Do not keep encoding selected goals only through legacy desired module/topic IDs.

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
- If the assessor only has a topic-level result, keep writing compatibility `mastery_scores`.

### Waived Units

Target table: `waived_units`

Current writer:

- repository exists, but no runtime service writes this yet

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
- Only write `waived_units` when the runtime can identify the actual `learning_units.id`.

### Planner Audit

Target tables:

- `plan_history`
- `rationale_log`
- `planner_session_state`

Current writer:

- `src/services/recommendation_engine.py:generate_learning_path`

Current status:

- Already writes legacy topic-grain audit when `write_planner_audit_enabled=true`.
- Also has a canonical unit-grain branch when `read_canonical_planner_enabled=true`.
- Legacy audit keeps `rationale_log.learning_unit_id=null`.
- Canonical branch writes real `rationale_log.learning_unit_id`.

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
- `state_json`

Integration note:

- New planner implementations should rank canonical/product `learning_units`, not legacy `topics`.
- Every planner response should have a corresponding `plan_history` row and rationale rows.
- Use `planner_session_state` for sticky constraints such as bridge chain depth rather than recomputing only from the latest path.

## Read Contracts

### Planner Reads

Planner should read:

- learner goals from `goal_preferences`
- current KP mastery from `learner_mastery_kp`
- unit content shell from `learning_units`
- unit-KP coverage from `unit_kp_map`
- prerequisite graph from `prerequisite_edges`
- existing progress/resume from `learning_progress_records`
- waived/skipped units from `waived_units`

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
- optionally legacy `mastery_scores` during compatibility, but only with an explicit policy

### Resume / Progress Reads

Resume UI and backend should keep using:

- `learning_progress_records`

Do not replace it with planner audit tables. Planner audit explains recommendations; progress records represent actual user activity.

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

- `goal_preferences.selected_course_ids` is not fully populated by current onboarding because the old flow is still topic/module-grain.
- `learner_mastery_kp` is only written by the canonical assessment branch; legacy topic assessment still writes `mastery_scores`.
- `waived_units` is not written by runtime until skip logic can identify `learning_units.id`.
- `plan_history` has both legacy compatibility audit and canonical unit-grain audit branches.
- `rationale_log.learning_unit_id` can be `null` only for legacy compatibility audits.

## Do Not Do

- Do not wire frontend/UI as part of this database cutover.
- Do not fabricate `kp_id` from `topic_id`.
- Do not fabricate `learning_unit_id` from legacy path rows.
- Do not remove compatibility tables before parity is proven.
- Do not add new production semantics to `mastery_scores`, `learning_paths`, or legacy `questions`.
- Do not enable read flags before import/backfill verification.

## Freeze/Delete Policy

Detailed legacy cleanup ownership and task order live in `docs/LEGACY_SCHEMA_CLEANUP_PLAN.md`.

Old tables may only be frozen after canonical runtime parity is `ready` for two consecutive runs.

Freeze means:

- no new feature writes to `questions`, `mastery_scores`, or `learning_paths`
- old rows remain for audit/backward compatibility
- rollback is still possible by disabling canonical read flags

Delete/drop is a separate migration and requires explicit approval. This cutover plan does not delete or truncate old runtime data.

Run the parity report with:

```bash
PYTHONPATH=. python src/scripts/pipeline/check_canonical_runtime_parity.py
```

## Minimal Next Backend Tasks

1. Run `alembic upgrade head` in the target PostgreSQL environment.
2. Import canonical content with `src/scripts/pipeline/import_canonical_artifacts_to_db.py`.
3. Backfill product links with `src/scripts/pipeline/backfill_product_canonical_links.py --apply`.
4. Run parity check with `src/scripts/pipeline/check_canonical_runtime_parity.py`.
5. Populate real `goal_preferences.selected_course_ids` from onboarding/integration.
6. Enable read/write flags only after parity checks pass.
7. Update skip verification to write `waived_units` with evidence.
