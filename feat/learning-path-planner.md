# Feature: Learning Path Planner

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `3. Frontend architecture`, `5. Dòng dữ liệu học tập thích ứng`, `6. Canonical data model`, `7. Onboarding -> Assessment -> Planner flow`

## 1. Mục tiêu
Planner sinh ra lộ trình học theo unit dựa trên scope khóa học, mastery hiện tại, prerequisite graph, và progress của learner. Đây là trung tâm của adaptive learning experience.

## 2. User/problem this solves
Nếu hệ thống chỉ hiện curriculum tĩnh, mỗi learner sẽ đi cùng một đường. Planner giải quyết:
- học gì tiếp theo;
- unit nào có thể skip;
- unit nào cần quick review;
- unit nào cần deep practice;
- resume từ đâu khi user quay lại.

## 3. System scope
Backend:
- `src/routers/learning_path.py`
- `src/services/recommendation_engine.py`
- `src/services/skip_policy_service.py`
- `src/services/resume_state_service.py`

Frontend:
- `frontend/app/learning-path/page.tsx`
- `frontend/features/learning-path/*`

Tables:
- `goal_preferences`
- `learner_mastery_kp`
- `learning_progress_records`
- `waived_units`
- `plan_history`
- `rationale_log`
- `planner_session_state`
- `learning_units`
- `unit_kp_map`
- `prerequisite_edges`

## 4. Architecture & flow

```text
User hoàn tất onboarding / đã có profile
  -> POST /api/learning-path/generate
  -> recommendation_engine đọc scope, mastery, prerequisite graph, progress
  -> rank learning units
  -> classify skip / quick_review / deep_practice
  -> ghi plan_history + rationale_log + planner_session_state
  -> frontend render timeline/roadmap
  -> user học tiếp, complete quiz, cập nhật progress
```

Resume flow đọc `planner_session_state.current_unit_id/current_stage/current_progress` để đưa user quay lại đúng vị trí.

## 5. Key components
- `recommendation_engine`: planner runtime chính.
- `planner_session_state`: sticky state cho current unit, current stage, current progress.
- `rationale_log`: explainability cho vì sao planner chọn/bỏ qua một unit.
- `learning_progress_records`: source of truth cho unit status.
- frontend roadmap components: `RoadmapPlanner`, `TimelineBoard`, `LearningUnitDrawer`.

## 6. Data model / contracts
Planner đọc:
- `goal_preferences.selected_course_ids`
- `learner_mastery_kp`
- `learning_units`
- `unit_kp_map`
- `prerequisite_edges`
- `learning_progress_records`
- `waived_units`

Planner ghi:
- `plan_history.recommended_path_json`
- `rationale_log`
- `planner_session_state`

Contract public đã dùng unit-grain:
- `learning_unit_id`
- `section_title`
- `total_units`, `completed_units`, `in_progress_units`

## 7. Technical decisions
- Planner chạy ở grain `learning_unit`, không quay lại topic/module legacy.
- Gating skip dựa trên `mastery_lcb`, không dựa trên self-report.
- Staleness được xử lý on-read bằng tăng uncertainty, không mutate thẳng `learner_mastery_kp`.
- Tách planner audit (`plan_history`, `rationale_log`) khỏi progress runtime (`learning_progress_records`).

## 8. Risks / trade-offs
- Chất lượng planner phụ thuộc rất mạnh vào độ dày prerequisite graph và unit-KP mapping.
- `rationale_log` cần chất lượng dữ liệu tốt để explainability có giá trị thật.
- Khi canonical links chưa đủ parity, planner có thể xếp path phẳng hoặc thiếu context.
- Resume UX phía frontend có thể đi sau backend state model, tạo khoảng cách giữa "có data" và "có trải nghiệm".

## 9. Testing / validation
Backend:
- `tests/services/test_recommendation_engine_canonical_cutover.py`
- `tests/services/test_resume_state_service.py`
- `tests/test_phase_ab_lock.py`
- `tests/test_recommendation_phase_ab.py`

Frontend:
- `frontend/tests/unit/learning-path/*`
- `frontend/tests/routes/learning/unit.test.tsx`
- `frontend/tests/routes/dashboard/page.test.tsx`

Kiểm chứng cần có:
- planner sinh path có unit scope đúng;
- status lấy từ progress records;
- resume route phân loại theo `last_activity`;
- roadmap renderer ổn định trên profile thật.

## 10. Demo-worthy points
- Đây là feature để đưa vào report tổng vì nó cho thấy adaptive engine rõ nhất.
- Có audit, explainability, resume, và runtime gating thay vì chỉ là recommend list.
- Frontend roadmap/Timeline giúp phần này dễ minh họa trong report và demo.
