# Hybrid Integration Tasks: `001-course-first-refactor` + `db-review`

Mục tiêu của task list này là:

- tạo nhánh hybrid giữ được commit history của cả team
- giữ `course-first core` làm kiến trúc sản phẩm chính
- hấp thụ có chọn lọc backend/database hygiene từ `db-review`
- tránh merge thẳng hai nhánh theo kiểu hợp nhất cú pháp nhưng pha tạp kiến trúc

Format bám theo tinh thần `speckit-tasks`: dependency-ordered, có phase, có file path, đủ cụ thể để team làm từng bước.

---

## Phase 1: Setup Integration Branch

- [x] T001 Tạo nhánh tích hợp từ `001-course-first-refactor` bằng lệnh `git checkout -b hybrid/integrate-db-review` để giữ product baseline
- [x] T002 Merge `db-review` vào `hybrid/integrate-db-review` bằng `git merge --no-ff db-review` để preserve history commit của cả team
- [x] T003 Ghi lại danh sách conflict files vào `docs/hybrid-merge-conflicts.md` để team resolve có chủ đích thay vì xử lý ad-hoc
- [x] T004 Đối chiếu conflict với [docs/hybrid-system-design.md](/mnt/shared/AI-Thuc-Chien/A20-App-049/docs/hybrid-system-design.md) và [docs/branch-hybrid-merge-plan.md](/mnt/shared/AI-Thuc-Chien/A20-App-049/docs/branch-hybrid-merge-plan.md) trước khi resolve file nào cũng theo cùng một nguyên tắc

## Phase 2: Foundational Conflict Resolution

- [x] T005 Resolve `src/models/course.py` theo `001-course-first-refactor`, giữ canonical course domain làm product source of truth
- [x] T006 Resolve `src/schemas/course.py` theo `001-course-first-refactor`, giữ DTO/schema cho course-first API
- [x] T007 Resolve `src/routers/courses.py` theo `001-course-first-refactor`, giữ catalog/overview/start/learning-unit routes
- [x] T008 Resolve `src/services/course_bootstrap_service.py`, `src/services/course_catalog_service.py`, `src/services/course_entry_service.py`, `src/services/learning_unit_service.py` theo `001-course-first-refactor`
- [x] T009 Resolve `frontend/app/page.tsx`, `frontend/app/courses/[courseSlug]/page.tsx`, `frontend/app/courses/[courseSlug]/start/page.tsx`, `frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx` theo flow course-first hiện tại
- [x] T010 Resolve `frontend/components/course/*`, `frontend/components/learn/*`, `frontend/features/course-platform/presenters.ts`, `frontend/lib/course-gate.ts`, `frontend/lib/auth-redirect.ts`, `frontend/stores/courseCatalogStore.ts` theo `001-course-first-refactor`
- [x] T011 Resolve `src/models/store.py`, `src/services/llm_service.py`, `src/services/router.py` theo nguyên tắc `legacy adapter only`, không để lecture stack quay lại làm domain trung tâm

## Phase 3: App Config and Backend Hardening

- [x] T012 Resolve `src/config.py` bằng cách giữ config đang phục vụ course-first app và port thêm `cors_origins`, `redis_url` cùng các field explicit hữu ích từ `db-review:src/config.py`
- [x] T013 Resolve `src/api/app.py` bằng cách giữ routers/runtime behavior của branch hiện tại, thêm Redis lifespan, exception handlers, explicit CORS từ `db-review:src/api/app.py`, và không khôi phục root static HTML
- [x] T014 Thêm hoặc port `src/exceptions.py` từ pattern của `db-review` để có `DomainError` hierarchy rõ ràng
- [x] T015 Thêm hoặc port `src/exception_handlers.py` từ pattern của `db-review` rồi wire vào `src/api/app.py`
- [x] T016 Thêm hoặc port `src/services/redis_client.py` để có lifecycle Redis chuẩn cho auth/rate-limit/cache ngắn hạn
- [x] T017 Viết hoặc cập nhật test backend cho `src/api/app.py`, `src/config.py`, `src/exception_handlers.py` trong `tests/` để xác nhận app startup, CORS config, và error responses không làm gãy course routes

## Phase 4: Auth and Security Integration

- [x] T018 Resolve `src/routers/auth.py` thủ công, giữ behavior tương thích flow `login -> onboarding -> assessment -> return-to-course`
- [x] T019 Port có chọn lọc `db-review` rate-limit pattern vào auth flow, ưu tiên Redis-backed limiter thay cho in-memory limiter trong `src/routers/auth.py`
- [x] T020 Port token denylist hoặc revocation support từ `db-review` vào auth/security layer nếu implementation đủ chín để không phá current session flow
- [x] T021 Cập nhật test auth tương ứng trong `tests/` để xác nhận login, onboarding gate, assessment gate, và return redirect vẫn đúng

## Phase 5: Repository Layer Integration

- [x] T022 Thêm `src/repositories/base.py` theo pattern của `db-review` làm nền cho repository layer của hybrid branch
- [x] T023 Áp repository layer cho phần user/auth state, tạo hoặc cập nhật `src/repositories/*` tương ứng cho user/session/profile nếu vùng này đã DB-backed thật
- [x] T024 Áp repository layer cho assessment/history/recommendation ở `src/repositories/*` chỉ khi logic đang chạm DB thật, không bọc giả các bootstrap services
- [ ] T025 Giữ `src/services/course_catalog_service.py`, `src/services/course_entry_service.py`, `src/services/learning_unit_service.py` ở vai trò application service, chưa ép repository hóa mọi thứ khi runtime data còn transitional
- [ ] T026 Nếu tích hợp `db-review:src/services/question_selector.py`, đặt nó vào `src/services/question_selector.py` hoặc package phù hợp và chỉ nối vào flow assessment khi test coverage đủ

## Phase 6: Legacy Adapter Boundary Cleanup

- [x] T027 Xác nhận `src/models/store.py` chỉ còn phục vụ legacy lecture/tutor adapter cho `CS231n`
- [x] T028 Xác nhận mapping canonical-to-legacy trong `src/models/course.py` hoặc service liên quan vẫn là đường một chiều từ `LearningUnit` xuống `Lecture`, không ngược lại
- [x] T029 Kiểm tra `src/routers/courses.py` và `src/services/learning_unit_service.py` để đảm bảo learning unit contract vẫn là public-facing contract
- [x] T030 Kiểm tra `src/api/app.py` và lecture routes để đảm bảo `/api/lectures/*` chỉ còn là compatibility layer cho tutor/legacy retrieval
- [x] T031 Cập nhật [docs/course-first-refactor-architecture.md](/mnt/shared/AI-Thuc-Chien/A20-App-049/docs/course-first-refactor-architecture.md) hoặc [docs/hybrid-system-design.md](/mnt/shared/AI-Thuc-Chien/A20-App-049/docs/hybrid-system-design.md) nếu ranh giới adapter thay đổi sau integration

## Phase 7: Frontend Stability Verification

- [x] T032 Chạy lại route tests cho `frontend/tests/routes/course-catalog.test.tsx`, `frontend/tests/routes/course-start.test.tsx`, `frontend/tests/routes/personalized-catalog.test.tsx`, `frontend/tests/routes/learning-unit.test.tsx`, `frontend/tests/routes/legacy-tutor-redirect.test.tsx`
- [x] T033 Chạy lại tutor/component tests cho `frontend/tests/unit/in-context-tutor.test.tsx` và các unit tests liên quan presenter/auth redirect
- [x] T034 Chạy `frontend` typecheck để xác nhận merge không làm vỡ contracts giữa presenter, routes, và components
- [x] T035 Chạy các e2e specs đã có trong `frontend/tests/e2e/course-discovery.spec.ts`, `frontend/tests/e2e/course-gating.spec.ts`, `frontend/tests/e2e/lecture-tutor.spec.ts` nếu môi trường local đủ điều kiện

## Phase 8: Backend Stability Verification

- [x] T036 Chạy contract tests `tests/contract/test_course_catalog_api.py`, `tests/contract/test_course_start_api.py`, `tests/contract/test_learning_unit_api.py`
- [x] T037 Chạy tutor/lecture related tests `tests/test_lecture_routes.py`, `tests/test_chat_model_factory.py` để chắc rằng Redis/config/exception refactor không làm gãy AI Tutor
- [x] T038 Chạy các tests backend nền `tests/test_course_platform_foundation.py`, `tests/test_course_entry_service.py`, và các auth tests liên quan sau khi merge
- [x] T039 Kiểm tra live flow trên local: `Home -> Overview -> Start -> login/onboarding/assessment -> return to course -> learning unit -> AI Tutor`

## Phase 9: Documentation and Review Artifacts

- [x] T040 Cập nhật [docs/hybrid-system-design.md](/mnt/shared/AI-Thuc-Chien/A20-App-049/docs/hybrid-system-design.md) nếu thực tế integration khác với design ban đầu
- [x] T041 Cập nhật [docs/branch-hybrid-merge-plan.md](/mnt/shared/AI-Thuc-Chien/A20-App-049/docs/branch-hybrid-merge-plan.md) với các conflict thực tế và quyết định đã chốt
- [x] T042 Hoàn thiện `docs/hybrid-merge-conflicts.md` thành decision log cho từng file/package conflict lớn
- [x] T043 Viết summary review cho team vào `docs/hybrid-integration-review.md`, nêu rõ phần nào lấy từ nhánh nào và vì sao

## Phase 10: Merge to Main With History Preserved

- [ ] T044 Commit riêng từng cụm integration trên `hybrid/integrate-db-review`, tránh dồn mọi thay đổi vào một commit lớn
- [ ] T045 Merge `hybrid/integrate-db-review` vào `main` bằng `git merge --no-ff hybrid/integrate-db-review` hoặc PR kiểu `Create a merge commit`
- [ ] T046 Không dùng `Squash and merge` hoặc `Rebase and merge` khi đưa hybrid branch vào `main`
- [ ] T047 Sau khi merge vào `main`, chạy smoke verification tối thiểu cho UI `3000` và backend `8000`

---

## Suggested MVP Slice

Nếu team muốn làm theo từng đợt nhỏ, nên ưu tiên:

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 7
5. Phase 8

Đó là lát cắt nhỏ nhất để có một hybrid branch:

- preserve history
- giữ đúng course-first architecture
- hấp thụ được app/config/exception hardening quan trọng nhất từ `db-review`

## Fast Ownership Summary

- `001-course-first-refactor` sở hữu: course domain, course routes, learning flow, frontend structure
- `db-review` đóng góp: config hygiene, Redis patterns, DomainError, repository pattern, backend structure cleanup
- `Resolve thủ công`: `src/api/app.py`, `src/config.py`, `src/routers/auth.py`, `src/models/store.py`, `src/services/llm_service.py`, `src/services/router.py`, `src/database.py`
