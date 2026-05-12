# Feature: Replan

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `5. Dòng dữ liệu học tập thích ứng`, `8. Replan flow`, `10. Guardrails architecture`

## 1. Mục tiêu
Replan cho phép learner nói "tôi đã biết phần này" sau khi đã có learning path, sau đó hệ thống phân tích claim, xác định unit liên quan trong current path, gợi ý prerequisite cần review, và khởi tạo assessment có scope chính xác để cập nhật lộ trình.

## 2. User/problem this solves
Sau khi bắt đầu học, learner có thể nhận ra:
- một số phần trong path quá dễ;
- đã học rồi ở ngoài hệ thống;
- muốn tối ưu lại path mà không rebuild tất cả bằng tay.

Nếu không có replan, người dùng phải học theo path cũ hoặc admin/dev phải can thiệp.

## 3. System scope
Backend:
- `src/routers/replan.py`
- `src/services/replan_service.py`
- `src/services/replan_keyword_planner.py`
- `src/services/replan_unit_discovery.py`
- `src/services/replan_prerequisite_suggestions.py`
- `src/services/replan_question_scope.py`

Frontend:
- `frontend/app/replan/page.tsx`
- `frontend/components/replan/*`
- `frontend/lib/replan-api.ts`
- `frontend/lib/replan-claim-guardrails.ts`
- `frontend/lib/replan-assessment-context.ts`

## 4. Architecture & flow

```text
User từ /learn hoặc /agent -> /replan
  -> nhập knowledge claim
  -> frontend validate basic guardrails
  -> POST /api/replan/analyze
  -> keyword planner + unit discovery trên current path
  -> suggest prerequisite units nếu cần
  -> user review selected scope
  -> POST /api/replan/assessment/start
  -> tạo assessment session dùng existing assessment flow
  -> user làm assessment
  -> planner cập nhật dựa trên evidence mới
```

Replan không tự commit path trong chat hay tạo result page riêng; nó là scope builder + assessment bridge.

## 5. Key components
- `ReplanKnowledgeClaimStep`: nhập claim.
- `ReplanScopeReviewStep`: review units tìm được.
- `PrerequisiteSuggestionDialog`: thêm prerequisite khi claim đè chạm vào unit downstream.
- `ReplanKeywordPlanner`: trích keyword/intent từ claim.
- `ReplanCurrentPathUnitDiscovery`: tìm unit trong current path.
- `replan_service`: orchestration analyze/start.

## 6. Data model / contracts
API:
- `POST /api/replan/analyze`
- `POST /api/replan/assessment/start`

Response analyze có thể trả:
- `status="ok"`
- `status="guardrail_blocked"`
- danh sách units, prerequisites, handled notes, question counts

Start assessment trả session tương thích với `/assessment`, không tạo route kết quả riêng cho replan.

## 7. Technical decisions
- Replan phân tích trên current path thật, không chạy trên toàn bộ content catalog.
- Scope builder tách riêng khỏi chat agent; agent chỉ đề xuất action và link sang `/replan`.
- Reuse engine assessment hiện có thay vì làm một replan-assessment subsystem riêng.
- Guardrails chạy sớm để chặn claim quá ngắn, `skip all`, hoặc "tôi biết hết".

## 8. Risks / trade-offs
- Claim của user là free text, nên extraction có rủi ro lexical ambiguity.
- Nếu prerequisite suggestion quá ít, user có thể test sai phạm vi.
- Nếu current path chưa có data tốt, replan sẽ không tìm được unit ý nghĩa.
- Replan cần cân bằng giữa "linh hoạt" và "không để user skip vô tội vạ".

## 9. Testing / validation
Backend:
- `tests/services/test_replan_service.py`
- `tests/services/test_replan_keyword_planner.py`
- `tests/services/test_replan_unit_discovery.py`
- `tests/services/test_replan_prerequisite_suggestions.py`
- `tests/services/test_replan_question_scope.py`

Frontend:
- `frontend/tests/routes/replan/page.test.tsx`
- `frontend/tests/unit/replan/*`

Cần test:
- guardrail block xảy ra trước active path lookup nếu claim xấu;
- selected units được filter đúng;
- assessment start dùng selected scope;
- không tạo duplicate result flow.

## 10. Demo-worthy points
- Replan là feature hay để viết report vì nó thể hiện khả năng adaptive sau onboarding.
- Có sự kết hợp giữa NLP parsing, current-path reasoning, prerequisite graph, và assessment reuse.
- Đây là một ví dụ tốt cho design "không để LLM mutate state trực tiếp".
