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

## Post-Merge Integration Decisions

Sau merge commit `73a8d1a`, hybrid branch tiếp tục có thêm một số quyết định tích hợp quan trọng không xuất hiện như conflict Git thuần túy, nhưng vẫn là conflict kiến trúc cần ghi lại.

## Decision 3: `src/routers/auth.py`

### Conflict source

- `001-course-first-refactor` cần giữ flow `login -> onboarding -> assessment -> return-to-course`
- `db-review` có pattern Redis/rate-limit/denylist tốt hơn nhưng không được phép làm gãy flow course-first hiện tại

### Decision

- Resolve thủ công trên nền behavior của `001-course-first-refactor`
- Thêm Redis-backed rate limiting theo kiểu `best available`
- Fallback về in-memory limiter khi Redis unavailable
- Thêm token denylist guard và `POST /api/auth/logout`
- Giữ frontend logout clear-local-state trong `finally`, còn revoke backend là best-effort

### Reason

- Auth là vùng vừa nhạy về behavior vừa nhạy về security; không nên lấy nguyên một bên
- Hybrid cần upgrade security/runtime quality mà không được mất redirect context của flow học

## Decision 4: `src/config.py`

### Conflict source

- `db-review` có config explicit hơn cho `cors_origins`, `redis_url`
- Branch hiện tại cần giữ compatibility với cách project đang nạp `.env`

### Decision

- Giữ `Settings` hiện tại làm base
- Hấp thụ thêm parsing linh hoạt cho `cors_origins`
  - CSV string
  - JSON array string
  - direct list

### Reason

- Đây là uplift an toàn, không thay đổi product flow
- Làm app chạy ổn hơn giữa local/dev/deploy mà không kéo thêm debt config mới

## Decision 5: `src/api/app.py`

### Conflict source

- Hybrid cần Redis lifespan + exception handler + explicit CORS
- Đồng thời phải giữ backend root `/` là API landing, không quay lại static legacy UI
- Lecture ask route sau merge bị mất precheck lecture existence từng có ở branch course-first

### Decision

- Giữ root `/` là backend API landing
- Giữ Redis fail-soft startup/shutdown behavior
- Khôi phục precheck `Lecture not found` cho `POST /api/lectures/ask`
- Giữ route theo sync streaming pattern, nhưng dùng async session factory nội bộ khi không có test double được inject

### Reason

- Khôi phục đúng behavior contract cũ mà không rollback về sync DB dependency toàn phần
- Giữ tutor route tương thích với runtime hiện tại và unit tests hiện có

## Decision 6: Legacy lecture boundary

### Conflict source

- `CS231n` vẫn cần lecture/tutor stack cũ để hoạt động
- Nhưng hybrid không được để lecture stack quay lại làm product domain trung tâm

### Decision

- Tạo `src/services/legacy_lecture_adapter.py`
- Gom các helper bridge:
  - `normalize_legacy_lecture_id(...)`
  - `get_unit_by_legacy_lecture_id(...)`
  - `build_tutor_bridge_payload(...)`
- Ghi rõ boundary note trong `src/models/store.py` và `src/services/llm_service.py`

### Reason

- Tách rõ legacy adapter khỏi canonical learning-unit contract
- Giảm mơ hồ cho team khi review hoặc tiếp tục migrate CS231n về canonical model sau này

## Decision 7: `main` schema v1 review

### Conflict source

- `main` commit `cc14d53` adds `alembic/versions/20260418_0001_schema_v1.py`
- migration enables `pgvector`, but also mutates legacy LMS entities directly:
  - `modules`
  - `topics`
  - `questions`
  - `knowledge_components`
- hybrid already has its own Alembic topology and canonical course schema branch

### Decision

- Port `pgvector` only through runtime/compose changes for now
- Do **not** port `20260418_0001_schema_v1.py` wholesale into hybrid
- Keep schema-v1 under review until there is a dedicated reconciliation pass against:
  - `src/models/course.py`
  - hybrid Alembic heads
  - repository-backed assessment/history/auth paths

### Reason

- `pgvector` is valuable and low-risk at the runtime layer
- the rest of `schema v1` is not a pure infra uplift; it is a schema strategy decision
- importing the migration as-is would risk new Alembic conflicts and model drift across the hybrid branch
