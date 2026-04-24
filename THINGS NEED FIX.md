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

## Remaining Work

### 1. Synthetic Calibration Dataset Design

Current state:

- Runtime has a phase-1 prior-based scoring policy and calibration readiness boundary.
- Real production calibration still requires interaction volume.
- User explicitly wants synthetic data to be handled carefully and later, not silently generated during cleanup.

Needed:

- Design synthetic learner/session/interaction generation rules before generating any rows.
- Decide volume and distribution:
  - number of synthetic learners
  - number of sessions per learner
  - course preference split
  - abandon/resume behavior
  - answer correctness distribution by latent ability, item difficulty, and phase
- Mark synthetic observations explicitly so they never satisfy real calibration readiness.
- Only after approval, generate synthetic data for demo/stress testing and optional calibration experiments.

Acceptance:

- Synthetic generation is documented before execution.
- Generated rows cannot be confused with real production evidence.
- Calibration reports keep real and synthetic response counts separate.
