# Feature: Onboarding

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `3. Frontend architecture`, `5. Dòng dữ liệu học tập thích ứng`, `7. Onboarding -> Assessment -> Planner flow`

## 1. Mục tiêu
Onboarding thu thập mục tiêu học, kinh nghiệm nền, phạm vi course mong muốn, và mức độ assessment để khởi tạo hồ sơ học tập ban đầu. Flow này dùng để đưa người dùng từ trạng thái "vừa đăng nhập" sang trạng thái có dữ liệu cho planner, assessment, và course gating.

## 2. User/problem this solves
Người dùng mới thường không có dữ liệu mastery, nhưng hệ thống vẫn cần biết:
- họ đang học theo hướng nào;
- đã biết gì ở mức self-report;
- cần assessment sâu đến mức nào;
- có được phép vào course/learn flow nào.

Nếu không có onboarding, planner sẽ phải đoán scope, assessment sẽ khởi động không đúng phạm vi, và UI sau login sẽ không có điểm bắt đầu rõ ràng.

## 3. System scope
Backend:
- `src/routers/auth.py`
- `src/schemas/onboarding.py`
- `src/services/onboarding_service.py`
- `src/services/auth_service.py`
- `src/repositories/goal_preference_repo.py`

Frontend:
- `frontend/app/onboarding/page.tsx`
- `frontend/components/onboarding/*`
- `frontend/stores/onboardingStore.ts`
- `frontend/lib/onboarding-schema.ts`

Related runtime tables:
- `users`
- `goal_preferences`

## 4. Architecture & flow
Flow hiện tại đi theo hướng course-first product shell, nhưng vẫn cho phép prior-analysis và placement handoff:

```text
Guest/Login
  -> /onboarding
  -> user chọn goal/course/experience/self-report
  -> frontend validate payload
  -> PUT /api/users/me/onboarding
  -> auth_service + onboarding_service chuẩn hóa dữ liệu
  -> ghi snapshot vào goal_preferences
  -> cập nhật users.is_onboarded
  -> route sang /learn, /assessment, hoặc return target
```

Hệ thống còn có prior-analysis cho input tự do và placement-lite cho trường hợp user quay lại sau thời gian dài.

## 5. Key components
- `StepGoalSelection`, `StepExperienceLevel`, `StepKnownTopicsFiltered`, `StepAssessmentDepth`, `StepPriorKnowledgeInput`: gồm các bước UI chính.
- `onboardingStore`: giữ state wizard phía frontend.
- `onboardingSchema`: ràng buộc contract phía client.
- `update_onboarding` trong `auth_service`: điểm ghi chính vào `goal_preferences`.
- `onboarding_service`: xử lý prior-analysis, path profile, và tracing.

## 6. Data model / contracts
Payload onboarding đã chuyển sang contract mới:
- `known_unit_ids`
- `desired_section_ids`
- `selected_course_ids`
- `goal_ids`

Dữ liệu được ghi vào `goal_preferences` để planner đọc lại:
- `selected_course_ids`
- `goal_weights_json`
- `derived_from_course_set_hash`
- `notes` chứa metadata bổ sung như `known_unit_ids`, `desired_section_ids`

Có alias tạm thời cho field cũ để không phá client cũ, nhưng contract mới là unit/section/course-first.

## 7. Technical decisions
- Tách onboarding khỏi planner renderer: onboarding chỉ là input provider, không tự generate learning path trên client.
- Self-report không được coi là mastery thật: nó chỉ ảnh hưởng scope/pacing, không được dùng để waive unit.
- Ghi snapshot vào `goal_preferences` thay vì nhét nhiều logic vào `users`.
- Hỗ trợ tracing cho prior-analysis qua LangFuse để có thể debug các nhánh provider khác nhau.

## 8. Risks / trade-offs
- Self-report dễ bias nếu user overclaim.
- Contract chuyển tiếp từ `known_topic_ids` sang `known_unit_ids` tạo technical debt tạm thời.
- Nếu onboarding và assessment routing không đồng bộ, user có thể bị đẩy sai vào assessment hoặc learn flow.
- Onboarding đang cân bằng giữa goal-first và course-first; đây là điểm đáng viết trong report vì nó là quyết định sản phẩm ảnh hưởng trực tiếp kiến trúc dữ liệu.

## 9. Testing / validation
Backend:
- `tests/test_onboarding_endpoints.py`
- `tests/test_onboarding_goal_ids.py`

Frontend:
- `frontend/tests/unit/onboarding/*`
- `frontend/tests/e2e/course-gating.spec.ts`

Kiểm chứng chính:
- payload mới hợp lệ;
- loading/finish state không double submit;
- user được route đúng sau onboarding;
- `goal_preferences` nhận scope và notes đúng format.

## 10. Demo-worthy points
- Wizard có state rõ ràng, không chỉ là form đăng ký.
- Onboarding ghi dữ liệu trực tiếp vào runtime table mà planner/assessment thực sự sử dụng.
- Có prior-analysis và course gating thay vì chỉ lưu thông tin profile trang trí.
- Dễ đưa vào report vì nó nối được câu chuyện "từ UX input sang decision engine backend".
