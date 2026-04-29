# Recommendation + Dashboard Consistency Plan

## Goal

Make recommendation behavior consistent across:

- `/learn` personalized planner
- dashboard tab `Dành cho bạn`
- global search in the top navigation

Add a global search dropdown under the navigation search input on every `TopNav`, showing matching course results immediately without redirecting.

This change must stay isolated. Do not modify unrelated behavior in assessment, auth, planner generation core, or learning-unit runtime.

## Problem Summary

Today the product has three different concepts that look similar to the user but are backed by different code paths:

- `/learn` renders the current personalized learning path from planner output
- dashboard `Dành cho bạn` renders from the course catalog and currently falls back to all courses when there are no recommended flags
- search behavior is limited and not available consistently across all navigation shells

This creates a mismatch:

- `/learn` can correctly show only the 2 courses in the selected path
- dashboard `Dành cho bạn` can show the entire catalog
- users interpret both as “recommendations”, even though they are not driven by the same source

## Design Principles

1. Keep concepts separate.
- Planner path is not the same thing as course recommendation.
- Recommendation is not the same thing as search.

2. Make recommendation semantics honest.
- `Dành cho bạn` must only show recommended courses.
- It must not silently degrade into “all courses”.

3. Keep search global but isolated.
- Navigation search should only provide quick course discovery.
- It should not mutate planner state or dashboard recommendation logic.

4. Minimize blast radius.
- Only touch components and services directly responsible for recommendation annotation, dashboard rendering, and top-nav search dropdown.

## Source of Truth

### Personalized Planner

`/learn` remains driven by planner path generation and `plan_history.recommended_path_json`.

This semantic stays unchanged:

- `/learn` = current personalized path

### Recommended Courses

Recommended courses should resolve through one backend path:

1. Primary source: `course_recommendations`
2. Fallback source: `goal_preferences.selected_course_ids`

Important data-shape constraint:

- `goal_preferences.selected_course_ids` stores course UUID strings, not slugs
- catalog rendering compares against course slugs
- therefore fallback resolution must map UUIDs to slugs before annotating `is_recommended`

This ensures the course catalog can still expose coherent recommendations even when explicit `course_recommendations` rows have not been written yet.

### Global Search

Global search should use the course catalog as a search source and remain independent from planner state.

## Scope

### Allowed Changes

- frontend `TopNav` and related search dropdown UI/state
- frontend dashboard filtering/rendering for `Dành cho bạn`
- backend course catalog recommendation resolution
- directly related tests

### Not Allowed

- planner generation algorithm beyond reading existing recommendation scope
- assessment flow
- auth flow semantics
- learning-unit runtime
- unrelated page layouts or unrelated navigation logic
- any broad refactor outside recommendation/search/dashboard consistency

## Phase Plan

### Phase 1: Lock Semantics

Objective:
- Freeze the meaning of planner path, recommended courses, and global search before changing code.

Checklist:
- `/learn` continues to mean current personalized path
- dashboard `Dành cho bạn` means recommended courses only
- global nav search means quick course lookup only
- recommendation must not silently fall back to full catalog
- search dropdown must not change planner or recommendation state

Success criteria:
- clear behavior matrix exists for:
  - user has `course_recommendations`
  - user has no `course_recommendations` but has `goal_preferences.selected_course_ids`
  - user has neither

### Phase 2: Isolate Backend Recommendation Resolution

Objective:
- Make catalog recommendation annotation consistent with planner scope when explicit recommendation rows are absent.

Implementation direction:
- update `src/services/course_catalog_service.py`
- resolve recommended course slugs with precedence:
  - `course_recommendations`
  - fallback from `goal_preferences.selected_course_ids`
- add an explicit UUID-to-slug mapping step for the fallback path
- keep precedence logic in one shared resolver so both catalog branches use the same result

Checklist:
- `view="recommended"` returns only recommended courses
- `view="all"` returns the full catalog with correct `is_recommended` flags
- explicit recommendation rows override fallback goal scope
- fallback course UUIDs are mapped to slugs before comparison with catalog rows
- the same precedence rule is used by both `view="recommended"` and `view="all"`
- remove/update old comments that instruct the frontend to fall back from empty recommended results to all courses
- no planner-generation rewrite

Success criteria:
- backend can produce a coherent recommended subset even without explicit `course_recommendations`

### Phase 3: Isolate Dashboard `Dành cho bạn`

Objective:
- Make dashboard recommendation behavior honest and consistent.

Implementation direction:
- update dashboard presenter/page logic
- remove current fallback from recommended tab to all courses

Checklist:
- `Dành cho bạn` only renders recommended courses
- if recommended set is empty, show an explicit empty state
- `Tất cả`, `Sẵn sàng`, `Sắp ra mắt` keep current behavior
- no hidden fallback to all catalog inside “for-you”
- update existing tests that currently encode the old fallback behavior

Success criteria:
- dashboard no longer misrepresents the full catalog as personalized recommendations

### Phase 4: Add Global Search Dropdown to Every `TopNav`

Objective:
- Expose the course search input consistently across all top navigation shells.

Implementation direction:
- render search input on every `TopNav`
- show a dropdown directly under the input while typing
- keep dropdown state independent from existing route-level `?q=` filtering used by `/dashboard` and `/tutor`

Checklist:
- search bar visible on every page using `TopNav`
- dropdown appears directly under the search field
- dropdown uses local component state, not shared `?q=` URL mutation during typing
- dropdown supports:
  - loading state
  - matched results
  - empty state
- click outside closes dropdown
- selecting a result navigates to the target course page
- search interaction does not auto-redirect while the user types
- guest users can use the dropdown against the general catalog
- recommended badges in the dropdown are only shown when recommendation annotation exists

Success criteria:
- users can type from any page and immediately see matching course results without leaving the page first

### Phase 5: Isolate Search Data Flow

Objective:
- Reuse course catalog data safely without creating a broad new search subsystem.

Implementation direction:
- prefer existing `courseApi.catalog({ includeUnavailable: true })`
- filter client-side for dropdown results
- keep the first version minimal and focused
- avoid repeated duplicate fetches by reusing a shared client-side cache/store for catalog data

Checklist:
- only course fields needed by dropdown are used
- query matches title and short description using existing search helpers where possible
- dropdown limits result count
- optional recommended badge can be shown from `is_recommended`
- planner store is not touched
- dashboard and dropdown should not each force their own redundant uncached catalog fetch on every mount if shared cache can be reused safely

Success criteria:
- dropdown search remains fast, local, and isolated

### Phase 6: Regression Boundaries

Objective:
- Ensure unrelated product areas are not altered.

Checklist:
- `/learn` still renders planner path as before
- assessment results CTA flow remains unchanged
- auth gating remains unchanged
- tutor and course pages only change insofar as they inherit the updated `TopNav`
- no unrelated navigation regressions
- verify `course_catalog_service` changes are not imported into planner rendering chains
- verify dropdown local state does not mutate `/dashboard` or `/tutor` page filter state

Success criteria:
- all changes remain inside recommendation/search/dashboard boundaries

### Phase 7: Verification

Objective:
- Prove the change set works locally and in Docker.

Checklist:
- targeted backend tests for recommendation resolution
- targeted frontend tests for dashboard and top-nav dropdown
- frontend type-check
- frontend production build
- Docker frontend dev build
- Docker frontend prod build

Success criteria:
- behavior is consistent in both local and Docker execution paths

## Expected UX After Change

### `/learn`

- continues to show the personalized path only
- if the selected path is `computer_vision`, it may still show only `CS230 + CS231n`
- if the selected path is `nlp`, it may still show only `CS230 + CS224n`

### Dashboard `Dành cho bạn`

- shows only recommended courses
- if recommendations are empty, it shows a clear empty state
- it no longer expands into the full catalog under the label “Dành cho bạn”

### Navigation Search

- search bar is available on every `TopNav`
- typing opens a dropdown under the input
- dropdown shows matching course results immediately
- clicking a result opens the corresponding course page

## Test Plan

### Backend Tests

- `view="recommended"` returns recommendation rows when `course_recommendations` exists
- `view="recommended"` falls back to `goal_preferences.selected_course_ids` when recommendation rows are absent
- `view="all"` annotates `is_recommended` correctly
- explicit recommendations override goal-scope fallback
- fallback works when `goal_preferences.selected_course_ids` are UUID strings rather than slugs

### Frontend Tests

- `TopNav` search input renders on every top-nav shell
- typing opens dropdown results
- no-match query shows empty state
- click outside closes the dropdown
- clicking a dropdown result navigates correctly
- dashboard `Dành cho bạn` only shows recommended courses
- dashboard `Dành cho bạn` shows empty state when there are none
- existing dashboard tests that asserted fallback-to-all are updated to assert the new empty-state behavior
- dropdown typing does not rewrite existing `/dashboard` or `/tutor` `?q=` page filter state

### Build Verification

- `npm --prefix frontend run type-check`
- `npm --prefix frontend run build`
- `docker compose build frontend`
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml build frontend`

## Non-Goals

- Do not redesign the planner
- Do not add a new backend search API unless existing catalog reuse proves insufficient
- Do not implement a broad omnibox for units, sections, tutor history, or other entities
- Do not rewrite onboarding path selection
- Do not expand recommendation scope beyond the existing goal-path model in this change

## Review Questions

Questions for review before implementation:

1. Is it acceptable that dashboard recommendation fallback is based on `goal_preferences.selected_course_ids` when explicit `course_recommendations` are absent?
2. Should the dropdown show unavailable courses as well, or only `ready` courses?
3. Should the dropdown open course overview pages for unavailable courses and start pages for ready courses, or always go to overview first?
4. Is a minimal result list sufficient, or should the dropdown include a “see all results” action later as a follow-up?
5. The current recommendation fallback source is `goal_preferences.selected_course_ids`. Is that acceptable as the canonical fallback until explicit `course_recommendations` are written consistently in runtime flows?

---

## Code Review Notes (đối chiếu với code hiện tại)

Đánh giá sau khi đọc trực tiếp `src/services/course_catalog_service.py`, `src/repositories/course_recommendation_repo.py`, `src/repositories/goal_preference_repo.py`, `src/models/learning.py`, `frontend/components/layout/TopNav.tsx`, `frontend/features/dashboard/presenters.ts`, `frontend/app/(protected)/dashboard/page.tsx`, `frontend/app/tutor/page.tsx`, `frontend/app/learn/page.tsx`.

### Điểm khớp với code hiện tại

- `course_catalog_service.list_course_catalog` đã có param `view` ("all" | "recommended") và đã đọc từ `course_recommendations` qua `CourseRecommendationRepository.get_recommended_slugs_for_user`.
- Fallback "all courses" trong tab `Dành cho bạn` thực sự tồn tại tại `frontend/features/dashboard/presenters.ts:17`: `return recommended.length > 0 ? recommended : courses;` — đây chính xác là chỗ Phase 3 cần fix.
- `goal_preferences.selected_course_ids` tồn tại đúng tên (`src/models/learning.py:264`).
- `/learn` đi qua `LearningPathShell` (planner), không import `course_catalog_service` → ranh giới Phase 6 hợp lệ.
- `courseApi.catalog({ includeUnavailable: true })` đã được dashboard sử dụng (`frontend/app/(protected)/dashboard/page.tsx:152`) → Phase 5 reuse được.
- `frontend/lib/course-search.ts` đã có `filterCoursesByQuery` + `normalizeCourseSearchQuery` → Phase 5 phải reuse, không tạo helper mới.

### Lỗi logic / thiếu sót cần sửa trong plan

1. **`selected_course_ids` chứa course UUIDs, KHÔNG phải slugs.**
   - Phase 2 viết: "resolve recommended course **slugs** with precedence: `course_recommendations` → fallback `goal_preferences.selected_course_ids`".
   - Thực tế: `selected_course_ids` được lưu là JSON list of UUID strings (xem `src/services/auth_service.py:194-199`, `src/services/recommendation_engine.py:306`, `src/services/placement_lite_service.py:48`).
   - `_get_recommended_course_slugs` hiện trả về `set[str]` slugs và service so sánh `row["slug"] in recommended_slugs` (line 103).
   - **Hệ quả nếu implement theo nguyên văn plan**: nhánh fallback sẽ so slug với UUID → không bao giờ match → `Dành cho bạn` luôn rỗng cho user chỉ có `goal_preferences`.
   - **Sửa**: trong nhánh fallback phải map UUID → slug, ví dụ thêm method vào `CourseRecommendationRepository`:
     ```python
     async def get_slugs_by_course_ids(self, course_ids: list[str | UUID]) -> set[str]:
         result = await self.session.execute(
             select(Course.slug).where(Course.id.in_(course_ids))
         )
         return {row[0] for row in result.all()}
     ```
     và gọi nó từ `_get_recommended_course_slugs` khi `course_recommendations` rỗng nhưng `goal_preferences.selected_course_ids` có giá trị.

2. **Phase 2 chưa nói rõ áp precedence cho cả `view="all"`.**
   - Hiện code chỉ resolve recommended slugs ở cả 2 nhánh `view="recommended"` (line 93) và `view="all"` (line 115), nhưng resolver chỉ đọc `course_recommendations`.
   - Nếu chỉ thêm fallback cho `view="recommended"`, thì `view="all"` (nhánh dashboard đang dùng) sẽ annotate `is_recommended=False` toàn bộ khi user chỉ có `goal_preferences`. Sau khi Phase 3 bỏ fallback, tab `Dành cho bạn` sẽ luôn empty cho nhóm user này — đây là regression.
   - **Sửa**: precedence (`course_recommendations` → `goal_preferences.selected_course_ids`) phải áp ở chính `_get_recommended_course_slugs`, dùng chung cho cả 2 nhánh `view`.

3. **Phase 4 mâu thuẫn với hành vi search hiện tại của TopNav.**
   - Code hiện tại: `SEARCH_ROUTE_ALLOWLIST = new Set(["/dashboard", "/tutor"])` (`TopNav.tsx:15`) — search là **page-scoped filter** ghi vào URL `?q=`.
   - `/dashboard` (line 147,162) và `/tutor` (line 78-87) đều đọc `searchParams.get("q")` để lọc danh sách hiển thị.
   - `buildHrefWithOptionalQuery` (line 23-35) carry-over `?q=` giữa các route trong allowlist.
   - Plan nói "dropdown must not change planner or recommendation state" nhưng **không quyết định** dropdown global có dùng cùng URL key `q` hay không.
   - **Rủi ro**: nếu dùng chung `?q=`, mỗi keystroke ở TopNav sẽ mutate URL của `/dashboard` và `/tutor` → đổi cả filter của list page và dropdown đồng thời → UX rối.
   - **Sửa**: chọn 1 trong 2 hướng và viết rõ vào Phase 4:
     - (a) Dropdown dùng **local component state** (không đụng URL); giữ `?q=` cho page filter của `/dashboard` và `/tutor` như cũ.
     - (b) Đổi URL key dropdown sang khác (vd `?cs=` cho course search) và migrate page filter sang key đó nếu cần thống nhất.
   - Khuyến nghị: hướng (a) — blast radius nhỏ nhất, đúng nguyên tắc "search dropdown must not mutate other state".

4. **Plan không liệt kê test cũ cần update.**
   - `frontend/tests/routes/dashboard/page.test.tsx` và `frontend/tests/unit/course-search.test.ts` nhiều khả năng cover hành vi fallback "recommended → all" hiện tại.
   - Phase 7 chỉ nói thêm test cho empty state — phải bổ sung "update existing dashboard tests asserting old fallback, replace with empty-state assertions".

5. **Comment cũ trong service ngược ý định mới.**
   - `course_catalog_service.py:106-109` có comment: "No recommendations yet — return empty list (frontend should fall back to all-courses tab)" — đây chính là design cũ Phase 3 muốn xoá.
   - Phase 2/Phase 3 cần ghi rõ: xoá/cập nhật comment này; verify không có caller nào dựa vào "empty list = signal to show all".

6. **Phase 5 thiếu chiến lược cache catalog cho dropdown.**
   - Nếu dropdown render trên **mọi** TopNav, mỗi mount = 1 request `courseApi.catalog` (dashboard hiện cũng tự gọi). Mỗi route change có thể tăng số request đáng kể.
   - **Sửa**: thêm vào Phase 5 hướng dẫn cụ thể — cache catalog ở shared store (Zustand) hoặc SWR/React Query với key chung `["course-catalog", { includeUnavailable: true }]`, TTL hợp lý. Dashboard cũng nên reuse cùng cache để bỏ duplicate fetch.

7. **Phase 6 thiếu verification rõ ràng cho `/learn` isolation.**
   - Plan tự tin `/learn` không bị ảnh hưởng. Cần thêm verification cụ thể trong Phase 6:
     - "Verify: `course_catalog_service` không được import bởi `recommendation_engine.py` hoặc `LearningPathShell` chain."
     - "Verify: `_get_recommended_course_slugs` mới không gọi planner code path."

8. **Hành vi dropdown cho guest user chưa nêu.**
   - `view="recommended"` trả empty cho user chưa login (line 88-90). Với guest, dropdown sẽ phải dùng `view="all"`, nhưng khi đó `is_recommended` luôn `False` → badge "Dành cho bạn" trên dropdown row sẽ không hiển thị.
   - **Sửa**: thêm 1 checklist item ở Phase 4: "guest user: dropdown vẫn hoạt động với `view="all"`; recommended badge ẩn — đây là behavior mong muốn".

### Tóm tắt mức độ ưu tiên

- **Blocker (sai sẽ break feature)**: #1 (UUID vs slug), #2 (precedence cho `view="all"`), #3 (URL `?q=` conflict).
- **Quan trọng (rủi ro regression / perf)**: #4 (test cũ), #6 (cache), #5 (comment cũ + caller).
- **Nice-to-have (rõ ý định)**: #7, #8.

Plan tổng thể đúng định hướng và ranh giới hợp lý; sửa 8 điểm trên trước khi implement để tránh phải redo.

---

## Plan Amendments Applied After Opus Review

The plan above has been updated to incorporate the main review findings:

- backend fallback now explicitly accounts for UUID-to-slug conversion before catalog annotation
- recommendation precedence is defined as shared logic for both `view="recommended"` and `view="all"`
- global dropdown search is explicitly isolated from the existing route-level `?q=` filtering used by `/dashboard` and `/tutor`
- dashboard tests that encoded the old fallback behavior must be updated, not merely supplemented
- stale code comments that describe the old fallback semantics are now in-scope for cleanup
- shared client-side catalog caching is now part of the plan to avoid duplicate fetch patterns
- isolation verification now includes explicit checks that planner rendering is not coupled to catalog recommendation resolution
- guest-user dropdown behavior is now defined as supported via general catalog search without recommendation badges
