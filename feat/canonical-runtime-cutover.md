# Feature: Canonical Runtime Cutover

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `1. Tổng quan hệ thống`, `2. Kiến trúc ứng dụng`, `4. Backend architecture`, `6. Canonical data model`

## 1. Mục tiêu
Canonical runtime cutover là việc chuyển hệ thống từ legacy schema/topic-grain sang một runtime course-first, unit-grain, KP-grounded, trong đó PostgreSQL canonical tables trở thành source of truth cho assessment, planner, và learner state.

## 2. User/problem this solves
Trước cutover, dữ liệu curriculum, question, mastery, và planner nằm ở nhiều schema lịch sử, dễ gây:
- schema drift;
- route contract không ổn định;
- khó import/validate dữ liệu mới;
- khó xây adaptive features trên cùng một data model.

Cutover giải quyết bài toán nền tảng dữ liệu cho toàn bộ platform.

## 3. System scope
Models/migrations:
- `src/models/canonical.py`
- `src/models/course.py`
- `src/models/learning.py`
- `alembic/versions/*canonical*`
- `alembic/versions/*runtime_canonical_bridge*`

Pipeline/scripts:
- `src/scripts/pipeline/import_canonical_artifacts_to_db.py`
- `src/scripts/pipeline/import_product_shell_to_db.py`
- `src/scripts/pipeline/backfill_product_canonical_links.py`
- `src/scripts/pipeline/check_canonical_runtime_parity.py`

Reference docs:
- `README.md`
- `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`
- `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`

## 4. Architecture & flow

```text
canonical JSONL artifacts
  -> validate manifest/counts
  -> import vào PostgreSQL canonical tables
  -> import product shell (courses/sections/units)
  -> backfill canonical bridge columns
  -> parity check
  -> runtime services đọc canonical tables thay vì legacy tables
```

Đây không phải migration "một lần xong", mà là cutover có bridge columns, feature flags, parity checks, và service-level rewiring.

## 5. Key components
- Canonical content tables: `concepts_kp`, `units`, `unit_kp_map`, `question_bank`, `item_calibration`, `item_phase_map`, `item_kp_map`, `prerequisite_edges`, `pruned_edges`.
- Product shell: `courses`, `course_sections`, `learning_units`.
- Learner/planner runtime: `goal_preferences`, `learner_mastery_kp`, `waived_units`, `plan_history`, `rationale_log`, `planner_session_state`.
- Bridge columns: `canonical_course_id`, `canonical_unit_id`, `canonical_item_id`.

## 6. Data model / contracts
Sau cutover:
- content selection đọc canonical question tables;
- planner đọc unit/KP/prerequisite graph;
- interactions link bằng `canonical_item_id`;
- public API dùng `learning_unit_id`, `section_id`, `learning_unit_results`.

Legacy runtime tables như `modules`, `topics`, `questions`, `mastery_scores`, `learning_paths` không còn là active contract cho product logic mới.

## 7. Technical decisions
- Tách canonical artifact layer khỏi runtime product shell nhưng nối bằng bridge columns.
- Importer idempotent theo natural keys + manifest verification.
- Dùng parity checker trước khi freeze/drop logic cũ.
- Chuyển dần bằng feature flags/read-write gates thay vì big-bang trong service layer.

## 8. Risks / trade-offs
- Đây là feature có blast radius lớn nhất trong repo.
- Nếu bridge/backfill thiếu, planner và assessment có thể hỏng thầm lặng.
- Docs lịch sử dễ gây nhầm source of truth nếu team không chốt active contract rõ.
- Chi phí migration và test cao, nhưng đổi lại hệ thống có nền dữ liệu để phát triển tiếp.

## 9. Testing / validation
Scripts:
- `import_canonical_artifacts_to_db --validate-only`
- `import_product_shell_to_db --validate-only`
- `check_canonical_runtime_parity`

Tests:
- `tests/pipeline/test_import_canonical_artifacts_to_db.py`
- `tests/pipeline/test_import_product_shell_to_db.py`
- `tests/pipeline/test_check_canonical_runtime_parity.py`
- `tests/services/test_*canonical_cutover.py`

Report cần nêu rõ:
- observed counts,
- parity status,
- route contract changes,
- what was dropped vs what remains compatibility-only.

## 10. Demo-worthy points
- Đây là feature rất mạnh để đưa vào technical report nếu bạn muốn nhấn vào architecture/data engineering.
- Nó thể hiện khả năng làm migration có audit, không chỉ code feature bề mặt.
- Gần như mọi feature khác trong repo đều đứng trên nền cutover này.
