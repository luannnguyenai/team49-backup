# Synthetic Demo Users Design

## Goal

Create deterministic synthetic learner data for product demos without using random generation. The dataset is split into two clear groups:

- `demo_accounts_v1`: 9 login-ready demo accounts, one per UX/runtime case.
- `cohort_30_v1`: 30 background synthetic users for dashboard/history/planner volume.

## Non-Goals

- Do not state-lock users at runtime.
- Do not generate real calibration truth.
- Do not let synthetic observations satisfy real calibration readiness.
- Do not change frontend UI.

## Login Contract

All demo login accounts use the `@vinuni.edu.vn` domain and the shared password `DemoPass123!`.

Demo accounts:

- `demo.firstlogin@vinuni.edu.vn`
- `demo.full@vinuni.edu.vn`
- `demo.cs231@vinuni.edu.vn`
- `demo.cs224n@vinuni.edu.vn`
- `demo.skipper@vinuni.edu.vn`
- `demo.reviewer@vinuni.edu.vn`
- `demo.beginner@vinuni.edu.vn`
- `demo.abandon.video@vinuni.edu.vn`
- `demo.returner@vinuni.edu.vn`

## Cohort Distribution

`cohort_30_v1` is not a login-demo dataset. It provides deterministic background volume with diverse proficiency:

| Proficiency | Count |
| --- | ---: |
| `beginner` | 6 |
| `developing` | 7 |
| `proficient` | 10 |
| `advanced` | 7 |

Case distribution:

| Case | Count |
| --- | ---: |
| `full_2_courses` | 6 |
| `cs231_only` | 5 |
| `cs224n_only` | 3 |
| `strong_skipper` | 4 |
| `review_heavy` | 3 |
| `weak_beginner` | 3 |
| `abandon_mid_video` | 2 |
| `abandon_mid_quiz` | 2 |
| `long_returner_review` | 1 |
| `very_long_returner_placement_lite` | 1 |

## Reset Contract

The importer must be idempotent. Each run deletes the known synthetic emails and recreates them from a fixed snapshot. If a demo user changes state during a live demo, rerunning the script restores the baseline.

Rows must carry metadata where the destination table supports it:

- `is_synthetic=true`
- `synthetic_dataset=demo_accounts_v1|cohort_30_v1`
- `synthetic_case=<case_name>`
- `resettable=true`

## Time Contract

All timestamps are based on `DEMO_NOW = 2026-04-24T09:00:00Z`.

- Active learners: last activity within 24 hours.
- Abandon-video learner: last activity at `2026-04-24T08:10:00Z`.
- Abandon-quiz learner: last activity at `2026-04-23T10:00:00Z`.
- Long-return learner: last activity at `2026-03-10T09:00:00Z`.
- First-login learner: no planner/progress/mastery state.

## Output / Import Contract

The source of truth is hand-authored scenario JSON:

- `data/synthetic/demo_accounts_v1/scenarios.json`
- `data/synthetic/cohort_30_v1/scenarios.json`

Each scenario explicitly declares `mastery_profile`, `learning_state`, and `sessions[].answer_pattern`. The Python script creates deterministic JSONL snapshots under `data/synthetic/<dataset>/` and can also reset/import those rows into the active DB. It must select real course/unit/item IDs from the current canonical DB, sorted deterministically, so the fixture stays aligned with imported course content.
