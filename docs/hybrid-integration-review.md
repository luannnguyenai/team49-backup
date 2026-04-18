# Hybrid Integration Review

## Mục tiêu của file này

File này chốt lại trạng thái thực tế của nhánh `hybrid/integrate-db-review` sau khi:

- merge `db-review` vào `001-course-first-refactor`
- preserve history commit của cả team
- tích hợp có chọn lọc các phần backend/database hygiene từ `db-review`

Mục đích là để team có một file ngắn, thực dụng, đủ dùng cho:

- review chéo giữa các member
- đối chiếu khi resolve conflict tiếp
- giải thích vì sao một số phần được giữ, một số phần chưa kéo sang

## Kết luận tổng quát

Hybrid branch hiện tại đúng hướng nếu tiêu chí chính là:

- giữ `course-first product architecture`
- tăng chất lượng backend/auth/runtime
- không làm gãy UI flow đã refactor

Nó chưa phải trạng thái "done toàn bộ", nhưng đã vượt qua giai đoạn merge thô và đang ở mức:

- chạy được
- test core xanh
- boundary chính đã rõ hơn

## Những gì giữ từ `001-course-first-refactor`

Đây là phần được giữ làm `behavior source`:

- canonical `course-first` domain
- `src/models/course.py`
- `src/routers/courses.py`
- `src/services/course_catalog_service.py`
- `src/services/course_entry_service.py`
- `src/services/learning_unit_service.py`
- frontend flow:
  - `Home`
  - `Course Overview`
  - `Start`
  - `Learning Unit`
  - `AI Tutor` in-context
- frontend presenter/store/route orchestration đã refactor trước đó

Lý do giữ:

- đây là north-star product architecture đã chốt với user
- nếu bỏ phần này thì hybrid sẽ quay lại mental model `LMS + legacy lecture pages`

## Những gì hấp thụ từ `db-review`

Đây là phần được dùng làm `backend quality pattern source`:

- `DomainError` + exception handlers
- Redis lifecycle
- explicit `cors_origins` / `redis_url`
- rate limit pattern cho login
- token revoke / denylist pattern cho auth

Những uplift đã có mặt trong code:

- app startup fail-soft nếu Redis unavailable
- login ưu tiên Redis-backed rate limit
- fallback về local limiter khi Redis chưa sẵn
- access/refresh token có `jti`
- denylist guard ở dependency/auth flow
- `POST /api/auth/logout`
- frontend logout gọi backend revoke

## Những gì resolve thủ công

Một số vùng không thể lấy nguyên một nhánh:

- `src/api/app.py`
- `src/config.py`
- `src/routers/auth.py`
- `src/services/llm_service.py`
- `src/models/store.py`

Nguyên tắc resolve:

- product flow lấy từ `001-course-first-refactor`
- runtime hardening và error model lấy ý tưởng từ `db-review`
- không khôi phục root static UI legacy ở backend

## Những gì đã được cô lập rõ hơn

### Legacy lecture adapter

Hybrid branch hiện đã rõ hơn ở chỗ:

- `src/models/store.py` được coi là legacy adapter data model
- `src/services/legacy_lecture_adapter.py` là bridge layer rõ ràng
- `src/services/llm_service.py` được note là nằm sau compatibility boundary

Ý nghĩa:

- `learning unit` vẫn là contract public-facing
- lecture stack chỉ là lớp nuôi `CS231n` trong giai đoạn chuyển tiếp

## Những gì vẫn còn transitional

Các điểm sau vẫn chưa xong:

- course metadata runtime chưa DB-authoritative hoàn toàn
- repository layer chưa rollout rộng
- live full flow `login -> onboarding -> assessment -> return-to-course` chưa được re-verify đầy đủ trên hybrid branch
- backend docker-compose bootstrap hiện còn vướng Alembic multiple-heads ở bước `alembic upgrade head`

## Verification snapshot hiện tại

Những gì đã verify được:

- frontend route/unit/typecheck xanh
- backend contract/auth/config tests xanh
- Playwright smoke:
  - `9 passed`
  - `2 skipped` (hai case personalized catalog vẫn đang intentionally skip vì thiếu seeded recommendation state)
- live smoke đã cover:
  - public catalog
  - course overview
  - coming-soon gate
  - unauthenticated start -> login redirect with `next`
  - learning unit page
  - AI Tutor panel open

Những gì chưa cover trọn vẹn:

- `login -> onboarding -> assessment -> return-to-course` như một journey đầy đủ
- startup qua `docker compose` không cần workaround local uvicorn

## Đánh giá thực tế

### Điểm tốt của hybrid hiện tại

- Giữ đúng product direction
- Hấp thụ được nhiều uplift backend mà không phá flow chính
- Commit history của cả team vẫn được preserve
- Boundary giữa canonical course layer và legacy lecture layer rõ hơn trước

### Điểm chưa nên tự tin quá mức

- Chưa đủ để gọi là production-ready hoàn chỉnh
- Chưa chứng minh xong repository strategy tối ưu
- Chưa migrate được `CS231n` sang canonical model hoàn toàn

## Recommendation cho bước tiếp theo

Thứ tự thực dụng nhất từ đây:

1. Rerun thêm e2e/smoke cho flow học thật
2. Cập nhật docs task/status một vòng nữa nếu có thay đổi
3. Chỉ port repository layer ở nơi thật sự DB-backed
4. Sau đó mới cân nhắc merge vào `main`

## Quy tắc chọn nhánh khi có tranh luận trong team

Nếu tranh luận về:

- `product flow`
- `route structure`
- `course overview/start/learning unit`
- `frontend flow`

thì ưu tiên `001-course-first-refactor`

Nếu tranh luận về:

- `error handling`
- `Redis lifecycle`
- `config hygiene`
- `auth hardening`
- `backend separation of concerns`

thì ưu tiên pattern từ `db-review`
