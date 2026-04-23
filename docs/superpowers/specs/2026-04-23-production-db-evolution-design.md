# Production DB Evolution Design

## Goal

Chốt thiết kế database cho giai đoạn chuyển từ:

- runtime cũ kiểu `module/topic/question/mastery_scores/learning_paths`

sang:

- product schema kiểu `course-first`
- content graph chuẩn hóa theo canonical artifacts
- learner/planner schema ở grain `kp/unit`

Mục tiêu của tài liệu này là **khóa data model và source-of-truth**, không phải nối logic code ngay trong lượt này.

## Bối cảnh hiện tại

Repo hiện có bốn lớp dữ liệu cùng tồn tại:

1. **Legacy tutor layer**
   - `lectures`
   - `chapters`
   - `transcript_lines`
   - `qa_history`
   - `learning_progress`

2. **Runtime content + learning layer cũ**
   - `modules`
   - `topics`
   - `knowledge_components`
   - `questions`
   - `sessions`
   - `interactions`
   - `mastery_scores`
   - `learning_paths`

3. **Course-first product layer**
   - `courses`
   - `course_overviews`
   - `course_sections`
   - `learning_units`
   - `course_assets`
   - `learning_progress_records`
   - `learner_assessment_profiles`
   - `course_recommendations`
   - `tutor_context_bindings`
   - `legacy_lecture_mappings`

4. **Canonical ingestion contract**
   - `courses.jsonl`
   - `concepts_kp.jsonl`
   - `units.jsonl`
   - `unit_kp_map.jsonl`
   - `question_bank.jsonl`
   - `item_calibration.jsonl`
   - `item_phase_map.jsonl`
   - `item_kp_map.jsonl`
   - `prerequisite_edges.jsonl`
   - `pruned_edges.jsonl`

Ngoài ra, nhánh hiện đã thêm sidecar planner/learner tables:

- `learner_mastery_kp`
- `goal_preferences`
- `waived_units`
- `plan_history`
- `rationale_log`
- `planner_session_state`

## Quyết định kiến trúc

### 1. Course-first product schema là business shell chính

Các bảng sau tiếp tục là shell runtime của sản phẩm:

- `courses`
- `course_overviews`
- `course_sections`
- `learning_units`
- `course_assets`
- `learning_progress_records`
- `learner_assessment_profiles`

Ý nghĩa:

- đây là lớp product/UI-facing
- chịu trách nhiệm catalog, learn page, progress, assets
- không cố gánh toàn bộ semantics của KP graph, calibration, planner rationale

### 2. Canonical content graph đã được materialize thành DB tables riêng

Production DB hiện có ORM + Alembic cho các bảng first-class tương ứng canonical JSONL:

- `concepts_kp`
- `units`
- `unit_kp_map`
- `question_bank`
- `item_calibration`
- `item_phase_map`
- `item_kp_map`
- `prerequisite_edges`
- `pruned_edges`

Lý do:

- canonical JSONL hiện đã là contract sạch nhất của pipeline
- nếu không materialize thành bảng thật, toàn bộ planner/assessor sau này sẽ phải đọc file JSONL hoặc qua mapping tạm
- làm production thì không nên giữ source-of-truth dạng file bootstrap quá lâu

Implementation hiện tại:

- ORM: `src/models/canonical.py`
- Migration: `alembic/versions/20260423_canonical_content_tables.py`
- Importer: `src/scripts/pipeline/import_canonical_artifacts_to_db.py`
- Importer có `--validate-only` để kiểm tra JSONL + manifest counts trước khi ghi DB

### 3. Learner/planner phải chuyển dần sang grain `kp/unit`

Đích đến production:

- learner mastery authoritative nằm ở `learner_mastery_kp`
- planning/audit authoritative nằm ở:
  - `goal_preferences`
  - `waived_units`
  - `plan_history`
  - `rationale_log`
  - `planner_session_state`

`mastery_scores` và `learning_paths` cũ chỉ nên giữ vai trò compatibility layer trong giai đoạn chuyển tiếp.

### 4. Không rewrite “big bang”

Không nên xóa ngay runtime cũ.

Thay vào đó:

- thêm bảng mới
- backfill dữ liệu
- chuyển dần read path
- chuyển dần write path
- chỉ deprecate bảng cũ sau khi đạt parity

## Target source-of-truth matrix

## A. User / goal / planner state

### `users`

Giữ lại:

- account identity
- auth
- profile nhẹ

Không dùng làm nơi nhét thêm planner state phức tạp.

### `goal_preferences`

Source of truth cho:

- selected course set
- goal weights
- goal embedding

Tất cả planner run phải snapshot từ đây, không suy ngược từ `learning_paths`.

### `waived_units`

Source of truth cho skip/waive audit.

Nếu một unit bị bỏ qua vì learner đã master:

- evidence nằm ở đây
- không chỉ encode bằng `learning_paths.action = skip`

### `plan_history`

Source of truth cho mỗi planner run.

Mỗi lần generate/replan phải sinh một row mới.

### `rationale_log`

Source of truth cho explainability per unit.

### `planner_session_state`

Source of truth cho planner-local counters và sticky state qua nhiều lượt.

## B. Product content shell

### `courses`

Giữ vai trò:

- shell business table cho course
- slug/title/visibility/order/marketing metadata

Không nên dùng nó để chứa toàn bộ ingestion metadata từ canonical `courses.jsonl`.

Nếu cần provenance ingest, dùng mapping/import tables riêng hoặc metadata JSON bổ sung, không biến `courses` thành dump của pipeline.

### `course_sections`

Source of truth cho product hierarchy hiển thị.

### `learning_units`

Source of truth cho:

- unit shell
- slug/title/order
- product-facing entry mode
- estimated minutes

Nhưng **không** là source of truth cho:

- unit-KP coverage
- key points canonical
- question provenance sâu

Các thứ đó nên nằm ở bảng canonical tương ứng.

### `learning_progress_records`

Source of truth cho runtime progress/resume:

- `status`
- `last_position_seconds`
- `last_opened_at`
- `completed_at`

Đây là bảng chính cho “học dở rồi quay lại”.

## C. Canonical content graph

### `concepts_kp`

Source of truth cho global concept graph.

### `unit_kp_map`

Source of truth cho:

- KP nào xuất hiện trong unit
- mức coverage
- role cho planner/instruction

### `question_bank`

Source of truth cho authored items.

### `item_calibration`

Source of truth cho prior và IRT calibration.

### `item_phase_map`

Source of truth cho phase suitability.

### `item_kp_map`

Source of truth cho Q-matrix baseline.

### `prerequisite_edges`

Source of truth cho graph prerequisite đã giữ lại.

### `pruned_edges`

Source of truth cho audit những cạnh đã bị loại.

## D. Legacy / compatibility tables

### Giữ tạm nhưng không phát triển thêm

- `lectures`
- `chapters`
- `transcript_lines`
- `qa_history`
- `learning_progress`
- `modules`
- `topics`
- `knowledge_components`
- `questions`
- `mastery_scores`
- `learning_paths`

Rule:

- không thêm feature mới vào các bảng này nếu feature đó đã có home rõ ràng ở schema mới
- chỉ dùng chúng cho compatibility/adapters trong giai đoạn chuyển tiếp

## Bảng nào cần thêm/đổi ở DB

## 1. Đã materialize từ canonical artifacts

Các bảng dưới đây đã có ORM + Alembic migration:

- `concepts_kp`
- `units`
- `unit_kp_map`
- `question_bank`
- `item_calibration`
- `item_phase_map`
- `item_kp_map`
- `prerequisite_edges`
- `pruned_edges`

## 2. Đã có stub, cần xem là production tables mới

- `learner_mastery_kp`
- `goal_preferences`
- `waived_units`
- `plan_history`
- `rationale_log`
- `planner_session_state`

## 3. Cần chỉnh semantic nhưng không cần xóa ngay

- `mastery_scores`
- `learning_paths`
- `questions`
- `sessions`

Các bảng này sẽ tiếp tục tồn tại trong giai đoạn chuyển tiếp, nhưng không còn là target lâu dài cho planner/assessor đời mới.

## Handoff contract cho người nối code

Đây là phần quan trọng nhất của tài liệu.

### 1. Đừng đoán source-of-truth

Người nối code phải theo matrix này:

- goal selection: `goal_preferences`
- KP mastery: `learner_mastery_kp`
- unit skip evidence: `waived_units`
- planner run snapshot: `plan_history`
- planner explanations: `rationale_log`
- planner transient counters: `planner_session_state`
- unit resume: `learning_progress_records`
- concept graph: `concepts_kp`
- item authoring: `question_bank`
- item-to-KP mapping: `item_kp_map`
- phase selection: `item_phase_map`
- prerequisite graph: `prerequisite_edges`

### 2. Tránh double write không kiểm soát

Trong giai đoạn đầu:

- nếu một flow đã bắt đầu viết vào bảng mới, phải document rõ nó còn có viết vào bảng cũ không
- không để “có khi viết vào `mastery_scores`, có khi viết vào `learner_mastery_kp`” mà không có policy

### 3. Chưa xóa compatibility layer

Người tích hợp không nên xóa ngay:

- `mastery_scores`
- `learning_paths`
- `questions`
- `topics`

Cho tới khi:

- read paths mới đã ổn
- write paths mới đã ổn
- dashboard/query chính đã chuyển xong

### 4. Tất cả backfill phải idempotent

Backfill scripts sau này phải:

- có deterministic source
- có dry-run mode
- rerun được không sinh duplicate logic

### 5. Planner integration phải ghi audit trước

Khi nối planner mới:

1. ghi `plan_history`
2. ghi `rationale_log`
3. cập nhật `planner_session_state`
4. nếu có skip thật sự, ghi `waived_units`

Không nên sinh recommendation mà không có audit trail.

## Migration order khuyến nghị

### Phase 1 — Schema foundation

Done hoặc gần done:

- thêm planner/learner stub tables

### Phase 2 — Canonical content tables vào DB

Status:

- Done
- Commit: `c8c4213` `feat: materialize canonical content schema`
- Tables:
  - `concepts_kp`
  - `units`
  - `unit_kp_map`
  - `question_bank`
  - `item_calibration`
  - `item_phase_map`
  - `item_kp_map`
  - `prerequisite_edges`
  - `pruned_edges`

### Phase 3 — Backfill/import

Status:

- Importer implemented
- Commit: `e7547b2` `feat: add canonical content importer`
- Validate-only command:

```bash
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/import_canonical_artifacts_to_db.py --validate-only
```

- Verified counts:
  - `concepts_kp = 470`
  - `units = 295`
  - `unit_kp_map = 767`
  - `question_bank = 985`
  - `item_calibration = 985`
  - `item_phase_map = 6699`
  - `item_kp_map = 1171`
  - `prerequisite_edges = 79`
  - `pruned_edges = 34`

### Phase 4 — Read-path cutover

Việc cần làm:

- planner read từ bảng mới
- assessor read từ `question_bank` + `item_kp_map` + `item_calibration`
- goal read từ `goal_preferences`

### Phase 5 — Write-path cutover

Việc cần làm:

- learner mastery update vào `learner_mastery_kp`
- planner run ghi vào `plan_history` / `rationale_log`
- skip verification ghi vào `waived_units`

### Phase 6 — Compatibility deprecation

Chỉ khi đã ổn:

- hạ vai trò hoặc freeze `mastery_scores`
- hạ vai trò hoặc freeze `learning_paths`
- giảm phụ thuộc vào `topics/questions` cũ

## Những gì không nên làm trong phase DB-only này

- không nối vội service/router nếu contract chưa rõ
- không tự ý map `topic_id -> kp_id` bằng heuristic ngầm trong runtime
- không xóa bảng cũ chỉ vì “đã có bảng mới”
- không dual-write nếu chưa có ownership rule

## Kết luận

Nếu mục tiêu là production, việc đúng nhất bây giờ không phải nhồi thêm logic vào schema cũ, mà là:

1. khóa source-of-truth mới
2. materialize canonical layer vào DB
3. coi các bảng stub learner/planner là production landing zone
4. để người nối code làm cutover có kiểm soát

Tài liệu này nhằm đảm bảo người làm bước integration sau không phải đoán:

- bảng nào authoritative
- bảng nào chỉ compatibility
- nên migrate theo thứ tự nào
- và audit trail phải rơi vào đâu
