# Phase 05: Evaluation And Guardrails

## Goal

Add evaluation, regression safety, and correctness guardrails so recommendation quality can be measured instead of guessed.

## Why This Phase Exists

A recommendation system can appear to work while silently regressing.
This repo already has behavior tests, but behavior tests alone are not enough for quality.

This phase adds:

- correctness checks
- quality benchmarks
- explanation validation
- constraint regression coverage

## Scope

This phase covers:

- offline evaluation fixtures
- deterministic correctness tests
- scenario-based quality tests
- recommendation and explanation guardrails

This phase does not require any LLM components.

## New And Modified Modules

### Add

- `tests/evals/test_course_recommendation_quality.py`
- `tests/evals/test_recommendation_explanation_quality.py`
- `tests/evals/fixtures/learner_profiles.py`
- `tests/evals/fixtures/expected_recommendations.py`
- `docs/RECAI-EVALS.md`

### Modify

- `tests/services/test_course_recommendation_engine.py`
  Keep as compatibility regression during migration.
- `tests/contract/test_course_recommendations_api.py`
  Add stricter validation for returned explanation and ordering semantics.

## Evaluation Categories

### Deterministic Constraint Checks

- no duplicate courses in top-N
- no already-completed course in top-N unless explicitly allowed
- no blocked or unavailable course ranked above ready alternatives without strong reason
- reason code must match emitted explanation summary
- explanation cannot mention unsupported prerequisites or goals

### Scenario Quality Checks

Create seeded personas such as:

- cold-start learner
- weak-foundation learner
- strong-vision learner
- NLP-goal learner
- learner who completed `cs231n`
- learner with mixed weak and strong clusters

For each persona, assert broad quality expectations rather than brittle exact strings when appropriate.

### Explanation Fidelity Checks

- explanation summary must be derivable from chosen features
- explanation code must match rank reason
- explanation must not overclaim graph evidence

## Metrics To Track

Track metrics such as:

- top-k readiness correctness
- remediation coverage score
- advancement alignment score
- goal alignment hit rate
- explanation fidelity pass rate
- duplicate suppression pass rate

Even if some metrics start as internal test assertions, define them now so they can be reported later.

## Testing Plan

### Unit-Like Eval Tests

- seeded feature payloads map to the expected reason codes
- availability penalties behave as expected
- goal proximity meaningfully affects ranking where configured

### Scenario Eval Tests

- cold-start defaults remain stable
- remediation users get foundational courses near the top
- advanced learners get meaningful next-step courses
- completed-course users are not looped back to the same course

### API Regression Tests

- recommendation endpoints preserve response schema
- catalog decoration stays consistent with persisted rows

## Suggested Commit Slices

1. `test: add learner profile eval fixtures`
2. `test: add recommendation constraint regression suite`
3. `test: add explanation fidelity eval suite`
4. `docs: document recommendation evaluation metrics`

## Done When

- quality regressions are caught by automated tests
- explanation fidelity is testable
- recommendation constraints are enforced and measurable
- future ranking changes can be benchmarked before merge
