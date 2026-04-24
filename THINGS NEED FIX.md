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
- Abandon/resume runtime state is represented in `planner_session_state` with current unit/stage/progress and `last_activity`; planner reads apply mastery staleness on-read.
- Onboarding contract is course-first: frontend sends `known_unit_ids`, `desired_section_ids`, and `selected_course_ids`; backend writes explicit `goal_preferences.selected_course_ids`.
- Runtime DTO/API naming is learning-unit/section-first for assessment results, module-test groups/results, learning-path counts, and history question detail.
- README and historical superpowers plans/specs now clearly point new work at the canonical production contract instead of legacy transitional architecture.
- Orphan topic-grain helpers were removed; `scripts/seed.py`, `make seed`, and startup seeding now import canonical artifacts/product shell instead of legacy `modules/topics/questions`.

## Remaining Work

### 1. Production Mastery / Scoring Calibration

Current state:

- Runtime writes `learner_mastery_kp` from canonical assessment evidence.
- `src/services/canonical_mastery_service.py` currently uses a bounded bootstrap heuristic:
  - `theta_mu +=/-= 0.25 * item_kp_map.weight`
  - `theta_sigma *= 0.95`
  - `mastery_mean_cached = sigmoid(theta_mu / sqrt(1 + theta_sigma^2))`
- `item_calibration` has priors and reserved fields for IRT-style calibration, but calibrated parameters are not yet produced from real interaction data.
- README now states this is bootstrap scoring unless calibration has actually run.

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
