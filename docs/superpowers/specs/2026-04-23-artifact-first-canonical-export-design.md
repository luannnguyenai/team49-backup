# Artifact-First Canonical Export Design

> **Historical spec:** This document is preserved for implementation history only. Canonical export has already been implemented; use the current exporter code and handoff docs for active behavior.

## Goal

Chuẩn hóa toàn bộ artifact ingestion hiện có thành một bộ canonical export ổn định, machine-readable, và dễ validate để làm input cho bước ingest PostgreSQL sau này mà chưa cần sửa schema DB ngay trong phase này.

Scope phase này chỉ bao gồm:

- canonical `units` export
- canonical question layer export từ P4
- canonical `prerequisite_edges` / `pruned_edges`
- derived fields rule-based, deterministic
- manifest + validation report

Ngoài scope:

- DB migrations
- importer vào PostgreSQL
- embeddings batch
- IRT calibration thật
- learner/planning runtime tables

## Why This Phase First

Repo hiện đã có đủ raw/final artifact để tự suy ra phần content graph cốt lõi:

- `data/courses/*/processed_sanitized/*.json`
- `data/courses/*/processed/P4/**/*.json`
- `data/final_artifacts/cs224n_cs231n_v1/p5_output_transitive_pruned.json`
- `data/final_artifacts/cs224n_cs231n_v1/gpt54_edge_labels.json`

Điểm thiếu lớn nhất hiện tại không phải dữ liệu, mà là thiếu một data contract canonical đủ sạch để:

1. validate count và referential integrity
2. làm baseline cho importer DB sau này
3. benchmark model / audit graph mà không phải chạm lại toàn bộ pipeline

Artifact-first giải quyết đúng nút thắt này với rủi ro thấp hơn schema-first.

## Canonical Output Layout

Canonical export sẽ được ghi vào:

```text
data/final_artifacts/cs224n_cs231n_v1/canonical/
```

Các file chuẩn:

```text
courses.jsonl
concepts_kp.jsonl
units.jsonl
unit_kp_map.jsonl
question_bank.jsonl
item_calibration.jsonl
item_phase_map.jsonl
item_kp_map.jsonl
prerequisite_edges.jsonl
pruned_edges.jsonl
manifest.json
validation_report.json
```

Format chính là `JSONL`.

Không xuất `CSV` trong phase này để tránh tăng surface area và duplicated contract. Nếu cần spreadsheet review sau này thì viết converter riêng từ canonical JSONL ra CSV.

Git strategy cho phase này:

- **Không commit các file JSONL canonical generated output**.
- Chỉ commit code + docs + `manifest.json` + `validation_report.json` khi cần snapshot nhỏ để review.
- JSONL canonical được xem là reproducible build artifact từ source đã versioned.

## Source Mapping

### 1. Courses

Nguồn:

- `data/courses/*/syllabus.json`

Mỗi record canonical trong `courses.jsonl` đại diện cho một course.

Field cốt lõi:

- `course_id`
- `course_name`
- `source`
- `note`
- `reference_slides_no_video`
- `lecture_count`
- `source_file`

Field nullable reserve:

- `track_tags`
- `summary_embedding`

### 2. Concepts

Nguồn:

- `data/final_artifacts/cs224n_cs231n_v1/p2_output_rationale_repaired.json`

Mỗi record canonical trong `concepts_kp.jsonl` đại diện cho một global KP.

Field cốt lõi:

- `kp_id`
- `name`
- `description`
- `track_tags`
- `domain_tags`
- `career_path_tags`
- `difficulty_level`
- `difficulty_source`
- `difficulty_confidence`
- `importance_level`
- `structural_role`
- `importance_confidence`
- `importance_rationale`
- `importance_scope`
- `importance_source`
- `source_course_ids`
- `source_file`

Field derived:

- `importance`

Field nullable reserve:

- `description_embedding`

### 3. Units

Nguồn:

- `data/courses/*/processed_sanitized/*.json`

Mỗi record canonical trong `units.jsonl` đại diện cho một `unit`.

Field cốt lõi:

- `unit_id`
- `course_id`
- `lecture_id`
- `lecture_order`
- `lecture_title`
- `unit_name`
- `description`
- `summary`
- `key_points`
- `content_ref`
- `difficulty`
- `difficulty_source`
- `difficulty_confidence`
- `duration_min`
- `ordering_index`
- `section_flags`
- `source_file`

Rule:

- `lecture_order` được suy ra từ filename `L*_p1.json` hoặc lecture metadata tương ứng.
- `ordering_index` là vị trí unit trong lecture, 1-based nếu source không có index rõ ràng.

Field nullable reserve:

- `video_clip_ref`
- `topic_embedding`

### 4. Unit-KP Map

Nguồn:

- `data/final_artifacts/cs224n_cs231n_v1/p2_output_rationale_repaired.json`

Mỗi record canonical trong `unit_kp_map.jsonl` đại diện cho quan hệ `unit x kp`.

Field cốt lõi:

- `unit_id`
- `kp_id`
- `planner_role`
- `instruction_role`
- `coverage_level`
- `coverage_confidence`
- `coverage_rationale`
- `source_file`

Field derived:

- `coverage_weight`

### 5. Question Layer

Nguồn:

- `data/courses/*/processed/P4/**/*.json`

Tách thành bốn bảng chuẩn:

- `question_bank.jsonl`
- `item_calibration.jsonl`
- `item_phase_map.jsonl`
- `item_kp_map.jsonl`

#### `question_bank.jsonl`

Một dòng cho một item trong `repaired_question_bank`.

Field cốt lõi:

- `item_id`
- `unit_id`
- `course_id`
- `lecture_id`
- `item_type`
- `knowledge_scope`
- `render_mode`
- `question`
- `choices`
- `answer_index`
- `explanation`
- `primary_kp_id`
- `source_ref`
- `difficulty`
- `question_intent`
- `qa_gate_passed`
- `review_status`
- `repair_history`
- `provenance`
- `source_file`

Field nullable reserve:

- `concept_alignment_cosine`
- `distractor_cosine_upper`
- `distractor_cosine_lower`

#### `item_calibration.jsonl`

Nguồn từ `item_calibration_bootstrap`.

Field cốt lõi:

- `item_id`
- `calibration_method`
- `is_calibrated`
- `difficulty_prior`
- `discrimination_prior`
- `guessing_prior`
- `difficulty_b`
- `discrimination_a`
- `guessing_c`
- `irt_calibration_n`
- `standard_error_b`
- `source_file`

Rule:

- Giữ nguyên tinh thần bootstrap / prior-only.
- Không fabricate calibrated IRT values.
- Các field calibrated thật (`difficulty_b`, `discrimination_a`, `guessing_c`, `standard_error_b`) có thể `null`.

#### `item_phase_map.jsonl`

Nguồn từ `item_phase_map`.

Field cốt lõi:

- `item_id`
- `phase`
- `phase_multiplier`
- `suitability_score`
- `source_file`

Field nullable reserve:

- `selection_priority`

#### `item_kp_map.jsonl`

Nguồn từ `item_kp_map`.

Field cốt lõi:

- `item_id`
- `kp_id`
- `kp_role`
- `weight`
- `source_file`

Field nullable reserve:

- `mapping_confidence`

Rule quan trọng:

- File P4 có `target_item_count=0` hoặc `repaired_question_bank=[]` không sinh row cho question layer.
- Nhưng unit tương ứng vẫn tồn tại ở `units.jsonl`.
- `weight` được default-fill rule-based nếu source artifact không có:
  - `primary -> 0.7`
  - `secondary -> 0.3`
  - `support -> 0.0`

### 6. Prerequisite Graph

Nguồn:

- `data/final_artifacts/cs224n_cs231n_v1/p5_output_transitive_pruned.json`
- `data/final_artifacts/cs224n_cs231n_v1/gpt54_edge_labels.json`

#### `prerequisite_edges.jsonl`

Chỉ giữ những edge final có verdict `keep`.

Field cốt lõi:

- `source_kp_id`
- `target_kp_id`
- `edge_scope`
- `provenance`
- `confidence`
- `review_status`
- `rationale`
- `temporal_signal`
- `source_first_seen`
- `target_first_seen`
- `p5_keep_confidence`
- `p5_expected_directionality`
- `p5_trace`
- `source_file`

Field nullable reserve:

- `edge_strength`
- `bidirectional_score`

Rule:

- verdict final lấy từ `gpt54_edge_labels.json` canonical hiện tại.
- không fabricate numeric ML score, nhưng reserve field nullable để fill ở phase ML/embedding sau.
- không dựa vào ModernBERT/SciBERT experiment artifacts trong canonical output này.

#### `pruned_edges.jsonl`

Giữ tất cả edge final có verdict `prune`.

Field cốt lõi tương tự `prerequisite_edges.jsonl`, cộng thêm:

- `prune_reason`

Mục đích:

- audit graph evolution
- benchmark model sau này
- explainability cho edge bị loại

## Derived Fields

Chỉ thêm derived fields deterministic, rule-based, không cần extra model:

### `coverage_weight`

Map từ `coverage_level × coverage_confidence`:

Base per `coverage_level`:

- `dominant -> 1.00`
- `substantial -> 0.75`
- `partial -> 0.50`
- `mention -> 0.25`

Multiplier per `coverage_confidence`:

- `high -> 1.00`
- `medium -> 0.80`
- `low -> 0.60`

Final rule:

```text
coverage_weight = round(base[level] * confidence_multiplier[confidence], 4)
```

### `importance`

Map từ `importance_level × importance_confidence` thành float [0, 1]:

Base per `importance_level`:

- `critical -> 1.00`
- `high -> 0.75`
- `medium -> 0.50`
- `low -> 0.25`

Multiplier per `importance_confidence`:

- `high -> 1.00`
- `medium -> 0.80`
- `low -> 0.60`

Final rule:

```text
importance = round(base[level] * confidence_multiplier[confidence], 4)
```

Có thể áp dụng boost deterministic nhỏ cho `structural_role ∈ {gateway, capstone}` nếu local source contract đã dùng rule đó; nếu chưa có rule commit sẵn, không boost ở phase này.

## Validation Requirements

Mỗi lần export phải sinh `validation_report.json` với hai section:

- `hard_checks`: deterministic, blocking
- `deferred_checks`: phụ thuộc embedding/ML/runtime, non-blocking trong phase này

### Identity and counts

- tổng số `courses`
- tổng số `concepts_kp`
- tổng số `units`
- tổng số `unit_kp_map`
- tổng số `question_bank`
- tổng số `item_calibration`
- tổng số `item_phase_map`
- tổng số `item_kp_map`
- tổng số `prerequisite_edges`
- tổng số `pruned_edges`

### Count consistency

- `question_bank` count phải bằng `item_calibration`
- `question_bank` count phải bằng `item_phase_map`

### Referential integrity

- mọi `units.course_id` tồn tại trong `courses`
- mọi `unit_kp_map.unit_id` tồn tại trong `units`
- mọi `unit_kp_map.kp_id` tồn tại trong `concepts_kp`
- mọi `item_calibration.item_id` tồn tại trong `question_bank`
- mọi `item_phase_map.item_id` tồn tại trong `question_bank`
- mọi `item_kp_map.item_id` tồn tại trong `question_bank`
- mọi `item_kp_map.kp_id` tồn tại trong `concepts_kp`
- mọi `prerequisite_edges.source_kp_id/target_kp_id` tồn tại trong `concepts_kp`
- mọi `pruned_edges.source_kp_id/target_kp_id` tồn tại trong `concepts_kp`

### Ordering integrity

- `units` phải có `lecture_order`
- `units` phải có `ordering_index`
- không có duplicate `(course_id, lecture_id, ordering_index, unit_id)` bất thường

### Duplicate checks

- không duplicate `item_id`
- không duplicate `(unit_id, kp_id)` trong `unit_kp_map`
- không duplicate `(source_kp_id, target_kp_id)` trong `prerequisite_edges`
- không overlap giữa `prerequisite_edges` và `pruned_edges`

### Null/empty checks

- `question` không rỗng
- `primary_kp_id` không rỗng
- `rationale` của edge final không rỗng

### Deterministic hard checks

- `question_bank.primary_kp_id` phải tồn tại trong `concepts_kp`
- `question_bank.source_ref` phải tồn tại
- `source_ref.evidence_span` phải substring-match transcript source tương ứng (case-insensitive, whitespace-normalized)
- `source_ref.multimodal_signals_used` phải chứa `"transcript"` nếu field này hiện diện
- `source_ref.timestamp_start/timestamp_end` phải nằm trong bound của `units.content_ref`
- `units.key_points[].timestamp_s` phải nằm trong bound `content_ref`
- `question_intent` nếu hiện diện phải thuộc `{conceptual, procedural, diagnostic, application}`
- `item_phase_map.phase` phải thuộc enum canonical
- `review_status` phải thuộc enum canonical
- `provenance` phải thuộc taxonomy canonical

### Deferred non-blocking checks

Các check dưới đây phải được log rõ trong `deferred_checks`, không block phase canonical export này:

- `concept_alignment_cosine`
- `distractor_cosine_upper/lower`
- `edge_strength`
- `bidirectional_score`
- bất kỳ embedding-based threshold nào

## Hard-Fail Policy

Canonical export dùng policy sau:

- Script **vẫn ghi đầy đủ canonical JSONL** để phục vụ audit/debug.
- Bất kỳ row nào fail deterministic hard check sẽ **không** đi vào table canonical chính tương ứng; thay vào đó ghi vào:

```text
rejected_items.jsonl
```

với:

- `row_kind`
- `row_id`
- `hard_fail_reason`
- `source_file`
- `payload`

- `validation_report.json` phải liệt kê chi tiết failures.
- Script exit code mặc định là **non-zero** nếu có hard failures.
- Có cờ debug `--allow-hard-fail` để vẫn exit zero khi cần inspect bundle bẩn.

## Manifest Requirements

`manifest.json` là snapshot metadata, gồm:

- `run_id`
- `artifact_version`
- `schema_version`
- `generated_at`
- `source_files`
- `counts`
- `pipeline_versions`
- `checksums`
- `notes`

Mục đích:

- freeze data contract
- hỗ trợ reproducibility
- giúp importer phase sau biết mình đang ingest bundle nào

`checksums` phải ghi `sha256` cho từng file canonical và cho `validation_report.json`.

## Non-Goals and Guardrails

Phase này không được:

- ghi thẳng vào PostgreSQL
- tự ý sửa P1/P4/P5 source artifacts
- generate embeddings
- infer fake calibrated IRT values
- merge experimental model scores vào edge final

Phase này được phép:

- normalize field names
- derive deterministic fields
- enrich provenance/source_file metadata
- generate validation report

## Write Safety

Canonical export phải dùng atomic write strategy:

1. ghi toàn bộ output vào thư mục tạm, ví dụ `canonical.tmp/`
2. chạy validation trên output tạm
3. nếu xong mới replace thư mục `canonical/`

Mục tiêu là tránh trạng thái half-written bundle nếu script crash giữa chừng.

## Recommended Implementation Shape

Triển khai nên là một export pipeline script duy nhất, ví dụ:

```text
src/scripts/pipeline/export_canonical_artifacts.py
```

Thiết kế nội bộ:

- loader P1
- loader P4
- loader P5 + edge audit
- normalizer per artifact family
- validator
- writer JSONL + manifest/report

Mỗi loader/normalizer nên là function nhỏ, pure-data-first, không phụ thuộc DB.

## Success Criteria

Phase này được coi là xong khi:

1. `canonical/` được generate đầy đủ
2. `validation_report.json` pass toàn bộ check cứng
3. counts ổn định và reproducible khi rerun
4. artifact đủ rõ để bước importer/Postgres sau chỉ còn là mapping kỹ thuật

## Decision

Chọn `Artifact-first` làm phase kế tiếp vì đây là bước có leverage cao nhất, ít rủi ro nhất, và tạo được canonical contract production-facing trước khi khóa schema DB ingest.
