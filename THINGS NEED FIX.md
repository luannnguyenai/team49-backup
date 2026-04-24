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
- Mastery scoring policy is now explicit: phase-1 2PL-lite prior scoring updates `learner_mastery_kp`, planner/waive gates use a shared mastery LCB, and calibration readiness separates real responses from synthetic data.
- Skip is now policy-gated before writing `waived_units`: either mastery LCB or a skip-verification score must satisfy the documented threshold.
- Learning-session resume/progress endpoints persist video progress, current stage, current unit, and current quiz progress into `planner_session_state`.
- Quiz abandon is represented by `items_answered` / `items_remaining` in `planner_session_state.current_progress`; answered items stay in `interactions` and are not rolled back.
- Review quick-check runtime exists at `/api/review/start` and selects canonical questions from `item_phase_map.phase='review'`.
- Placement-lite runtime exists at `/api/placement-lite/start` and selects canonical questions from `item_phase_map.phase='placement'` for partial recalibration flows.

## Remaining Work

### 1. Real Calibration Job / Synthetic Calibration Policy

Current state:

- Runtime has a phase-1 prior-based scoring policy and calibration readiness boundary.
- Real production calibration still requires interaction volume.
- Deterministic synthetic demo data now has a script and remains clearly separated from real calibration readiness.
- Synthetic observations are still not allowed to satisfy real calibration readiness.

Needed:

- Decide whether synthetic observations should be used only for demo/stress testing or also for optional offline bootstrap experiments.
- Build the actual calibration fitting job for 1PL/2PL/3PL when enough real production interaction data exists.
- Keep calibration reports separating real and synthetic response counts.

Acceptance:

- Demo synthetic rows cannot be confused with real production evidence.
- Calibration reports keep real and synthetic response counts separate.
