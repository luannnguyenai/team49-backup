# Hybrid Merge Conflicts Log

## Merge

- Base branch: `001-course-first-refactor`
- Merged branch: `db-review`
- Integration branch: `hybrid/integrate-db-review`

## Conflict 1: `src/api/app.py`

### Conflict source

- `001-course-first-refactor` đổi backend root `/` thành API landing JSON cho frontend chạy ở `3000`
- `db-review` giữ root `/` serve static HTML legacy, nhưng thêm Redis lifecycle, DomainError handler, explicit CORS

### Decision

- Giữ `001-course-first-refactor` cho root `/`
- Giữ các cải tiến từ `db-review` ở:
  - Redis lifespan
  - `DomainError` handler registration
  - explicit `cors_origins`
  - async lecture route structure

### Reason

- Root static HTML legacy mâu thuẫn với system design hybrid đã chốt
- Backend hygiene từ `db-review` là phần nên hấp thụ

## Conflict 2: `src/services/llm_service.py`

### Conflict source

- `001-course-first-refactor` có `build_chat_model_kwargs()` để inject API key/settings đúng cho model provider và lazy-init LLM
- `db-review` refactor file sang async DB helpers dùng `async_session`

### Decision

- Giữ async DB helper pattern từ `db-review`
- Giữ lazy model construction và API-key-aware factory từ `001-course-first-refactor`
- Giữ signature `context_binding_id` để không phá course-first tutor contract, nhưng chưa persist binding này trong QA history

### Reason

- Hybrid cần cả runtime tutor đang hoạt động lẫn cấu trúc DB access sạch hơn
- Không nên rollback về model init trực tiếp vì sẽ mất fix đã làm cho provider/API key

## Notes

- Sau merge đầu tiên, chỉ có 2 conflict code thực sự cần resolve
- Đây là dấu hiệu tốt: `course-first core` và `db-review` backend hygiene đang ít đè nhau hơn dự đoán ban đầu
