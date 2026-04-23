# Schema Branch Snapshot — 2026-04-23

Branch hiện tại: `rin/implement`

## Mục đích tài liệu

File này chốt lại 3 thứ:

1. Schema runtime thực tế trong code hiện đang có những bảng gì.
2. Canonical artifact layer mà nhánh này vừa chuẩn hóa thêm đang đại diện cho dữ liệu nào.
3. Ý định của từng field chính là gì, để sau này không bị lẫn giữa:
   - schema app/runtime đang chạy
   - schema chuyển tiếp legacy
   - schema canonical ingest artifact mới

## Tóm tắt nhánh này đang làm gì

Trong nhánh `rin/implement`, phần việc dữ liệu/schema gần đây tập trung vào:

- chuẩn hóa dữ liệu course của `CS224n` và `CS231n`
- sửa P1/P2/P3/P4/P5 để loại bỏ placeholder ID, timestamp drift, mapping lỗi
- tạo canonical exporter để gom các artifact ingestion về một contract sạch, machine-readable
- thêm lớp runtime stub cho learner/planner để chuẩn bị migrate từ grain `topic/module` sang `kp/unit`
- xuất bộ canonical JSONL cuối cùng ở:
  - `data/final_artifacts/cs224n_cs231n_v1/canonical/`
- xác nhận canonical bundle sạch:
  - `courses = 2`
  - `concepts_kp = 470`
  - `units = 295`
  - `unit_kp_map = 767`
  - `question_bank = 985`
  - `item_calibration = 985`
  - `item_phase_map = 6699`
  - `item_kp_map = 1171`
  - `prerequisite_edges = 79`
  - `pruned_edges = 34`
  - `rejected_items = 0`

## Cách đọc schema hiện tại

Hiện repo có 3 lớp dữ liệu khác nhau:

### 1. Runtime ORM schema

Nằm trong:

- `src/models/user.py`
- `src/models/content.py`
- `src/models/course.py`
- `src/models/learning.py`

Đây là schema app/backend thực tế đang dùng để chạy sản phẩm.

### 2. Legacy adapter schema

Nằm trong:

- `src/models/store.py`

Đây là các bảng cũ cho stack tutor/lecture trước đây, vẫn còn để tương thích ngược.

### 3. Canonical artifact schema

Nằm trong:

- `data/final_artifacts/cs224n_cs231n_v1/canonical/*.jsonl`

Đây là contract sạch để ingest PostgreSQL.

Hiện đã có DB materialization tương ứng:

- ORM: `src/models/canonical.py`
- Migration: `alembic/versions/20260423_canonical_content_tables.py`
- Importer: `src/scripts/pipeline/import_canonical_artifacts_to_db.py`
- Integration handoff: `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`

Importer chạy idempotent bằng natural keys, có `--validate-only` để kiểm tra manifest/counts trước khi ghi DB, và verify DB row counts sau import thật.

### 4. Learner / planner stub persistence

Nằm trong:

- `src/models/learning.py`
- `alembic/versions/20260423_learner_planner_stub_persistence.py`

Đây là lớp mới vừa được thêm vào nhánh này để giữ chỗ cho:

- mastery ở grain `user × kp`
- goal profile chính thức
- waived/skip audit
- plan history / rationale / session state

Nó chưa thay thế runtime cũ, mà là lớp sidecar để phase backend tiếp theo có điểm rơi rõ ràng.

### Trạng thái wiring runtime hiện tại

Hiện có 2 write-path đã được nối vào sidecar layer, đều nằm sau feature flag:

- `goal_preferences`
  - writer: `src/services/auth_service.py:update_onboarding`
  - flag: `write_goal_preferences_enabled`
  - dữ liệu hiện tại là **compatibility snapshot từ onboarding cũ**
  - `goal_weights_json` đang giữ:
    - `available_hours_per_week`
    - `preferred_method`
    - `legacy_desired_module_count`
    - `legacy_known_topic_count`
  - `notes` giữ JSON-encoded:
    - `legacy_desired_module_ids`
    - `legacy_known_topic_ids`
  - `selected_course_ids` vẫn để `null` vì onboarding hiện còn ở grain `module/topic`, chưa phải `course-first`

- `plan_history` / `rationale_log` / `planner_session_state`
  - writer: `src/services/recommendation_engine.py:generate_learning_path`
  - flag: `write_planner_audit_enabled`
  - dữ liệu hiện tại là **legacy topic-grain audit**
  - `recommended_path_json` lưu:
    - `topic_id`
    - `module_name`
    - `action`
    - `estimated_hours`
    - `order_index`
    - `week_number`
  - `rationale_log.learning_unit_id` hiện để `null`
  - `reason_code` được namespace theo dạng `legacy_topic_<action>`
  - `planner_session_state.session_id` hiện cố định là `learning-path`

Hai bảng sau vẫn mới chỉ dừng ở mức schema foundation, chưa nối runtime:

- `learner_mastery_kp`
  - chưa có bridge live từ `topic/module` runtime sang canonical `kp_id`
  - nếu ép ghi ngay sẽ phải fabricate `kp_id` hoặc tạo drift giữa topic mastery và KP mastery

- `waived_units`
  - skip flow hiện tại vẫn ở grain `topic` qua `learning_paths.status=skipped`
  - chưa có `learning_unit_id` authoritative tại đúng điểm runtime đó
  - nếu ép ghi ngay sẽ tạo waive audit sai grain

## A. Runtime ORM Schema

## A1. `users`

Nguồn: `src/models/user.py`

### Field và ý định

- `id`
  - khóa chính UUID của user.
  - dùng để join toàn bộ session, mastery, learning path, progress.

- `email`
  - định danh login duy nhất của user.
  - vừa là credential identifier, vừa là business key ở mức account.

- `full_name`
  - tên hiển thị của user trong app.

- `hashed_password`
  - mật khẩu đã hash.
  - chỉ phục vụ auth, không liên quan trực tiếp learning logic.

- `available_hours_per_week`
  - số giờ user tự khai có thể học mỗi tuần.
  - đầu vào cho planner/timeline để chia workload.

- `target_deadline`
  - thời điểm user muốn hoàn thành.
  - dùng để planner nén/giãn lộ trình.

- `preferred_method`
  - ưu tiên học bằng `reading` hay `video`.
  - dùng để cá nhân hóa entry mode/content presentation.

- `is_onboarded`
  - cờ cho biết user đã đi hết onboarding chưa.
  - gate logic cho assessment path / recommendation path ban đầu.

- `created_at`
  - thời điểm tạo account.
  - phục vụ audit và cohort tracking.

### Nhận xét

- Bảng này **chưa có** field kiểu `target_course_ids` hoặc `active_curriculum_scope`.
- Nghĩa là “user chỉ thích CS231n” hiện được suy ra từ hành vi và learning path, chưa phải preference first-class.

## A2. `modules`

Nguồn: `src/models/content.py`

### Field và ý định

- `id`
  - UUID primary key của module.

- `name`
  - tên module cấp cao, ví dụ một khối kiến thức lớn.

- `description`
  - mô tả ngắn của module.

- `order_index`
  - thứ tự hiển thị/học của module.

- `prerequisite_module_ids`
  - mảng JSON các module cần trước.
  - dùng để topo-sort lộ trình ở mức module.

### Nhận xét

- Đây là content hierarchy kiểu cũ/trung gian.
- Với canonical pipeline mới, module không còn là nguồn dữ liệu mạnh nhất; `course -> section -> learning_unit` quan trọng hơn.

## A3. `topics`

Nguồn: `src/models/content.py`

### Field và ý định

- `id`
  - UUID primary key của topic.

- `module_id`
  - FK sang module cha.
  - định vị topic trong curriculum cũ.

- `name`
  - tên topic.

- `description`
  - giải thích topic này nói về gì.

- `order_index`
  - thứ tự topic trong module.

- `prerequisite_topic_ids`
  - mảng JSON các topic phải nắm trước.
  - backbone cho planner/recommendation engine kiểu cũ.

- `estimated_hours_beginner`
  - giờ học nếu user yếu/chưa biết.

- `estimated_hours_intermediate`
  - giờ học nếu user đã có nền vừa phải.

- `estimated_hours_review`
  - giờ học nếu chỉ cần ôn nhanh.

- `content_markdown`
  - nội dung text của topic nếu app render trực tiếp.

- `video_url`
  - link video chính của topic nếu có.

### Nhận xét

- Topic hiện vẫn là grain chính cho `Session`, `MasteryScore`, `LearningPath`.
- Đây là lý do runtime hiện hỗ trợ learner/planner baseline, nhưng chưa full-wire với canonical `unit_kp_map` / `item_kp_map`.

## A4. `knowledge_components`

Nguồn: `src/models/content.py`

### Field và ý định

- `id`
  - UUID primary key của KC.

- `topic_id`
  - topic cha của KC.
  - cho biết KC này thuộc phạm vi topic nào.

- `name`
  - tên KC.

- `description`
  - mô tả ngắn KC là gì.

### Nhận xét

- Runtime ORM có bảng KC nhưng hiện chưa được dùng trọn vẹn theo canonical global KP graph mới.
- `MasteryScore.kc_id` có thể lưu theo KC, nhưng phần lớn flow hiện tại vẫn chủ yếu ở topic grain.

## A5. `questions`

Nguồn: `src/models/content.py`

### Field và ý định

- `id`
  - UUID PK nội bộ.

- `item_id`
  - business key dễ đọc của câu hỏi.
  - dùng để track version và external references.

- `version`
  - version của item.
  - phục vụ future editing / retirement / recalibration.

- `status`
  - vòng đời item: `draft`, `active`, `calibrated`, `retired`.
  - giúp runtime biết item đã sẵn sàng serve chưa.

- `topic_id`
  - topic mà item đang gắn vào trong schema runtime cũ.

- `module_id`
  - module chứa topic đó.

- `bloom_level`
  - mức Bloom mà item đang đo.
  - quan trọng cho pedagogy, assessor, selection diversity.

- `difficulty_bucket`
  - bucket độ khó thô `easy|medium|hard`.
  - dùng trước khi có IRT thật.

- `stem_text`
  - nội dung câu hỏi.

- `stem_media`
  - metadata media nếu stem cần ảnh/asset.

- `option_a` / `option_b` / `option_c` / `option_d`
  - bốn lựa chọn của MCQ.

- `correct_answer`
  - đáp án đúng.

- `distractor_*_rationale`
  - giải thích vì sao distractor đó sai hoặc gắn misconception gì.

- `misconception_*_id`
  - ID misconception ứng với mỗi distractor.
  - hỗ trợ detection misconception và remediate path.

- `explanation_text`
  - giải thích cho đáp án đúng.

- `time_expected_seconds`
  - thời gian kỳ vọng để làm item.
  - có thể dùng cho UI timing hoặc anomaly checks.

- `usage_context`
  - item được dùng cho `assessment`, `quiz`, `module_test` nào.

- `kc_ids`
  - mảng KC mà item chạm vào theo schema cũ.
  - đây là họ hàng gần nhất của Q-matrix runtime cũ.

- `irt_difficulty`
  - difficulty ước lượng nếu có calibration.

- `irt_discrimination`
  - discrimination ước lượng nếu có calibration.

- `irt_guessing`
  - guessing ước lượng nếu có calibration.

- `total_responses`
  - số lượt response đã thu về item này.
  - dùng để đánh giá độ tin cậy của calibration.

### Nhận xét

- Runtime `questions` table hiện khá giàu, nhưng chưa phản ánh trọn vẹn canonical P4 layer mới.
- Canonical P4 tách riêng `question_bank`, `item_calibration`, `item_phase_map`, `item_kp_map`, trong khi ORM cũ đang gộp khá nhiều thứ vào cùng bảng `questions`.

## A6. `courses`

Nguồn: `src/models/course.py`

### Field và ý định

- `id`
  - UUID PK của course.

- `slug`
  - business key ổn định của course.
  - dùng trong URL, references, import mapping.

- `title`
  - tên hiển thị của course.

- `short_description`
  - mô tả ngắn cho listing / overview card.

- `status`
  - mức hoàn thiện metadata/course readiness.

- `visibility`
  - public hay hidden.

- `cover_image_url`
  - ảnh cover cho course.

- `hero_badge`
  - badge/UI label nổi bật của course.

- `primary_subject`
  - subject chính của course.

- `sort_order`
  - thứ tự render trong catalog.

### Nhận xét

- Đây là lõi cho course-first product direction.

## A7. `course_overviews`

Nguồn: `src/models/course.py`

### Field và ý định

- `course_id`
  - FK 1-1 sang course.

- `headline`
  - tiêu đề marketing ngắn.

- `subheadline`
  - phụ đề.

- `summary_markdown`
  - mô tả dài hơn của course.

- `learning_outcomes`
  - list outcome người học sẽ đạt được.

- `target_audience`
  - course dành cho ai.

- `prerequisites_summary`
  - cần biết gì trước khi học.

- `estimated_duration_text`
  - mô tả thời lượng ở dạng human-readable.

- `structure_snapshot`
  - JSON snapshot cấu trúc course cho UI nhanh.

- `cta_label`
  - label nút call-to-action.

## A8. `course_sections`

Nguồn: `src/models/course.py`

### Field và ý định

- `course_id`
  - course cha.

- `parent_section_id`
  - cho phép nesting section.

- `title`
  - tiêu đề section.

- `kind`
  - loại section: `module`, `unit`, `lesson_group`, `lecture_group`.

- `sort_order`
  - thứ tự section trong course.

- `is_entry_section`
  - đánh dấu section entry/landing quan trọng.

### Nhận xét

- Đây là layer tổ chức UI/narrative cho course.
- `learning_units` sẽ nằm bên dưới `course_sections`.

## A9. `learning_units`

Nguồn: `src/models/course.py`

### Field và ý định

- `course_id`
  - course mà unit thuộc về.

- `section_id`
  - section cha.

- `slug`
  - business key của unit trong course.

- `title`
  - tiêu đề unit.

- `unit_type`
  - `lesson`, `lecture`, `reading`, `practice`.
  - dùng để planner/UI biết bản chất unit.

- `status`
  - unit đã sẵn sàng hay metadata còn thiếu.

- `sort_order`
  - thứ tự unit trong section.

- `content_source_type`
  - cho biết nguồn content là video/text/hybrid source kiểu gì.

- `content_body`
  - text content trực tiếp nếu unit text-based.

- `estimated_minutes`
  - thời lượng học dự kiến.

- `entry_mode`
  - `text`, `video`, `hybrid`.
  - quan trọng cho UX routing.

### Nhận xét

- Đây là bảng runtime gần nhất với canonical `units.jsonl`.
- Tuy nhiên canonical `units.jsonl` đang giàu provenance hơn runtime ORM hiện tại, ví dụ có `content_ref`, `key_points`, `difficulty_source`, `transcript_path`.

## A10. `course_assets`

Nguồn: `src/models/course.py`

### Field và ý định

- `course_id`
  - asset thuộc course nào.

- `learning_unit_id`
  - asset gắn trực tiếp unit nào nếu có.

- `asset_type`
  - `video`, `transcript`, `slides`, `thumbnail`, `supplement`.

- `storage_key`
  - key trong object storage.

- `delivery_url`
  - URL dùng để serve asset.

- `availability_status`
  - `available`, `processing`, `missing`.
  - giúp UI và ingest biết asset đã sẵn sàng chưa.

- `metadata_json`
  - JSON phụ cho asset metadata.

## A11. `learner_assessment_profiles`

Nguồn: `src/models/course.py`

### Field và ý định

- `user_id`
  - mỗi user có tối đa một assessment profile.

- `is_onboarded`
  - user đã đi qua assessment/onboarding chưa.

- `skill_test_completed_at`
  - thời điểm hoàn thành skill test đầu vào.

- `assessment_session_id`
  - session assessment gốc làm căn cứ recommendation.

- `recommendation_ready`
  - cờ cho biết đã đủ dữ liệu để sinh recommendation chưa.

### Nhận xét

- Bảng này hỗ trợ pre-learning flow.
- Rất hữu ích cho demo placement/skip.

## A12. `course_recommendations`

Nguồn: `src/models/course.py`

### Field và ý định

- `user_id`
  - user nhận recommendation.

- `course_id`
  - course được recommend.

- `rank`
  - thứ hạng của recommendation.

- `reason_summary`
  - lý do recommend ở dạng text ngắn.

- `generated_at`
  - timestamp sinh recommendation.

### Nhận xét

- Đây là recommendation ở level course, không phải learning path chi tiết trong course.

## A13. `learning_progress_records`

Nguồn: `src/models/course.py`

### Field và ý định

- `user_id`
  - user đang học.

- `course_id`
  - course mà progress record này thuộc về.

- `learning_unit_id`
  - unit đang track progress.

- `status`
  - `not_started`, `in_progress`, `completed`, `blocked`.
  - biểu diễn trạng thái tiến độ thực tế ở level unit.

- `last_position_seconds`
  - vị trí dở dang trong video/nội dung có timeline.
  - cực quan trọng cho case “quay lại học tiếp”.

- `last_opened_at`
  - lần gần nhất user chạm vào unit.
  - dùng để detect stale units / resume suggestions.

- `completed_at`
  - nếu xong thì ghi thời điểm hoàn thành.

### Nhận xét

- Đây là bảng quan trọng nhất cho case “user học nửa chừng rồi quay lại”.
- Tuy nhiên `skip` không được encode ở đây; `skip` hiện encode tốt hơn ở `learning_paths`.

## A14. `tutor_context_bindings`

Nguồn: `src/models/course.py`

### Field và ý định

- `learning_unit_id`
  - unit mà context binding áp vào.

- `context_type`
  - loại context được bind.

- `source_ref`
  - tham chiếu tới nguồn context.

- `context_window_rule`
  - rule để cắt context window.

- `is_active`
  - context binding còn hiệu lực hay không.

### Nhận xét

- Bảng này phục vụ tutor/context orchestration hơn là learner state.

## A15. `legacy_lecture_mappings`

Nguồn: `src/models/course.py`

### Field và ý định

- `legacy_lecture_id`
  - ID lecture cũ trong stack legacy.

- `learning_unit_id`
  - unit mới mà lecture cũ map sang.

- `course_id`
  - course chứa mapping đó.

- `migration_state`
  - trạng thái migrate: `pending`, `mapped`, `deprecated`.

### Nhận xét

- Đây là cầu nối giữa schema cũ và course-first schema mới.

## A16. `sessions`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - user sở hữu session.

- `session_type`
  - `assessment`, `quiz`, `module_test`, `practice`.
  - giúp phân biệt ý nghĩa pedagogy của session.

- `topic_id`
  - topic mà session đang tập trung vào.

- `module_id`
  - module tương ứng của session nếu có.

- `started_at`
  - bắt đầu session lúc nào.

- `completed_at`
  - hoàn tất session lúc nào.

- `total_questions`
  - số câu trong session.

- `correct_count`
  - số câu đúng.

- `score_percent`
  - điểm tổng hợp của session.

### Nhận xét

- Session lưu được “một buổi học/assessment” rất tốt.
- Nhưng nó vẫn neo vào `topic/module` cũ, chưa phải `learning_unit / kp` của canonical layer.

## A17. `interactions`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - user trả lời.

- `session_id`
  - thuộc session nào.

- `question_id`
  - item nào được trả lời.

- `sequence_position`
  - thứ tự trong session hiện tại.

- `global_sequence_position`
  - thứ tự tổng thể của interaction trong lịch sử user.
  - hữu ích cho audit và recency logic.

- `selected_answer`
  - user đã chọn đáp án nào.
  - có thể `null` nếu skipped/no-answer.

- `is_correct`
  - đúng hay sai.

- `response_time_ms`
  - thời gian phản hồi.

- `changed_answer`
  - có đổi đáp án sau lần chọn đầu không.

- `hint_used`
  - có dùng hint không.

- `explanation_viewed`
  - có mở explanation không.

- `timestamp`
  - thời điểm interaction xảy ra.

### Nhận xét

- Đây là raw event log cốt lõi cho mastery update, misconception detection, IRT sau này.

## A18. `mastery_scores`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - user sở hữu mastery estimate.

- `topic_id`
  - topic đang được đo mastery.

- `kc_id`
  - KC cụ thể nếu muốn đi xuống hạt mịn hơn.
  - `NULL` nghĩa là đang lưu ở level topic.

- `mastery_probability`
  - estimate xác suất đã nắm được.

- `mastery_level`
  - bucket `not_started`, `novice`, `developing`, `proficient`, `mastered`.

- `bloom_max_achieved`
  - mức Bloom cao nhất user đã thể hiện được.

- `evidence_count`
  - số evidence/interactions đã dùng để cập nhật mastery này.

- `recent_trend`
  - `improving`, `stable`, `declining`.
  - đặc biệt hữu ích cho user quay lại sau thời gian dài.

- `last_practiced`
  - lần gần nhất topic/KC này được thực hành.

- `updated_at`
  - lần gần nhất record được cập nhật.

### Nhận xét

- Bảng này đã đủ cho demo learner state.
- Chưa full canonical-KP-based, nhưng đủ cho baseline.

## A19. `mastery_history`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - ai bị thay đổi mastery.

- `topic_id`
  - topic bị ảnh hưởng.

- `kc_id`
  - KC bị ảnh hưởng nếu có.

- `old_mastery_probability`
  - mastery trước update.

- `new_mastery_probability`
  - mastery sau update.

- `old_mastery_level`
  - level trước.

- `new_mastery_level`
  - level sau.

- `evidence_count`
  - số evidence tích lũy tại thời điểm thay đổi.

- `trigger_session_id`
  - session nào gây ra update này.

- `changed_at`
  - thời điểm thay đổi.

### Nhận xét

- Đây là audit trail rất hữu ích để explain mastery drift.

## A20. `learning_paths`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - ai sở hữu path item này.

- `topic_id`
  - topic mà planner đang nhắm tới.

- `action`
  - planner muốn user làm gì:
    - `skip`
    - `quick_review`
    - `standard_learn`
    - `deep_practice`
    - `remediate`

- `estimated_hours`
  - effort ước tính cho action đó.
  - `skip` thì thường là `0.0`.

- `order_index`
  - vị trí của bước trong plan.

- `week_number`
  - tuần được đề xuất.
  - item bị skip có thể không có week cụ thể.

- `status`
  - `pending`, `in_progress`, `completed`, `skipped`.

### Nhận xét

- Đây là bảng encode `skip` rõ nhất trong runtime hiện tại.
- Nếu user được phép skip một topic, thường:
  - `action = skip`
  - `estimated_hours = 0`
  - `status = skipped`

## A21. `learner_mastery_kp`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - user mà mastery row này thuộc về.

- `kp_id`
  - canonical KP/business key đang được theo dõi.
  - đây là điểm khác biệt lớn nhất so với `mastery_scores.topic_id`.

- `theta_mu`
  - latent ability mean ở grain `user × kp`.
  - chưa được service/runtime cũ sử dụng, nhưng là landing zone đúng cho planner/assessor đời sau.

- `theta_sigma`
  - uncertainty của latent ability.
  - rất quan trọng nếu sau này cần lower-confidence-bound thay vì dùng một số point estimate duy nhất.

- `mastery_mean_cached`
  - xác suất mastery đã cache sẵn trong `[0,1]`.
  - dùng để UI/planner đọc nhanh mà không phải tính lại từ `theta_mu/theta_sigma` mỗi lần.

- `n_items_observed`
  - số item evidence đã dùng để cập nhật row này.
  - giúp phân biệt mastery mạnh/yếu về mặt bằng chứng.

- `updated_by`
  - cơ chế nào đã cập nhật row:
    - backfill
    - assessor
    - synthetic bootstrap
    - planner side-effect
  - hiện mới là chỗ để provenance, chưa có convention cứng.

### Nhận xét

- Đây là bảng mới quan trọng nhất để bridge từ runtime cũ sang spec learner layer mới.
- Nó chưa thay thế `mastery_scores`, nhưng cho phép cả hai cùng tồn tại trong giai đoạn chuyển tiếp.

## A22. `goal_preferences`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - mỗi user có tối đa một goal preference row.

- `goal_weights_json`
  - trọng số mục tiêu/hứng thú của user.
  - dùng làm source-of-truth cho planner thay vì suy từ hành vi hoặc từ `users`.

- `selected_course_ids`
  - tập course user muốn theo.
  - đây là mảnh còn thiếu trước đó để encode rõ “chỉ học CS231n”.

- `goal_embedding`
  - reserve cho vector hóa mục tiêu học tập.
  - hiện là JSON để tránh khóa cứng representation quá sớm.

- `goal_embedding_version`
  - version của embedding/generator đã dùng.

- `derived_from_course_set_hash`
  - hash của selected course set.
  - hữu ích để detect khi mục tiêu đã đổi và embedding cũ không còn hợp lệ.

- `notes`
  - chỗ để lưu ghi chú tự do hoặc planner-side explanation phụ.

### Nhận xét

- Bảng này chính thức lấp gap “users chưa có target_course_ids”.
- Đây vẫn mới là persistence shell; chưa có onboarding/service wiring.

## A23. `waived_units`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - user được waive.

- `learning_unit_id`
  - unit bị waive.

- `evidence_items`
  - list item IDs đã làm căn cứ waive.
  - cho phép audit quyết định skip thay vì chỉ nhìn `learning_paths.action = skip`.

- `mastery_lcb_at_waive`
  - lower-confidence-bound tại thời điểm waive.
  - tách rõ “skip vì đủ chắc” với “skip vì rule heuristic”.

- `skip_quiz_score`
  - điểm của bài skip-verification nếu có.

### Nhận xét

- Đây là lớp audit đúng nghĩa cho skip/waive.
- Nó không thay `learning_paths`, mà bổ sung evidence cho quyết định skip.

## A24. `plan_history`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - user sở hữu plan.

- `parent_plan_id`
  - plan cha nếu đây là replan.
  - cho phép lần theo cây evolution của learning plan.

- `trigger`
  - nguyên nhân sinh plan:
    - onboarding
    - replan
    - post-quiz
    - manual refresh

- `recommended_path_json`
  - snapshot path được đề xuất ở thời điểm đó.

- `goal_snapshot_json`
  - ảnh chụp goal profile dùng khi sinh plan.

- `weights_used_json`
  - các trọng số scoring dùng ở run đó.

### Nhận xét

- Đây là planner audit shell, chưa phải planner engine.
- Nó giúp phase sau có nơi lưu plan versioning thay vì mất dấu mỗi lần regenerate.

## A25. `rationale_log`

Nguồn: `src/models/learning.py`

### Field và ý định

- `plan_history_id`
  - rationale này thuộc về planner run nào.

- `learning_unit_id`
  - unit mà rationale đang nói tới.

- `rank`
  - thứ hạng của unit trong plan.

- `reason_code`
  - mã ngắn cho lý do chọn/lọc.

- `term_breakdown_json`
  - breakdown các term scoring ở dạng JSON.

- `rationale_text`
  - giải thích human-readable.

### Nhận xét

- Đây là shell cho explainability của planner.
- Rất hợp với UI/debugging, dù hiện chưa có service ghi dữ liệu vào.

## A26. `planner_session_state`

Nguồn: `src/models/learning.py`

### Field và ý định

- `user_id`
  - user đang có planner session state.

- `session_id`
  - business/session token của planner session.

- `last_plan_history_id`
  - plan gần nhất gắn với state này.

- `bridge_chain_depth`
  - số bridge liên tiếp đang ở trong chain hiện tại.

- `consecutive_bridge_count`
  - counter để enforce cap logic nếu planner cần giới hạn bridge liên tục.

- `state_json`
  - state phụ mà planner cần giữ giữa các lần gọi.

### Nhận xét

- Bảng này chưa có logic runtime đi kèm, nhưng đã tạo được landing zone cho session-aware planner.

## B. Legacy Adapter Schema

Nguồn: `src/models/store.py`

Các bảng này là cầu nối cho stack tutor/lecture cũ.

## B1. `lectures`

- `id`
  - string ID của lecture cũ.

- `title`
  - tên lecture.

- `description`
  - mô tả lecture.

- `video_url`
  - link video.

- `duration`
  - thời lượng video.

- `created_at`
  - timestamp tạo record.

## B2. `chapters`

- `id`
  - PK tăng dần.

- `lecture_id`
  - lecture cha.

- `title`
  - tên chapter.

- `summary`
  - tóm tắt chapter.

- `start_time`
  - mốc bắt đầu chapter.

- `end_time`
  - mốc kết thúc chapter.

## B3. `transcript_lines`

- `id`
  - PK tăng dần.

- `lecture_id`
  - lecture cha.

- `start_time`
  - mốc bắt đầu line transcript.

- `end_time`
  - mốc kết thúc line transcript.

- `content`
  - nội dung transcript line.

## B4. `qa_history`

- `id`
  - PK tăng dần.

- `lecture_id`
  - lecture nào user đang hỏi.

- `question`
  - câu user hỏi.

- `answer`
  - câu trả lời.

- `thoughts`
  - reasoning/thought trace cũ nếu lưu.

- `current_timestamp`
  - thời điểm đang đứng trong video lúc hỏi.

- `context_binding_id`
  - binding context nào đã dùng.

- `image_base64`
  - ảnh đính kèm nếu có.

- `rating`
  - user feedback cho câu trả lời.

- `created_at`
  - thời điểm hỏi đáp.

## B5. `learning_progress`

- `id`
  - PK tăng dần.

- `session_id`
  - session string của stack cũ.

- `lecture_id`
  - lecture đang track.

- `last_timestamp`
  - vị trí dừng gần nhất trong video.

- `checkpoint_state`
  - trạng thái thô kiểu `unwatched`, `watched`, `quiz_completed`.

- `updated_at`
  - timestamp cập nhật.

### Nhận xét chung về layer legacy

- Layer này vẫn hữu ích cho tương thích ngược.
- Nhưng **không nên** là source of truth cho course-first product mới.

## C. Canonical Artifact Schema

Nguồn:

- `data/final_artifacts/cs224n_cs231n_v1/canonical/*.jsonl`
- exporter: `src/scripts/pipeline/export_canonical_artifacts.py`

Đây là lớp dữ liệu mà nhánh này vừa chuẩn hóa xong.

## C1. `courses.jsonl`

### Field và ý định

- `course_id`
  - business ID ổn định của course trong canonical layer.

- `course_name`
  - tên course.

- `source`
  - nguồn/syllabus origin của course.

- `note`
  - ghi chú dữ liệu nhập vào.

- `reference_slides_no_video`
  - danh sách slide reference không có video đi kèm.

- `lecture_count`
  - số lecture trong syllabus.

- `track_tags`
  - reserve cho track classification sau này.

- `summary_embedding`
  - reserve cho embedding của course summary.

- `source_file`
  - file nguồn dùng để build record này.

## C2. `concepts_kp.jsonl`

### Field và ý định

- `kp_id`
  - global concept/KP ID.

- `name`
  - tên concept.

- `description`
  - mô tả semantically concept này là gì.

- `track_tags`
  - tag theo track học.

- `domain_tags`
  - tag theo domain/chủ đề.

- `career_path_tags`
  - tag theo career path.

- `difficulty_level`
  - difficulty gốc trong P2.

- `difficulty_source`
  - difficulty lấy từ đâu.

- `difficulty_confidence`
  - mức tự tin của difficulty estimate.

- `importance_level`
  - importance theo tier.

- `structural_role`
  - vai trò như `gateway`, `capstone`, ...

- `importance_confidence`
  - self-confidence cho importance labeling.

- `importance_rationale`
  - giải thích tại sao concept quan trọng như vậy.

- `importance_scope`
  - phạm vi áp dụng importance đó.

- `importance_source`
  - provenance của importance labeling.

- `source_course_ids`
  - concept này xuất phát từ course nào.

- `importance`
  - điểm float rule-based suy ra từ `importance_level x confidence`.

- `description_embedding`
  - reserve cho embedding.

- `source_file`
  - file P2 nguồn.

## C3. `units.jsonl`

### Field và ý định

- `unit_id`
  - business ID của unit/segment.

- `course_id`
  - course chứa unit.

- `lecture_id`
  - lecture chứa unit.

- `lecture_order`
  - thứ tự lecture trong course.

- `lecture_title`
  - tên lecture.

- `unit_name`
  - tên segment/unit.

- `description`
  - mô tả unit.

- `summary`
  - summary ngắn, thường để hiển thị hoặc ingest downstream.

- `key_points`
  - list key points có timestamp.
  - cực quan trọng cho provenance và tutor grounding.

- `content_ref`
  - tham chiếu nội dung gốc, thường gồm start/end time và video/source context.

- `difficulty`
  - độ khó mức unit.

- `difficulty_source`
  - difficulty lấy từ đâu.

- `difficulty_confidence`
  - tự tin vào difficulty đó.

- `duration_min`
  - độ dài ước tính của unit.

- `ordering_index`
  - thứ tự unit trong lecture.

- `section_flags`
  - cờ phân loại unit, ví dụ recap/admin/demo/theory.

- `video_clip_ref`
  - reserve cho clip cắt riêng nếu cần.

- `topic_embedding`
  - reserve cho embedding unit/topic text.

- `source_file`
  - file P1 sanitized gốc.

- `transcript_path`
  - transcript file đã dùng để validate provenance.

## C4. `unit_kp_map.jsonl`

### Field và ý định

- `unit_id`
  - unit được map.

- `kp_id`
  - concept xuất hiện trong unit.

- `planner_role`
  - role của concept trong planner logic.

- `instruction_role`
  - role của concept trong giảng dạy.

- `coverage_level`
  - mức độ được dạy: `dominant`, `substantial`, `partial`, `mention`.

- `coverage_confidence`
  - confidence cho coverage labeling.

- `coverage_rationale`
  - giải thích vì sao gán coverage đó.

- `coverage_weight`
  - điểm float rule-based từ `coverage_level x coverage_confidence`.

- `source_local_kp_ids`
  - local KP IDs đã merge về global `kp_id` này.

- `source_file`
  - file P2 nguồn.

## C5. `question_bank.jsonl`

### Field và ý định

- `course_id`
  - course chứa item.

- `lecture_id`
  - lecture chứa item.

- `unit_id`
  - unit nguồn của item.

- `source_file`
  - file P4 nguồn.

- `item_id`
  - business ID của item.

- `item_type`
  - loại item, ví dụ `concept_mcq`, `code_mcq`.

- `knowledge_scope`
  - item đo kiến thức transferable hay course-specific.

- `render_mode`
  - cách render item trong UI.

- `question`
  - stem text.

- `choices`
  - danh sách lựa chọn.

- `answer_index`
  - đáp án đúng.

- `explanation`
  - giải thích cho đáp án.

- `primary_kp_id`
  - global KP chính mà item đo.

- `source_ref`
  - provenance chi tiết:
    - unit nguồn
    - timestamp/evidence span
    - transcript grounding
  - đây là field quan trọng nhất để audit item có grounded thật không.

- `difficulty`
  - độ khó ở mức item.

- `question_intent`
  - `conceptual`, `procedural`, `diagnostic`, `application`.

- `qa_gate_passed`
  - item đã qua gate chất lượng nội bộ chưa.

- `review_status`
  - trạng thái review hiện tại.

- `repair_history`
  - lịch sử self-repair nếu prompt đã sửa item qua nhiều vòng.

- `provenance`
  - item này đến từ pass nào của pipeline.

- `concept_alignment_cosine`
  - reserve cho semantic alignment score sau embedding batch.

- `distractor_cosine_upper`
  - reserve cho quality/distance check của distractor.

- `distractor_cosine_lower`
  - reserve cho lower-bound distractor quality check.

- `assessment_purpose`
  - item sinh ra nhằm reinforcement, placement, v.v.

- `grounding_mode`
  - transcript-only, multimodal, ...

- `grounding_confidence`
  - confidence vào grounding mode trên.

## C6. `item_calibration.jsonl`

### Field và ý định

- `course_id`, `lecture_id`, `unit_id`, `source_file`
  - provenance/context của item calibration row.

- `item_id`
  - item đang được chấm prior/calibration.

- `calibration_method`
  - `prior_only`, `synthetic_bootstrap`, ... trong tương lai.

- `is_calibrated`
  - đã có calibration thật hay chưa.

- `difficulty_prior`
  - prior độ khó trước khi có IRT thật.

- `discrimination_prior`
  - prior độ phân biệt.

- `guessing_prior`
  - prior khả năng đoán mò.

- `difficulty_b`
  - IRT `b` nếu có fit thật.

- `discrimination_a`
  - IRT `a` nếu có fit thật.

- `guessing_c`
  - IRT `c` nếu có fit thật.

- `irt_calibration_n`
  - số response đã dùng để fit.

- `standard_error_b`
  - độ bất định của `b`.

- `calibration_confidence`
  - confidence tổng quát cho calibration row.

- `calibration_rationale`
  - giải thích tại sao cho prior như vậy.

## C7. `item_phase_map.jsonl`

### Field và ý định

- `course_id`, `lecture_id`, `unit_id`, `source_file`
  - provenance row.

- `item_id`
  - item được map phase.

- `phase`
  - phase nào item phù hợp:
    - `placement`
    - `mini_quiz`
    - `skip_verification`
    - `bridge_check`
    - `final_quiz`
    - `transfer`
    - `review`

- `phase_multiplier`
  - hệ số khuếch đại/giảm trọng số evidence theo phase.

- `suitability_score`
  - độ phù hợp của item với phase đó.

- `selection_priority`
  - reserve cho thứ tự ưu tiên chọn item trong cùng phase.

- `phase_rationale`
  - giải thích vì sao item phù hợp phase đó.

## C8. `item_kp_map.jsonl`

### Field và ý định

- `course_id`, `lecture_id`, `unit_id`, `source_file`
  - provenance row.

- `item_id`
  - item nào đang map.

- `kp_id`
  - global KP mà item đo.

- `kp_role`
  - `primary`, `secondary`, hoặc `support`.

- `weight`
  - trọng số evidence rule-based hiện tại:
    - `primary = 0.7`
    - `secondary = 0.3`
    - `support = 0.0`

- `mapping_confidence`
  - confidence của mapping.
  - hiện còn yếu/nullable, đây là chỗ Q-matrix chưa psychometric-grade.

### Nhận xét

- Đây chính là Q-matrix baseline của pipeline mới.
- Nó dùng được cho demo/baseline mastery update.
- Chưa nên coi là ground truth calibrated cho CDM/IRT tinh vi.

## C9. `prerequisite_edges.jsonl`

### Field và ý định

- `source_kp_id`
  - concept được xem là prerequisite.

- `target_kp_id`
  - concept downstream phụ thuộc vào source.

- `edge_scope`
  - intra-course hay inter-course.

- `provenance`
  - edge đến từ pass nào:
    - llm
    - rule-based
    - audit
    - v.v.

- `confidence`
  - self-confidence của edge verdict.

- `review_status`
  - tình trạng review của edge.

- `rationale`
  - giải thích tại sao giữ edge.

- `temporal_signal`
  - tín hiệu về thứ tự xuất hiện theo lecture/course.

- `source_first_seen`
  - concept nguồn xuất hiện lần đầu ở đâu.

- `target_first_seen`
  - concept đích xuất hiện lần đầu ở đâu.

- `p5_keep_confidence`
  - confidence từ adjudication P5.

- `p5_expected_directionality`
  - chiều kỳ vọng từ P5.

- `p5_trace`
  - trace adjudication phục vụ audit.

- `edge_strength`
  - reserve/nullable cho score ML hoặc post-processing sau này.

- `bidirectional_score`
  - reserve/nullable cho direction ambiguity score.

- `source_file`
  - file nguồn để truy ra audit trail.

## C10. `pruned_edges.jsonl`

### Field và ý định

- giống `prerequisite_edges.jsonl`, cộng thêm:

- `prune_reason`
  - lý do edge bị loại:
    - transitive redundant
    - GPT-5.4 prune
    - v.v.

### Nhận xét

- Tách riêng file này giúp audit graph evolution tốt hơn nhiều so với xóa im lặng.

## C11. `manifest.json`

### Vai trò

- snapshot toàn cục của canonical bundle.
- lưu:
  - source files
  - pipeline versions
  - counts
  - sha256 từng file

### Ý định

- reproducibility
- review/diff dễ hơn
- biết canonical bundle có bị drift khi rerun không

## C12. `validation_report.json`

### Vai trò

- ghi kết quả validator sau khi export.

### Ý định

- tách rõ:
  - `hard_checks`
  - `deferred_checks`
- hiện hard fail = `0`
- deferred checks chủ yếu là:
  - embedding-dependent checks
  - ML-dependent edge checks

## Đánh giá schema hiện tại

## 1. Điểm đã đủ tốt

- Runtime schema đủ cho:
  - user học nửa chừng rồi quay lại
  - session/interactions history
  - mastery snapshot + mastery audit
  - planner baseline với `skip`, `quick_review`, `deep_practice`
- runtime giờ cũng đã có **stub foundation** cho learner/planner đời mới:
  - `learner_mastery_kp`
  - `goal_preferences`
  - `waived_units`
  - `plan_history`
  - `rationale_log`
  - `planner_session_state`
- Canonical artifact layer đủ sạch để làm bước ingest PostgreSQL sau này.
- P4/P5/P2 giờ đã có contract rõ hơn nhiều so với trạng thái trước của nhánh.

## 2. Điểm còn lệch giữa runtime và canonical

- Runtime mastery/path vẫn nghiêng về `topic/module`, chưa full canonical `kp/unit`.
- Runtime `questions` còn gộp nhiều concern mà canonical đã tách riêng.
- Stub tables đã được wire một phần, sau feature flag:
  - onboarding ghi compatibility snapshot vào `goal_preferences`
  - planner legacy ghi topic-grain audit vào `plan_history` / `rationale_log` / `planner_session_state`
  - skip flow chưa ghi `waived_units`
  - assessor chưa cập nhật `learner_mastery_kp`
  - `learner_mastery_kp` và `waived_units` đang chờ bridge đúng sang canonical `kp_id` / `learning_unit_id`
- Runtime vẫn chưa có shared taxonomy end-to-end giữa:
  - `sessions.session_type`
  - canonical `item_phase_map.phase`
  - planner/session-state semantics

## 3. Ý nghĩa thực tế cho phase tiếp theo

- Nếu mục tiêu là demo:
  - schema hiện tại đủ dùng.
- Nếu mục tiêu là ingest + production hóa dần:
  - canonical artifact đã có DB materialization và importer để map vào PostgreSQL.
- Nếu mục tiêu là mastery/IRT/CDM tinh vi:
  - cần thêm wiring từ canonical `item_kp_map` / `unit_kp_map` vào runtime schema hoặc schema mới.

## Kết luận ngắn

Nhánh `rin/implement` trong giai đoạn này đã làm được một việc quan trọng:

- biến dữ liệu course/question/prerequisite từ trạng thái rải rác, lệch format, nhiều debt
- thành một canonical contract đủ sạch để ingest tiếp
- đồng thời mở thêm một lớp runtime stub để learner/planner phase sau có chỗ bám đúng grain hơn
- khóa thêm handoff contract để người nối backend/database có thể cutover mà không phải đoán source-of-truth

Runtime ORM hiện vẫn chạy theo `module/topic/question/mastery_path` cũ là chính, nhưng đã có `course-first` layer khá rõ ở `src/models/course.py`. Canonical artifact layer mới là bước đệm để nối hai thế giới đó lại với nhau trong phase tiếp theo.
