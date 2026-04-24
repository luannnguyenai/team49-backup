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

### 1. Production Mastery / Scoring Calibration

Current state:

- Runtime writes `learner_mastery_kp` from canonical assessment evidence.
- `src/services/canonical_mastery_service.py` currently uses a bounded bootstrap heuristic:
  - `theta_mu +=/-= 0.25 * item_kp_map.weight`
  - `theta_sigma *= 0.95`
  - `mastery_mean_cached = sigmoid(theta_mu / sqrt(1 + theta_sigma^2))`
- `item_calibration` has priors and reserved fields for IRT-style calibration, but calibrated parameters are not yet produced from real interaction data.
- README still describes BKT / IRT 2PL as if fully implemented.

Needed:

- Define the production scoring policy for phase 1:
  - whether to keep the bootstrap theta update as demo-only
  - whether to move to 1PL/2PL-lite using `item_calibration.difficulty_prior`, `discrimination_prior`, `guessing_prior`
  - how to compute/update `theta_mu`, `theta_sigma`, `mastery_mean_cached`, and mastery LCB consistently
- Add calibration input contract from `sessions` + `interactions` + `question_bank` + `item_kp_map`.
- Add a job or service boundary for future real/synthetic calibration, without pretending synthetic calibration is production truth.
- Update README/docs so they clearly say current scoring is bootstrap unless calibration has been run.

Acceptance:

- A developer can explain exactly how one answer changes `learner_mastery_kp`.
- Planner skip/quick-review/deep-practice thresholds use the same documented mastery semantics.
- No doc claims production IRT/BKT accuracy before calibration exists.

### 2. Abandon / Resume Runtime State

Current state:

- `planner_session_state` tracks planner counters and last activity, but not enough fine-grained resume state.
- `learning_progress_records` covers durable unit progress/status.
- `sessions` + `interactions` preserve answered quiz/assessment evidence.
- Partial evidence from answered questions must not be rolled back if the user abandons a quiz; evidence remains valid even if the quiz gate/session is later invalidated.

Cases to support:

- User abandons while watching a video.
- User abandons midway through a quiz.
- User finishes video but has not started mini-quiz.
- User receives skip/bridge offer but does not respond.
- User stops between units/segments.
- User returns after a long gap and previous mastery may be stale.

Needed schema/runtime additions:

- Add current unit pointer and partial progress to `planner_session_state` or a dedicated learner session state table:
  - `current_unit_id`
  - `current_stage`: `watching | quiz_in_progress | post_quiz | between_units`
  - `current_progress` JSON with fields such as:
    - `video_progress_s`
    - `video_finished`
    - `quiz_id`
    - `quiz_phase`
    - `items_answered`
    - `items_remaining`
  - `last_activity`
- Define quiz abandon policy:
  - `< 24h`: allow finish remaining items
  - `>= 24h`: invalidate the quiz gate/session and generate fresh items
  - keep existing `interactions` evidence and mastery updates
- Implement resume routing by `delta_t` since last activity:
  - `< 24h`: seamless resume
  - `1-7 days`: welcome-back summary
  - `7-30 days`: quick review check on recent high-mastery KP
  - `> 30 days`: placement-lite or partial recalibration offer
- Implement mastery decay on-read, not destructive DB overwrite:
  - inflate `theta_sigma` based on time since `learner_mastery_kp.updated_at`
  - optionally decay `theta_mu` toward zero for planning/assessment reads
  - keep raw evidence untouched until new quick-check evidence updates mastery officially
- Use `item_phase_map.phase='review'` for quick-check item selection.

Acceptance:

- User can close the browser mid-video or mid-quiz and resume predictably.
- Old partial quiz answers remain auditable in `interactions`.
- Planner does not treat stale 3-week-old mastery as equally reliable without on-read uncertainty inflation.
- Completed/waived units are not deleted just because mastery became stale.

### 3. Course-First Onboarding / Goal Preferences Contract

Current state:

- DB has `goal_preferences.selected_course_ids`.
- `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md` still notes this is not fully populated by the current onboarding flow.
- Frontend/onboarding still uses compatibility names:
  - `known_topic_ids`
  - `desired_module_ids`
  - `StepKnownTopics`
  - `StepDesiredModules`
- These values are mapped to canonical units/sections in runtime, but the public contract still speaks topic/module language.

Needed:

- Decide final onboarding payload names, likely:
  - `known_unit_ids`
  - `desired_section_ids`
  - `selected_course_ids`
- Update frontend types/schema/components/API payloads to use course-first names.
- Keep temporary backend aliases only if needed for migration, and document when to remove them.
- Ensure `goal_preferences.selected_course_ids` is populated from explicit course choices, not inferred indirectly from legacy-style module/topic fields.

Acceptance:

- A new frontend/backend engineer can wire onboarding without seeing `topic/module` as the primary contract.
- `goal_preferences` rows contain explicit course scope for planner goal weighting.

### 4. Frontend / API Semantic Naming Cleanup

Current state:

- Runtime routes are canonical, but several DTOs/comments/UI labels still use old names:
  - `TopicResult`, `TopicQuestionsGroup`, `ReviewTopicSuggestion`
  - `total_topics`, `completed_topics`, `in_progress_topics`
  - assessment result `topic_results`
  - module-test labels like "topic" / "module" where the payload is now learning-unit / section
- This is mostly naming debt, not a functional blocker.

Needed:

- Rename frontend and schema types toward:
  - `LearningUnitResult`
  - `LearningUnitQuestionsGroup`
  - `ReviewLearningUnitSuggestion`
  - `total_units`, `completed_units`, `in_progress_units`
- Update route descriptions/docstrings in `src/routers/*` that still say topic/module when the runtime is learning-unit/section.
- Keep response aliases only where product/API backward compatibility is intentionally required.

Acceptance:

- Public runtime/API contract consistently says `learning_unit_id` and `section_id`.
- Tests no longer need to mentally translate "topic" to "learning unit".
- No UI visual redesign is required for this task.

### 5. Historical Docs / README Sweep

Current state:

- Main handoff docs were refreshed, but older docs/specs still describe transitional or pre-cutover architecture.
- README is especially stale:
  - mentions `modules/topics/questions` seed flow
  - describes BKT / IRT 2PL as implemented production scoring
  - says planner is topic/topological-sort based
- Some `docs/superpowers/*` files are historical plans, but not all are clearly marked as historical.

Needed:

- Mark old plans/specs as historical where they should not guide current implementation.
- Rewrite README to reflect current source-of-truth:
  - `courses/course_sections/learning_units`
  - `question_bank/item_phase_map/item_kp_map/item_calibration`
  - `learner_mastery_kp`
  - `learning_progress_records`
  - `plan_history/rationale_log/planner_session_state`
- Remove or qualify old claims about dropped tables and unimplemented scoring sophistication.

Acceptance:

- New engineer reading the repo cannot mistake legacy tables or old plans for active production design.
- README matches the canonical runtime that currently passes build/e2e.

### 6. Orphan Legacy Helper / Script Review

Current state:

- Runtime DB legacy tables are dropped, but a few helper files still speak topic-grain or legacy archive language:
  - `src/utils/topological_sort.py`
  - `src/services/timeline_builder.py`
  - `src/data_paths.py` still exposes `MODULES_FILE` / `TOPICS_FILE`
  - legacy export/check scripts under `src/scripts/pipeline/*legacy*`
- Some of these are harmless historical/guard tooling; some may now be dead code.

Needed:

- For each helper/script, decide one of:
  - keep and rename to canonical unit/section semantics
  - move to explicit legacy/archive tooling
  - delete after confirming no runtime/test dependency
- Do not delete guard scripts that still protect canonical cleanup unless they are replaced by a newer check.

Acceptance:

- `rg` for active runtime code no longer shows unused topic-grain helpers as if they were production planner logic.
- Any remaining legacy script is clearly marked as archive/audit tooling.
