# THINGS NEED FIX

Date: 2026-04-23
Branch: `rin/implement`

## Context

Branch `rin/implement` has moved the product/content surface toward canonical data. The following areas are already cleaned up and should not be reintroduced:

- Frontend no longer calls `/api/modules` or `/api/topics/*`.
- Backend removed `/api/modules`, `/api/topics/*`, and `/api/seed`.
- Content routes now use `/api/course-sections`, `/api/course-sections/{id}`, and `/api/learning-units/{id}/content`.
- Runtime defaults are canonical-first and legacy flags default to disabled.
- Profile skill overview reads `learner_mastery_kp`.
- History reads canonical `question_bank` rows only.
- Planner generation/list/timeline reads canonical planner audit data; legacy `learning_paths` writes are blocked.
- Legacy public content routes `/api/modules` and `/api/topics/*` are removed.

The remaining work is mostly assessor/quiz/module-test migration and final legacy ORM/table removal.

## Non-Negotiables

- Do not touch UI visuals/layout unless explicitly requested.
- Do not re-enable legacy routes or default legacy flags.
- Do not add new compatibility fallback branches back into runtime services.
- Do not write new data into `modules`, `topics`, `questions`, `mastery_scores`, or `learning_paths`.
- Keep canonical product/content tables protected: `courses`, `course_sections`, `learning_units`, `concepts_kp`, `units`, `unit_kp_map`, `question_bank`, `item_*`, `learner_mastery_kp`, `goal_preferences`, `waived_units`, `plan_history`, `rationale_log`, `planner_session_state`.
- Any DB table cleanup must happen only after runtime imports are removed and an archive/export path is verified.
- Commit after each completed task with focused tests.

## Task 1: Migrate Assessment Fully To Canonical

Current risk:

- `src/services/assessment_service.py` still imports and uses legacy `Question`, `Topic`, `KnowledgeComponent`, and `MasteryScore`.
- It has legacy fallback paths guarded by `allow_legacy_question_reads` and `allow_legacy_mastery_writes`.

Required changes:

- Make `start_assessment` require `canonical_unit_ids` and always select from `question_bank` through `CanonicalQuestionSelector`.
- Remove topic-id question selection, `QuestionSelector`, `QuestionRepository`, and 2PL logic tied to legacy `Question`.
- Make `submit_assessment` accept only `canonical_item_id` answers.
- Always write interactions with `canonical_item_id`; never write `question_id`.
- Always update `learner_mastery_kp` through `update_kp_mastery_from_item`.
- Make `get_assessment_results` rebuild results from canonical interaction + question_bank rows, or return the current session-level summary if per-KP aggregation is not ready.
- Delete legacy guard tests and replace them with canonical-only tests.

Files likely involved:

- `src/services/assessment_service.py`
- `src/repositories/assessment_repo.py`
- `src/schemas/assessment.py`
- `tests/services/test_assessment_canonical_cutover.py`
- `tests/services/test_assessment_canonical_mastery_cutover.py`
- `tests/test_assessment_question_selector_integration.py`

Acceptance criteria:

- No `src.services.assessment_service` import of `Question`, `Topic`, `KnowledgeComponent`, `MasteryScore`, `QuestionRepository`, or `QuestionSelector`.
- `rg "allow_legacy_question_reads|allow_legacy_mastery_writes" src/services/assessment_service.py` returns no runtime guard usage.
- Assessment start/submit tests pass using canonical item IDs.

Suggested tests:

- `uv run pytest tests/services/test_assessment_canonical_cutover.py tests/services/test_assessment_canonical_mastery_cutover.py -q`
- Add a contract/integration test for `/api/assessment/start` using `canonical_unit_ids`.

## Task 2: Migrate Quiz Fully To Canonical

Current risk:

- `src/services/quiz_service.py` still uses legacy `Question`, `MasteryScore`, and `LearningPath`.
- It still contains legacy question selection, legacy mastery update, and legacy learning path status update.

Required changes:

- Make quiz start read from `question_bank` by canonical learning unit / unit id.
- Remove legacy `Question` selection helpers.
- Make answer/complete flow validate `canonical_item_id` only.
- Write interactions with `canonical_item_id`.
- Update `learner_mastery_kp`; do not write `mastery_scores`.
- Do not update legacy `learning_paths`. If progress tracking is needed, create or use canonical progress/audit table instead.
- Replace legacy guard tests with canonical quiz tests.

Files likely involved:

- `src/services/quiz_service.py`
- `src/repositories/question_repo.py`
- `src/repositories/mastery_repo.py`
- `src/schemas/quiz.py`
- `tests/services/test_quiz_legacy_guards.py`
- existing quiz route/unit tests

Acceptance criteria:

- No `Question`, `MasteryScore`, or `LearningPath` imports in `quiz_service.py`.
- No legacy guard functions in quiz service.
- Quiz test data uses `question_bank`/`item_kp_map`, not `questions`.

Suggested tests:

- `uv run pytest tests/services/test_quiz_legacy_guards.py -q` should be replaced by canonical quiz tests.
- Run frontend quiz unit tests after API shape is confirmed.

## Task 3: Migrate Module-Test Fully To Canonical

Current risk:

- `src/services/module_test_service.py` still uses legacy `Question`, `MasteryScore`, and `LearningPath`.
- It still inserts remediation into legacy `learning_paths`.

Required changes:

- Make module-test start use canonical section/unit refs and `question_bank`.
- Make submit/results logic use canonical item rows.
- Update `learner_mastery_kp`.
- Replace legacy remediation writes with canonical planner audit / rationale rows, or mark this feature unsupported until canonical remediation is implemented.
- Remove legacy question/mastery/planner guards.

Files likely involved:

- `src/services/module_test_service.py`
- `src/schemas/module_test.py`
- `tests/services/test_module_test_legacy_guards.py`
- existing module-test route/unit tests

Acceptance criteria:

- No `Question`, `MasteryScore`, or `LearningPath` imports in `module_test_service.py`.
- No writes to legacy `learning_paths`.
- Module-test flow can run from canonical section/unit IDs only.

Suggested tests:

- Replace `tests/services/test_module_test_legacy_guards.py` with canonical module-test service tests.
- Add one submit test that verifies `learner_mastery_kp` update.

## Task 4: Remove Legacy Question/Mastery Repositories

Current risk:

- Several repositories still exist only for legacy tables.

Required changes:

- Remove or archive code paths using:
  - `src/repositories/question_repo.py`
  - `src/repositories/mastery_repo.py`
  - legacy methods in `src/repositories/assessment_repo.py`
  - legacy methods in `src/repositories/interaction_repo.py` if only `question_id`-based.
- Keep canonical repositories:
  - `canonical_question_repo.py`
  - `learner_mastery_kp_repo.py`
  - `canonical_content_repo.py`
  - `planner_audit_repo.py`

Acceptance criteria:

- `rg "QuestionRepository|MasteryRepository|get_mastery_score|get_questions_by_ids|get_topic_map|get_kc_name_map" src tests` only returns deleted tests/docs or no runtime usage.
- Canonical assessor/quiz/module-test tests still pass.

## Task 5: Clean Legacy ORM Exports

Current risk:

- `src/models/content.py` still defines `Module`, `Topic`, `KnowledgeComponent`, `Question`.
- `src/models/learning.py` still defines `MasteryScore` and `LearningPath`.
- `src/models/__init__.py` exports legacy classes.
- Some canonical/shared enums still live in legacy files.

Required changes:

- Move shared enums needed by canonical schemas/services to a neutral module, for example `src/models/enums.py`.
- Update imports for `BloomLevel`, `DifficultyBucket`, `CorrectAnswer`, `QuestionStatus`.
- Remove legacy exports from `src/models/__init__.py`.
- Only delete legacy ORM classes after tasks 1-4 have removed runtime references.

Acceptance criteria:

- `rg "from src.models.content import" src tests` no longer points to runtime services.
- `rg "MasteryScore|LearningPath\\b" src tests` no longer points to runtime product code, except non-legacy KG schema names that are unrelated.

## Task 6: Remove Or Replace Legacy KG Routes

Current risk:

- `src/kg/router.py` is guarded by `allow_legacy_kg_routes` and still describes legacy KG backed by module/topic/question/KC data.

Required changes:

- Decide one of two paths:
  - Remove legacy KG router entirely from app mount.
  - Replace with canonical KG endpoints backed by `concepts_kp`, `unit_kp_map`, and `prerequisite_edges`.
- Update KG tests accordingly.

Acceptance criteria:

- `allow_legacy_kg_routes` is removed from `src/config.py`.
- `src/kg/router.py` no longer references legacy module/topic/question/KC data.
- If removed, stale KG routes return 404.
- If replaced, endpoint names and schemas use KP/unit terminology, not topic/module terminology.

## Task 7: Remove Legacy Config Flags

Current risk:

- Config still exposes legacy flags even though defaults are disabled.

Required changes:

- Remove flags after dependent guards are gone:
  - `allow_legacy_question_reads`
  - `allow_legacy_mastery_reads`
  - `allow_legacy_mastery_writes`
  - `allow_legacy_planner_writes`
  - `allow_legacy_topic_content_reads`
  - `allow_legacy_kg_routes`
- Update `tests/test_config.py`.
- Update `.env.example` if these flags appear there.

Acceptance criteria:

- `rg "allow_legacy_" src tests .env.example` returns no runtime config references.

## Task 8: Final DB Table Archive/Drop

Current risk:

- Migration `20260423_archive_legacy_runtime_tables.py` archives legacy tables, but code cleanup must happen before this becomes final production migration.

Required changes:

- Run legacy usage scanner:
  - `uv run python -m src.scripts.pipeline.check_legacy_cleanup_readiness`
- Confirm no runtime references remain.
- Archive/drop allowed legacy tables only:
  - `questions`
  - `mastery_scores`
  - `mastery_history`
  - `learning_paths`
  - `modules`
  - `topics`
  - `knowledge_components`
- Do not touch protected canonical/product tables.

Acceptance criteria:

- Legacy cleanup readiness reports no blockers.
- Alembic upgrade passes.
- Focused backend tests pass.

## Task 9: Remove Legacy Seed/Data Docs

Current risk:

- `scripts/seed.py` still seeds legacy `modules`, `topics`, `knowledge_components`, and `questions`.
- Some docs still mention module/topic/question bootstrap as if it were production data.

Required changes:

- Replace `scripts/seed.py` with a canonical importer entrypoint, or delete it if canonical import is already covered elsewhere.
- Update docs that still tell engineers to seed `modules/topics/questions`.
- Keep repository `data/` artifacts as bootstrap/import inputs only, not runtime source-of-truth.

Files likely involved:

- `scripts/seed.py`
- `docs/LEGACY_SCHEMA_CLEANUP_PLAN.md`
- `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`
- README files if they mention old seed commands

Acceptance criteria:

- `rg "data/bootstrap/modules|data/bootstrap/topics|scripts/seed.py|modules/topics/questions" scripts docs README*` returns only historical/archive references or no runtime setup instructions.
- Canonical importer docs say exactly which JSONL files/tables are authoritative.

## Task 10: Final Verification Gate

Required checks:

- Run backend focused tests:
  - `uv run pytest tests/test_config.py -q`
  - `uv run pytest tests/contract/test_canonical_content_routes.py -q`
  - `uv run pytest tests/services/test_assessment_canonical_cutover.py tests/services/test_assessment_canonical_mastery_cutover.py -q`
  - `uv run pytest tests/repositories/test_history_repo.py tests/services/test_history_service_canonical_detail.py -q`
  - `uv run pytest tests/services/test_recommendation_engine_canonical_cutover.py -q`
- Run legacy readiness scan:
  - `uv run python -m src.scripts.pipeline.check_legacy_cleanup_readiness`
- Run targeted runtime scan:
  - `rg "allow_legacy_|from src.models.content import|MasteryScore|LearningPath|QuestionRepository|MasteryRepository" src tests scripts`

Acceptance criteria:

- Focused tests pass.
- Readiness scan reports no blockers.
- Targeted runtime scan has no production runtime hits, except intentionally retained archive/docs/test fixtures.

## Recommended Commit Order

1. `refactor: make assessment canonical only`
2. `refactor: make quiz canonical only`
3. `refactor: make module test canonical only`
4. `refactor: remove legacy question mastery repositories`
5. `refactor: remove legacy ORM exports`
6. `refactor: remove legacy kg surface`
7. `refactor: remove legacy runtime flags`
8. `chore: finalize legacy table cleanup`
9. `chore: remove legacy seed docs`
10. `test: verify canonical runtime cutover`

## Quick Verification Commands

```bash
uv run pytest tests/test_config.py -q
uv run pytest tests/contract/test_canonical_content_routes.py -q
uv run pytest tests/services/test_assessment_canonical_cutover.py tests/services/test_assessment_canonical_mastery_cutover.py -q
uv run pytest tests/services/test_recommendation_engine_canonical_cutover.py -q
uv run pytest tests/repositories/test_history_repo.py tests/services/test_history_service_canonical_detail.py -q
rg "allow_legacy_|from src.models.content import|MasteryScore|LearningPath" src tests
```

## Current Known Clean State

Latest completed cleanup commits before this handoff:

- `bf25a13 refactor: default runtime to canonical data`
- `f542bfd refactor: remove legacy content seed endpoint`
- `5970b76 refactor: use canonical mastery for skill overview`
- `66d06df refactor: make history reads canonical only`
- `c8b4752 refactor: remove legacy planner branch`
- `7b87e48 refactor: remove legacy content routes`
