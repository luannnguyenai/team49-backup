# Search Box Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến search box ở top navigation thành search thật theo URL (`?q=`), lọc cục bộ trên catalog đã tải sẵn, hoạt động cùng dashboard filters mà không làm lan thay đổi sang backend hay các component ngoài phạm vi.

**Architecture:** Search sẽ được triển khai hoàn toàn ở frontend. `TopNav` chịu trách nhiệm đồng bộ input với URL query param `q`; từng page đang render course list sẽ đọc `q` từ URL và áp filter cục bộ bằng utility chung. Không thay đổi API backend, không thêm endpoint search mới, không gắn logic search vào những component không render catalog.

**Tech Stack:** Next.js App Router, React 18 client hooks, URLSearchParams, TypeScript, existing course catalog/frontend presenters.

---

## Scope Guardrails

- Chỉ sửa frontend.
- Không đổi contract backend `courseApi.catalog()`.
- Không thêm search vào toàn app ngay từ đầu; chỉ áp vào các surface đang hiển thị danh sách course:
  - `TopNav`
  - `dashboard`
  - `tutor`
  - nếu có public catalog route đang dùng cùng luồng course list thì chỉ nối lại utility, không tạo nhánh logic riêng
- Không refactor lớn `TopNav`, `dashboard`, `tutor`.
- Không chạm các component không liên quan đến course list như assessment, onboarding, history.

## File Map

**Create:**
- `frontend/lib/course-search.ts`

**Modify:**
- `frontend/components/layout/TopNav.tsx`
- `frontend/app/(protected)/dashboard/page.tsx`
- `frontend/app/tutor/page.tsx`
- `frontend/components/course/CourseCatalog.tsx`
- `frontend/tests/unit/dashboard/presenters.test.ts` or nearby relevant search tests if already aligned
- `frontend/tests/unit/mock-course-catalog.test.ts` only if needed for coverage adjacency
- `frontend/tests/...` add one focused search test file if current layout makes that cleaner

**Do not modify unless implementation proves necessary:**
- `frontend/lib/api.ts`
- backend files under `src/`

---

## Phase 1: Define Isolated Search Contract

**Objective:** Chốt đúng hành vi search trước khi sửa UI.

**Files:**
- Create: `frontend/lib/course-search.ts`
- Reference: `frontend/types/index.ts`

- [ ] Xác định fields được search:
  - `title`
  - `short_description`
  - `hero_kicker` nếu có

- [ ] Xác định behavior:
  - URL param là `q`
  - query rỗng thì không filter
  - giữ nguyên logic tab/status hiện có, search chạy sau tab filter
  - không call backend

- [ ] Viết utility API nhỏ:
  - `normalizeCourseSearchQuery(query: string): string`
  - `matchesCourseQuery(course: CourseCatalogItem, query: string): boolean`
  - `filterCoursesByQuery(courses: CourseCatalogItem[], query: string): CourseCatalogItem[]`

- [ ] Giữ utility thuần, không import router, không import component.

---

## Phase 2: URL State Layer In Top Navigation

**Objective:** Kích hoạt search box thật nhưng chỉ bằng URL state, không gắn logic business vào `TopNav`.

**Files:**
- Modify: `frontend/components/layout/TopNav.tsx`

- [ ] Bỏ các dấu hiệu placeholder-only:
  - xóa `readOnly`
  - xóa `tabIndex={-1}`
  - bỏ `value=""` cứng

- [ ] Đọc query hiện tại bằng:
  - `useSearchParams()`
  - `usePathname()`
  - `useRouter()`

- [ ] Thêm local input state để người dùng gõ mượt, nhưng source of truth vẫn là URL.

- [ ] Khi input đổi:
  - cập nhật local state ngay
  - debounce ngắn trước khi ghi `q` vào URL
  - nếu input trống thì xóa `q` khỏi URL
  - giữ lại các query param khác nếu có

- [ ] Chỉ enable search bar ở các route có course list:
  - `/dashboard`
  - `/tutor`
  - route course catalog nếu có
  - ở route khác vẫn có thể hiển thị nhưng disabled/readonly by design, hoặc ẩn hẳn tùy code hiện tại thuận hơn

- [ ] Không gắn fetch, không filter data trực tiếp trong `TopNav`.

---

## Phase 3: Dashboard Integration

**Objective:** Search hoạt động trên dashboard mà không phá filter tabs hiện tại.

**Files:**
- Modify: `frontend/app/(protected)/dashboard/page.tsx`
- Reference: `frontend/features/dashboard/presenters.ts`
- Create or Modify: `frontend/lib/course-search.ts`

- [ ] Đọc `q` từ URL trên page dashboard.

- [ ] Áp thứ tự lọc rõ ràng:
  1. lấy `courses`
  2. áp `filterDashboardCourses(courses, activeTab)`
  3. áp `filterCoursesByQuery(filteredByTab, q)`

- [ ] Không sửa `filterDashboardCourses` nếu không cần.
  - Nếu cần, chỉ giữ presenter thuần và không trộn URL logic vào presenter.

- [ ] Cập nhật empty state:
  - nếu tab có data nhưng query không match thì hiển thị message riêng kiểu “Không tìm thấy khóa học phù hợp với từ khóa …”
  - nếu tab vốn rỗng thì giữ message cũ

- [ ] Giữ nguyên CTA, card, navigation hiện có.

---

## Phase 4: Tutor Catalog Integration

**Objective:** Dùng cùng search contract ở tutor page để hành vi nhất quán giữa các surface hiển thị course.

**Files:**
- Modify: `frontend/app/tutor/page.tsx`
- Create or Modify: `frontend/lib/course-search.ts`

- [ ] Đọc `q` từ URL trên tutor page.

- [ ] Áp search cho các collection đang render:
  - `joinedCourses`
  - `recommendedCourses`
  - `others` nếu surface đó được hiển thị/đếm

- [ ] Không đổi logic `buildUserCourseCollections`.
  - Search phải là lớp ngoài, applied-after-collection-build.

- [ ] Nếu query đang có:
  - đảm bảo count/empty copy phản ánh đúng kết quả sau filter
  - không làm sai logic `activeCourse`

---

## Phase 5: Shared Rendering Hygiene

**Objective:** Tránh rải logic search vào card/component presentational.

**Files:**
- Review: `frontend/components/course/CourseCatalog.tsx`

- [ ] Giữ `CourseCatalog` là presentational component nhận `items`.

- [ ] Không cho `CourseCatalog` tự đọc URL.

- [ ] Chỉ sửa `CourseCatalog` nếu cần một empty message riêng truyền từ parent.
  - Ưu tiên xử lý empty state ở page-level thay vì trong component này.

---

## Phase 6: Query UX Details

**Objective:** Hoàn thiện trải nghiệm mà vẫn cô lập thay đổi.

**Files:**
- Modify: `frontend/components/layout/TopNav.tsx`

- [ ] Placeholder rõ nghĩa:
  - `Tìm theo tên khóa học, mô tả...`

- [ ] Thêm nút clear nhỏ nếu layout cho phép.
  - Chỉ reset `q`, không reset tab hiện tại.

- [ ] Khi người dùng nhấn Enter:
  - flush debounce ngay
  - đồng bộ URL tức thì

- [ ] Khi route đổi:
  - input phải sync lại từ URL hiện tại

---

## Phase 7: Testing Plan

**Objective:** Chứng minh search hoạt động mà không ảnh hưởng luồng cũ.

**Files:**
- Create: `frontend/tests/unit/course-search.test.ts`
- Modify or Create: dashboard/tutor route tests tùy cấu trúc hiện có

- [ ] Test utility thuần:
  - query rỗng trả full list
  - match theo `title`
  - match theo `short_description`
  - match theo `hero_kicker`
  - case-insensitive

- [ ] Test dashboard behavior:
  - `coming_soon` tab + query vẫn lọc đúng
  - `all` tab + query vẫn giữ full behavior cũ ngoài phần search

- [ ] Test TopNav behavior ở mức vừa đủ:
  - input phản ánh giá trị từ URL
  - nhập text cập nhật query param
  - xóa text sẽ xóa `q`

- [ ] Không mở rộng test sang backend.

---

## Phase 8: Verification Checklist

- [ ] `TopNav` search box gõ được thật.
- [ ] URL cập nhật `?q=...`.
- [ ] Reload trang vẫn giữ query.
- [ ] Dashboard tab filter vẫn hoạt động.
- [ ] Search không làm thay đổi `courseApi.catalog()` hoặc backend response.
- [ ] Tutor page không vỡ grouping logic.
- [ ] Empty state đúng khi query không có kết quả.
- [ ] Light mode không đổi ngoài search interaction.
- [ ] Dark mode search input vẫn readable theo token theme hiện tại.

---

## Implementation Sequence

1. Tạo `frontend/lib/course-search.ts`
2. Kích hoạt `TopNav` search + URL sync
3. Nối dashboard vào utility filter
4. Nối tutor page vào utility filter
5. Thêm empty-state copy riêng cho search
6. Viết unit tests cho utility
7. Viết route/component tests tối thiểu cho dashboard + TopNav
8. Chạy verify frontend

---

## Non-Goals

- Không thêm backend search endpoint
- Không search trên history, assessment, module test, onboarding
- Không highlight từ khóa trong card ở vòng đầu
- Không đổi contract `courseApi.catalog()`
- Không refactor presenters lớn

---

## Rollback Strategy

Nếu implementation gây side effects:
- revert `TopNav` URL sync trước
- giữ lại `course-search.ts` utility độc lập
- rollback từng page integration riêng (`dashboard`, `tutor`) mà không cần đụng backend

---

## Expected Outcome

Sau khi hoàn thành:
- search box không còn là placeholder
- search hoạt động thật trên các danh sách course chính
- URL phản ánh state search
- thay đổi được cô lập ở frontend, không lan sang backend hoặc các component không liên quan
