# Phase 04: Recommendation Engine

## Goal

Implement the backend recommendation engine as a modular pipeline:

- filter
- retrieve
- rank
- explain
- persist

This is the core phase.

## Why This Phase Exists

The current course recommendation engine already contains useful ranking logic, but it is still one file that couples:

- source loading
- signal reads
- candidate scoring
- explanation
- response assembly

This phase turns that baseline into a stable backend engine that can evolve without rewriting the whole service.

## Scope

This phase covers:

- candidate generation from course-aware KG
- filtering and constraint enforcement
- ranking from graph and learner-state features
- explanation from real features and graph paths
- persistence and retrieval contracts

This phase should still remain deterministic.

## New And Modified Modules

### Add

- `src/services/recommendation/user_state_snapshot.py`
  Shared import point for learner snapshot types if the feature folder pattern is preferred.
- `src/services/recommendation/candidate_generator.py`
  Generate raw course candidates from KG neighborhoods and course metadata.
- `src/services/recommendation/candidate_filter.py`
  Enforce availability, duplication, completion, and business rules.
- `src/services/recommendation/candidate_ranker.py`
  Compute numeric scores from graph and learner features.
- `src/services/recommendation/explainer.py`
  Emit reason codes, summaries, and supporting feature evidence.
- `src/services/recommendation/persistence.py`
  Persist recommendation runs, rows, and analytics.
- `tests/services/recommendation/`
  Unit tests per submodule.

### Modify

- `src/services/course_recommendation_engine.py`
  Turn into a façade or compatibility wrapper over the new pipeline.
- `src/routers/course_recommendations.py`
  Call the new pipeline and preserve existing API shape where possible.
- `src/services/course_catalog_service.py`
  Decorate catalog items from persisted recommendation output cleanly.

## Pipeline Design

### 1. Candidate Generator

Inputs:

- learner snapshot
- course-aware KG
- optional source course
- optional recommendation trigger

Outputs:

- broad candidate set with graph neighborhoods and raw features

Candidate generation should pull from:

- courses aligned to weak topics
- courses aligned to strong topics
- courses downstream of completed courses
- courses related to explicit learner goals

### 2. Candidate Filter

Remove candidates that violate constraints:

- unavailable or blocked courses
- already completed courses unless explicitly allowed
- duplicate or semantically repeated candidates
- courses whose prerequisite readiness is below a hard floor

### 3. Candidate Ranker

Rank using weighted features such as:

- prerequisite readiness
- remediation gain
- advancement fit
- transfer boost
- goal proximity
- freshness penalty
- availability multiplier

Weights should be config-driven where reasonable.

### 4. Explainer

Produce:

- `reason_code`
- `reason_summary`
- explanation feature payload
- optional graph path evidence for debugging and eval

Explanation must never assert anything the ranker did not actually use.

### 5. Persistence

Persist:

- request metadata
- ranked rows
- feature payloads
- explanation payloads
- shown and clicked events

## API Behavior

Preserve current useful routes where possible:

- `POST /api/course-recommendations/me/generate`
- `GET /api/course-recommendations/me`
- recommendation decoration in catalog responses

If new debug or trace endpoints are added, keep them admin-only or internal.

## Explanation Design

The explanation layer should standardize on a small set of codes first:

- `remediate_weak_foundation`
- `fill_skill_gap`
- `advance_from_completed_course`
- `specialize_strength`
- `goal_aligned_next_step`
- `transfer_from_related_strength`

Each code should map to:

- expected feature combinations
- allowed summary template shapes
- evaluation rules in Phase 5

## Testing Plan

### Unit Tests

- candidate generator returns graph-relevant candidates
- filter removes completed and unavailable courses correctly
- ranker orders candidates deterministically from seeded features
- explainer returns codes consistent with feature patterns
- persistence stores feature payloads and rows correctly

### Service Tests

- cold-start user gets sensible defaults
- weak-foundation user gets remediation-heavy ranking
- completed-course user gets advancement-heavy ranking
- mixed-state user gets diverse top-N output

### Contract Tests

- current recommendation API contracts still work
- catalog decoration includes persisted recommendation fields

### Regression Tests

- no recommendation path depends on bootstrap graph directly
- explanation remains grounded in real feature payloads

## Suggested Commit Slices

1. `feat: add recommendation pipeline candidate generator`
2. `feat: add recommendation filter and ranker`
3. `feat: add recommendation explanation module`
4. `refactor: route course recommendation engine through pipeline`
5. `feat: persist recommendation feature payloads`
6. `test: cover recommendation pipeline modules`

## Done When

- recommendation logic is modular and testable
- ranking depends on KG plus learner snapshot
- explanations are grounded and persisted
- existing API consumers keep working
