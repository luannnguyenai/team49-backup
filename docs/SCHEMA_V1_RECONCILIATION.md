# Schema v1 Reconciliation

## Scope

This document reconciles `main` migration:

- `alembic/versions/20260418_0001_schema_v1.py`

against the current hybrid branch.

Goal:

- identify the safe subset that can be adopted
- identify the parts that need a rewrite before adoption
- identify the parts that should be avoided for now because they conflict with the current hybrid model

## Current Hybrid Baseline

Hybrid already has:

- canonical course-first schema in [src/models/course.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/models/course.py:1)
- LMS/content schema in [src/models/content.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/models/content.py:1)
- learning activity schema in [src/models/learning.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/models/learning.py:1)
- legacy lecture adapter schema in [src/models/store.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/models/store.py:1)

Hybrid also already has:

- repositories for auth, recommendation, history, assessment
- question selection and assessment logic integrated around existing `questions`, `interactions`, `mastery_scores`, and `sessions`

This matters because `schema_v1` is not adding into an empty system. It is proposing a second schema strategy on top of tables that already exist and already serve running code.

## Safe to Adopt

### `pgvector` extension

Decision:

- adopt

Why:

- low-risk infra uplift
- future-compatible for embeddings and retrieval
- does not force immediate schema or service redesign

Status:

- already adopted in hybrid via:
  - `docker-compose.yml` using `pgvector/pgvector:pg16`
  - [alembic/versions/20260418_enable_pgvector_extension.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/alembic/versions/20260418_enable_pgvector_extension.py:1)

## Rewrite Before Adoption

These ideas may be useful, but should not be ported by copying `schema_v1` directly.

### `embeddings` table

`schema_v1` adds:

- `embeddings(entity_type, entity_id, model, vector)`

Assessment:

- useful idea
- compatible with a future retrieval/search path
- currently unused by hybrid runtime code

Decision:

- rewrite later as a dedicated hybrid feature

Reason:

- should align with actual consumers first:
  - tutor retrieval
  - recommendation/search
  - possible course asset indexing

### `slug`, `version`, `status` additions on `modules` and `topics`

Assessment:

- potentially useful for seed hygiene and future content versioning
- but hybrid still treats `modules/topics` as LMS support content, not the canonical course platform

Decision:

- rewrite only if a clear operational need appears

Reason:

- adding these fields is not inherently wrong
- but porting them now would expand legacy LMS entities without a direct product need

### `learning_objectives`, `assessment_config`, `content_embedding_id` on `topics`

Assessment:

- conceptually useful
- but they belong to a content-authoring/runtime strategy that hybrid has not adopted yet

Decision:

- rewrite later behind a clear service contract

Reason:

- hybrid should not accumulate schema fields with no runtime reader/writer

### extra analytics fields on `questions`

`schema_v1` adds fields such as:

- `source`
- `review_status`
- `num_shown`
- `num_correct`
- `irt_a`
- `irt_b`
- `calibration_status`
- `content_embedding_id`

Assessment:

- some of these are useful
- but hybrid already has overlapping fields:
  - `status`
  - `version`
  - `irt_difficulty`
  - `irt_discrimination`
  - `irt_guessing`
  - `total_responses`

Decision:

- rewrite as an explicit `question analytics / calibration` pass later

Reason:

- copying these fields directly would create overlapping semantics
- hybrid needs one coherent question analytics model, not two partially overlapping ones

## Avoid for Now

These parts should not be ported into hybrid in their current form.

### `user_responses`

`schema_v1` introduces a new `user_responses` table.

Hybrid already has:

- `interactions`

Decision:

- avoid

Reason:

- `interactions` is already the active write model for quiz/assessment/module-test behavior
- adding `user_responses` now would duplicate responsibility and split analytics history across two tables

### `user_mastery`

`schema_v1` introduces:

- `user_mastery(topic_slug, mastery_score, theta, theta_se, ...)`

Hybrid already has:

- `mastery_scores`
- `mastery_history`

Decision:

- avoid

Reason:

- hybrid already has a mastery write/read model in production code
- importing `user_mastery` would create a second mastery system

### `review_schedule`

Assessment:

- useful concept for spaced repetition later
- not currently part of hybrid runtime flow

Decision:

- avoid for now

Reason:

- this is a new product capability, not an infra uplift
- should land only with a service/runtime plan, not as an orphan table

### `tutor_sessions`

Hybrid already has:

- legacy tutor persistence in `qa_history`
- in-context tutor flow under the legacy lecture adapter boundary

Decision:

- avoid for now

Reason:

- adding `tutor_sessions` now would create another parallel tutor persistence model
- tutor persistence should be redesigned only when hybrid moves off the legacy adapter more fully

### trigger-based counters on `questions`

Assessment:

- technically sound
- but tied to `user_responses`, which hybrid is not adopting

Decision:

- avoid for now

Reason:

- if question counters are needed, they should be derived from or integrated with `interactions`, not from a second event table

## Final Classification

### Ported

- `pgvector` runtime image
- `pgvector` extension migration

### Rewrite Later

- `embeddings`
- optional version/status metadata for `modules` and `topics`
- topic content config fields
- question analytics/calibration fields

### Avoid for Now

- `user_responses`
- `user_mastery`
- `review_schedule`
- `tutor_sessions`
- trigger-based question counters tied to `user_responses`

## Recommendation

For hybrid, the correct approach is:

1. keep the existing hybrid canonical/product model
2. take `pgvector` as infra only
3. treat the rest of `schema_v1` as a pool of ideas, not a migration to import
4. implement any future adoption as separate hybrid-native migrations backed by actual runtime requirements
