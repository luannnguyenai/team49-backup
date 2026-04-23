# Legacy Schema Cleanup Plan

Mục tiêu của tài liệu này là làm rõ phần schema cũ còn tồn tại sau canonical DB/runtime cutover, tránh team tiếp tục build feature mới trên bảng legacy, và chuẩn bị một lộ trình drop/archive an toàn cho production.

## Nguyên tắc

1. Không drop bảng cũ khi chưa chứng minh runtime không còn dependency.
2. Không fabricate mapping từ `topic_id` sang `kp_id`; chỉ dùng canonical bridge/link đã import/backfill.
3. Không đụng frontend/UI trong phase cleanup này.
4. Mọi destructive change phải đi sau backup/export và parity check.
5. Mỗi bước hoàn thành phải có commit riêng để dễ revert.

## Ownership Matrix

| Nhóm | Bảng | Trạng thái mục tiêu | Replacement canonical/product | Ghi chú |
| --- | --- | --- | --- | --- |
| Content legacy | `modules` | Deprecated | `courses`, `course_sections`, `learning_units`, `units` | Không dùng làm source-of-truth mới. |
| Content legacy | `topics` | Deprecated | `learning_units`, `units`, `unit_kp_map` | Planner mới không được rank topic. |
| Content legacy | `knowledge_components` | Deprecated | `concepts_kp`, `unit_kp_map`, `item_kp_map` | Không suy `kp_id` từ KC cũ. |
| Question legacy | `questions` | Deprecated | `question_bank`, `item_calibration`, `item_phase_map`, `item_kp_map` | Assessor canonical phải đọc `question_bank`. |
| Mastery legacy | `mastery_scores` | Deprecated after canonical parity | `learner_mastery_kp` | Còn dùng bởi path topic-grain cũ. |
| Mastery legacy | `mastery_history` | Deprecated after canonical parity | future KP mastery audit | Hiện vẫn neo `topic_id`/`kc_id`. |
| Planner legacy | `learning_paths` | Deprecated after canonical planner parity | `plan_history`, `rationale_log`, canonical planner response | Còn phục vụ compatibility response cũ. |
| Runtime shared | `sessions` | Keep, evolve | same table + `canonical_phase` | Không drop; canonical assessment vẫn cần session. |
| Runtime shared | `interactions` | Keep, evolve | same table + `canonical_item_id` | Không drop; canonical evidence dùng bảng này. |
| Product shell | `courses`, `course_sections`, `learning_units` | Keep authoritative product shell | linked to canonical via bridge columns | Không phải legacy; chỉ cần backfill canonical links. |
| Tutor/QA legacy | `lectures`, `chapters`, `transcript_lines`, `qa_history` | Compatibility | future tutor adapter / canonical transcript layer | Chưa drop nếu tutor/retrieval còn dùng. |
| KG legacy | `kg_concepts`, `kg_edges`, `kg_sync_state` | Compatibility / review separately | `concepts_kp`, `prerequisite_edges` | KG service hiện còn topic-slug oriented. |

## Current Runtime Dependencies

Các dependency dưới đây phải được xử lý trước khi tạo migration drop.

### `questions`

Hiện còn được dùng bởi:

- `src/repositories/question_repo.py`
- `src/repositories/assessment_repo.py`
- `src/repositories/history_repo.py`
- `src/repositories/interaction_repo.py`
- `src/services/assessment_service.py` legacy branch
- quiz/module-test/history schemas và tests liên quan
- `src/kg/loader.py`, `src/kg/providers.py`, `src/kg/service.py`

Cleanup requirement:

- Assessor canonical branch phải dùng `question_bank` cho mọi assessment/quiz/module-test path production.
- History API phải join được cả `interactions.canonical_item_id -> question_bank.item_id`.
- Sau cutover, không tạo row mới trong `questions`.

### `mastery_scores` và `mastery_history`

Hiện còn được dùng bởi:

- `src/repositories/mastery_repo.py`
- `src/repositories/assessment_repo.py`
- `src/services/assessment_service.py` legacy mastery branch
- `src/services/recommendation_engine.py` legacy planner branch
- `src/routers/auth.py`
- `tests/test_user_skill_overview.py`

Cleanup requirement:

- Mastery production phải ghi `learner_mastery_kp`.
- Progress/skill overview phải đọc `learner_mastery_kp` hoặc read-model derived từ KP.
- Nếu cần compatibility trong ngắn hạn, chỉ đọc legacy khi canonical flag tắt.

### `learning_paths`

Hiện còn được dùng bởi:

- `src/services/recommendation_engine.py`
- `src/routers/learning_path.py`
- `src/repositories/course_recommendation_repo.py` indirectly through recommendation flow
- `src/schemas/learning_path.py`

Cleanup requirement:

- Planner production phải trả canonical unit path từ `learning_units` + `unit_kp_map` + `prerequisite_edges`.
- Audit source-of-truth là `plan_history` + `rationale_log`.
- Không dùng `learning_paths.action=skip` để tạo `waived_units`.

### `modules`, `topics`, `knowledge_components`

Hiện còn được dùng bởi:

- `src/routers/content.py`
- `src/repositories/assessment_repo.py`
- `src/repositories/session_repo.py`
- `src/repositories/question_repo.py`
- `src/repositories/history_repo.py`
- `src/services/recommendation_engine.py` legacy branch
- `src/kg/*`
- `src/utils/topological_sort.py`

Cleanup requirement:

- Public product APIs phải đi qua `courses/course_sections/learning_units`.
- Planner/assessor không đọc topic/KC cũ khi canonical flags bật.
- KG topic-slug service cần migration riêng hoặc được đánh dấu compatibility-only.

## Cleanup Task List

### Task 1: Freeze Ownership In Docs

Files:

- `docs/LEGACY_SCHEMA_CLEANUP_PLAN.md`
- `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`
- `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`

Steps:

1. Add ownership matrix.
2. Mark `questions`, `mastery_scores`, `mastery_history`, `learning_paths`, `modules`, `topics`, `knowledge_components` as deprecated for new production work.
3. Mark `sessions` and `interactions` as shared runtime tables, not drop candidates.
4. Commit: `docs: document legacy schema cleanup plan`.

### Task 2: Add Static Legacy Usage Check

Files:

- Create `src/scripts/pipeline/check_legacy_schema_usage.py`
- Create `tests/pipeline/test_check_legacy_schema_usage.py`

Checker behavior:

- Scan `src/` for configured legacy model/table references.
- Exclude migration files and docs.
- Emit JSON with `table`, `status`, `references`.
- Exit non-zero only in strict mode.

Commands:

```bash
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/check_legacy_schema_usage.py
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/check_legacy_schema_usage.py --strict
PYTHONPATH=. .venv/bin/pytest tests/pipeline/test_check_legacy_schema_usage.py -q
```

Commit: `chore: add legacy schema usage checker`.

### Task 3: Add Runtime Deprecation Guards

Files:

- `src/config.py`
- `src/services/assessment_service.py`
- `src/services/recommendation_engine.py`
- `src/repositories/question_repo.py`
- `src/repositories/mastery_repo.py`

Flags:

- `allow_legacy_question_reads`
- `allow_legacy_mastery_writes`
- `allow_legacy_planner_writes`
- `allow_legacy_topic_content_reads`

Behavior:

- Default should preserve current runtime until canonical parity is proven.
- Production cleanup profile can set these to false.
- When false, legacy-only path raises a clear backend error instead of silently writing old tables.

Commit: `feat: add legacy runtime deprecation guards`.

### Task 4: Complete Canonical Read/Write Parity

Files likely involved:

- `src/services/assessment_service.py`
- `src/services/recommendation_engine.py`
- `src/repositories/history_repo.py`
- `src/routers/learning_path.py`
- `src/routers/content.py`

Required parity:

- Assessment selection can serve from `question_bank`.
- Assessment submit writes `interactions.canonical_item_id`.
- Mastery update writes `learner_mastery_kp`.
- Planner reads canonical/product units and writes `plan_history`/`rationale_log`.
- History can display canonical item attempts.
- Product content APIs do not require `modules/topics`.

Commit: `feat: complete canonical runtime parity`.

### Task 5: Archive Legacy Data

Files:

- Create `src/scripts/pipeline/export_legacy_runtime_data.py`
- Create `tests/pipeline/test_export_legacy_runtime_data.py`

Export tables:

- `modules`
- `topics`
- `knowledge_components`
- `questions`
- `mastery_scores`
- `mastery_history`
- `learning_paths`

Output:

- `data/legacy_archive/<timestamp>/<table>.jsonl`
- `data/legacy_archive/<timestamp>/manifest.json`

Rules:

- Read-only.
- Manifest includes row counts and sha256 per file.
- Do not commit archive payloads unless explicitly requested.
- Reuse the legacy cleanup target guard so protected canonical/product tables cannot be exported or prepared for cleanup by mistake.

Preflight examples:

```bash
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/validate_legacy_cleanup_targets.py questions mastery_scores learning_paths
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/validate_legacy_cleanup_targets.py question_bank learning_units
```

Commit: `chore: add legacy data archive exporter`.

### Task 6: Add Destructive Cleanup Migration

Files:

- Create `alembic/versions/<revision>_archive_or_drop_legacy_runtime_tables.py`

Preconditions:

- Static usage checker strict mode passes for production paths.
- Canonical runtime parity checker passes.
- Legacy archive exporter has produced a manifest.
- User explicitly approves destructive migration.

Preferred first destructive step:

- Rename tables to `_legacy_archived` instead of immediate drop:
  - `questions -> questions_legacy_archived`
  - `mastery_scores -> mastery_scores_legacy_archived`
  - `mastery_history -> mastery_history_legacy_archived`
  - `learning_paths -> learning_paths_legacy_archived`
  - `modules -> modules_legacy_archived`
  - `topics -> topics_legacy_archived`
  - `knowledge_components -> knowledge_components_legacy_archived`

Why rename first:

- Keeps rollback possible.
- Breaks accidental runtime dependency loudly.
- Allows one production cycle before final drop.

Commit: `refactor: archive legacy runtime tables`.

### Task 7: Final Drop Migration

Only after one stable production cycle with archived tables unused:

- Drop `_legacy_archived` tables.
- Drop unused enums/indexes if Alembic can do so safely.
- Keep `sessions` and `interactions`.

Commit: `refactor: drop archived legacy runtime tables`.

## Verification Gates

Run before destructive migration:

```bash
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/import_canonical_artifacts_to_db.py --validate-only
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/check_canonical_runtime_parity.py
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/check_legacy_schema_usage.py --strict
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/check_legacy_cleanup_readiness.py
```

If any gate fails, do not rename/drop legacy tables.

## Current Recommendation

Proceed in this order:

1. Commit this cleanup plan.
2. Add the static usage checker.
3. Add deprecation guards.
4. Complete parity gaps in history/content/KG paths.
5. Archive legacy data.
6. Rename legacy tables.
7. Drop archived tables only after one stable cycle.
