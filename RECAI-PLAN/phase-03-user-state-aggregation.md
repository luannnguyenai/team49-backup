# Phase 03: User State Aggregation

## Goal

Build one authoritative learner-state layer for recommendation.

The recommendation engine should not read half a dozen unrelated tables directly every time it ranks.
It should consume a stable, typed `LearnerStateSnapshot`.

## Why This Phase Exists

Current learner signals are fragmented across:

- onboarding readiness and auth gating
- mastery tables
- assessment sessions
- learning progress
- recommendation rows and events
- history and interaction traces

That fragmentation causes three problems:

- inconsistent ranking inputs
- duplicated logic across services
- hard-to-explain recommendations

## Scope

This phase covers:

- learner profile snapshot contract
- aggregation service
- normalization of readiness, progress, mastery, goals, and preferences
- stable feature extraction inputs for ranking

This phase does **not** yet implement final recommendation ranking logic.

## New And Modified Modules

### Add

- `src/services/learner_state_service.py`
  Main aggregator for learner state.
- `src/schemas/learner_state.py`
  Typed snapshot schemas for recommendation.
- `tests/services/test_learner_state_service.py`
  Unit tests for aggregation behavior.

### Modify

- `src/services/course_entry_service.py`
  Reuse normalized readiness logic rather than ad hoc checks.
- `src/services/course_recommendation_engine.py`
  Replace direct table reads with learner snapshot inputs during transition.
- `src/kg/providers.py`
  Align mastery semantics with learner state aggregation.

## Target Snapshot Shape

`LearnerStateSnapshot` should include:

- `user_id`
- `is_onboarded`
- `recommendation_ready`
- `completed_course_slugs`
- `in_progress_course_slugs`
- `hidden_course_slugs`
- `saved_course_slugs`
- `goal_topic_slugs`
- `goal_course_slugs`
- `topic_mastery`
- `kc_mastery`
- `weak_topics`
- `strong_topics`
- `recent_learning_topics`
- `recent_recommendation_interactions`
- `available_time_budget`
- `preferred_learning_modes`

Keep the snapshot small enough to reason about and stable enough to test.

## Data Sources

Expected sources include:

- course progress records
- assessment completion and readiness signals
- onboarding preferences
- topic or KC mastery tables
- recommendation event history
- learning history or session traces

If hidden or saved course states do not exist yet, define placeholder extension points but do not invent fake persistence.

## Normalization Rules

The service must make hard choices explicit:

- what counts as `completed`
- what counts as `in_progress`
- what mastery thresholds define `weak` and `strong`
- how long `recent` means
- what makes a learner recommendation-ready

These thresholds must live in config or clearly named constants, not scattered literals.

## Testing Plan

### Unit Tests

- learner with no history yields safe cold-start snapshot
- onboarding and readiness are normalized correctly
- completed and in-progress courses are partitioned correctly
- mastery thresholds produce correct weak and strong topic sets
- recent recommendation events are aggregated without duplication

### Integration Tests

- seeded learner state produces stable snapshot across repeated calls
- course entry and recommendation services agree on readiness semantics

### Regression Tests

- no recommendation service reads fragmented raw state directly after migration
- mastery semantics match KG provider expectations

## Suggested Commit Slices

1. `feat: add learner state schemas`
2. `feat: add learner state aggregation service`
3. `feat: normalize readiness and mastery thresholds`
4. `refactor: reuse learner snapshot in recommendation and gating paths`
5. `test: cover learner state aggregation`

## Done When

- one service owns learner-state aggregation
- recommendation code consumes a typed learner snapshot
- readiness and mastery semantics are consistent across runtime paths
- cold-start and rich-state users are both handled deterministically
