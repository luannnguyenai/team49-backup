# Feature: Assessment

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `4. Backend architecture`, `5. Dòng dữ liệu học tập thích ứng`, `6. Canonical data model`, `7. Onboarding -> Assessment -> Planner flow`

## 1. Mục tiêu
Assessment là cơ chế đánh giá kiến thức để khởi tạo hoặc cập nhật mastery của learner trên canonical content model. Nó phục vụ onboarding placement, review, placement-lite, mini quiz, và các flow replan.

## 2. User/problem this solves
Hệ thống adaptive learning cần bằng chứng thực nghiệm thay vì chỉ dựa vào self-report. Assessment giải quyết:
- xác định user đã biết gì;
- cập nhật mastery theo KP;
- mở khóa skip/review/deep practice có cơ sở;
- tạo dữ liệu cho planner và dashboard.

## 3. System scope
Backend:
- `src/routers/assessment.py`
- `src/services/assessment_service.py`
- `src/services/canonical_question_selector.py`
- `src/services/canonical_mastery_service.py`
- `src/repositories/canonical_question_repo.py`

Frontend:
- `frontend/app/assessment/page.tsx`
- `frontend/app/assessment/results/page.tsx`
- `frontend/lib/canonical-assessment-session.ts`

Tables:
- `question_bank`
- `item_phase_map`
- `item_kp_map`
- `item_calibration`
- `interactions`
- `learner_mastery_kp`

## 4. Architecture & flow

```text
Frontend assessment page
  -> POST /api/assessment/start
  -> chọn questions theo unit + phase
  -> user submit answers
  -> POST /api/assessment/{session_id}/submit
  -> ghi interactions.canonical_item_id
  -> canonical_mastery_service update learner_mastery_kp
  -> GET /api/assessment/{session_id}/results
  -> trả learning_unit_results + AI summary nếu có
```

Flow này được reuse cho onboarding placement, placement-lite, review, module test và replan assessment.

## 5. Key components
- `canonical_question_selector`: lấy item theo phase và scope.
- `assessment_service`: orchestration start/submit/result.
- `canonical_mastery_service`: update posterior theo item response.
- `item_phase_map`: cho biết item hợp với `placement`, `mini_quiz`, `review`, `skip_verification`, ...
- `item_kp_map`: Q-matrix baseline để quy đổi answer event thành evidence trên KP.

## 6. Data model / contracts
Assessment runtime không đọc bảng `questions` legacy nữa mà đọc canonical tables:
- item content từ `question_bank`
- phase suitability từ `item_phase_map`
- KP mapping từ `item_kp_map`
- calibration prior từ `item_calibration`

Kết quả submit ghi:
- `interactions.canonical_item_id`
- cập nhật `learner_mastery_kp.theta_mu`
- cập nhật `learner_mastery_kp.theta_sigma`
- recompute `mastery_mean_cached`

Public contract đã dùng `learning_unit_id` thay vì topic/module cũ.

## 7. Technical decisions
- Chọn item theo join `question_bank + item_phase_map`, không suy phase từ một bảng duy nhất.
- Update mastery theo phase-1 2PL-lite prior scoring, không claim IRT production-grade.
- Một answer có thể cập nhật nhiều KP dựa theo `item_kp_map.weight`.
- Giữ `interactions` làm shared runtime table, nhưng ref chính là canonical item ID.

## 8. Risks / trade-offs
- Calibration hiện tại là priors, chưa phải fitted model đầy đủ.
- Q-matrix baseline có thể chưa đủ sắc để tách đúng phân biệt giữa KP chồng lấp.
- Nếu `item_phase_map` thiếu, assessment có thể tạo session nhưng không có câu hỏi.
- AI summary phải là lớp bổ sung; không được để nó ảnh hưởng scoring logic.

## 9. Testing / validation
Backend:
- `tests/services/test_assessment_canonical_cutover.py`
- `tests/services/test_assessment_canonical_mastery_cutover.py`
- `tests/services/test_assessment_ai_summary.py`
- `tests/test_placement_assessment_service.py`

Contract/E2E:
- `tests/contract/test_canonical_runtime_routes.py`
- `frontend/tests/routes/assessment/results/page.test.tsx`

Cần xác nhận:
- start response không leak `correct_answer`;
- submit ghi canonical interaction;
- results trả về `learning_unit_results`;
- mastery updates khớp item mapping.

## 10. Demo-worthy points
- Assessment không là form quiz đơn thuần; nó đầy đủ scoring, persistence, và mastery update.
- Cùng một engine phục vụ placement, review, mini quiz, replan.
- Nói tốt cho report vì phần này cho thấy sự kết hợp giữa product flow, psychometric approximation, và runtime schema.
