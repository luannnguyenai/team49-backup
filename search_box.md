# Search Box Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến search box ở top navigation thành search thật theo URL (`?q=`), lọc cục bộ trên dataset course của từng page, hoạt động cùng dashboard filters mà không làm lan thay đổi sang backend hay các component ngoài phạm vi.

**Architecture:** Search sẽ được triển khai hoàn toàn ở frontend. `TopNav` chịu trách nhiệm đồng bộ input với URL query param `q`; từng page đang render course list sẽ đọc `q` từ URL và áp filter cục bộ bằng utility chung trên dataset mà page đó tự quản lý. Không thay đổi API backend, không thêm endpoint search mới, không gắn logic search vào những component không render catalog.

**Tech Stack:** Next.js App Router, React 18 client hooks, URLSearchParams, TypeScript, existing course catalog/frontend presenters.

---

## Scope Guardrails

- Chỉ sửa frontend.
- Không đổi contract backend `courseApi.catalog()`.
- Không thêm search vào toàn app ngay từ đầu; chỉ áp vào các surface đang hiển thị danh sách course:
  - `dashboard`
  - `tutor`
- `TopNav` chỉ là shell nhập query + đồng bộ URL; không được giữ business logic filter.
- Không refactor lớn `TopNav`, `dashboard`, `tutor`.
- Không chạm các component không liên quan đến course list như assessment, onboarding, history.

## Decisions Locked

- Search route allowlist: `["/dashboard", "/tutor"]`
- Route ngoài allowlist: ẩn hẳn search input, không render phiên bản disabled
- `q` carry-over khi đổi route:
  - từ allowlist route sang allowlist route: giữ `q`
  - từ allowlist route sang route ngoài allowlist: drop `q`
- Nếu người dùng chọn một search result là course cụ thể, điều hướng tới route overview/catalog của course: `/courses/[slug]`
- URL updates dùng `router.replace`, không dùng `router.push`
- Debounce URL update: `250ms`
- Nhấn Enter: flush debounce ngay
- Khi `pathname` đổi: cancel debounce cũ để tránh ghi bẩn URL route mới
- Normalize query: `trim` + lowercase + Unicode NFD strip diacritics
- Min query length: `2`; query ngắn hơn được coi như rỗng
- `/tutor` `activeCourse` panel không bị filter bởi search; chỉ các grid/list course bên dưới mới áp search
- `useSearchParams` phải được bọc trong `Suspense` boundary cục bộ, không yêu cầu thay root layout
- Vì `/` hiện là landing page và repo chưa có route `/courses` dạng catalog list, search phase đầu không áp cho public landing

## File Map

**Create:**
- `frontend/lib/course-search.ts`

**Modify:**
- `frontend/components/layout/TopNav.tsx`
- `frontend/app/(protected)/dashboard/page.tsx`
- `frontend/app/tutor/page.tsx`
- `frontend/components/course/CourseCatalog.tsx` only if parent-level empty state proves insufficient
- `frontend/app/courses/[courseSlug]/page.tsx` only if result-entry UX needs a query-preserving back-link or follow-up polish
- `frontend/tests/unit/dashboard/presenters.test.ts` only if presenter contract changes
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
  - query sau normalize có độ dài `< 2` thì coi như rỗng
  - giữ nguyên logic tab/status hiện có, search chạy sau tab filter
  - khi người dùng chọn đúng 1 course result từ UI search, action mặc định là mở `/courses/[slug]`
  - không call backend

- [ ] Viết utility API nhỏ:
  - `normalizeCourseSearchQuery(query: string): string`
  - `matchesCourseQuery(course: CourseCatalogItem, query: string): boolean`
  - `filterCoursesByQuery(courses: CourseCatalogItem[], query: string): CourseCatalogItem[]`

- [ ] Giữ utility thuần, không import router, không import component.

- [ ] Utility normalize phải xử lý tiếng Việt không dấu:
  - `"nhap mon"` match `"Nhập môn"`
  - dùng Unicode normalize NFD + strip diacritics

- [ ] Utility phải chỉ trả dữ liệu đã được React render an toàn; nếu page hiển thị lại `q` trong empty state thì chỉ render text thô, không dùng HTML injection.

---

## Phase 2: URL State Layer In Top Navigation

**Objective:** Kích hoạt search box thật nhưng chỉ bằng URL state, không gắn logic business vào `TopNav`.

**Files:**
- Modify: `frontend/components/layout/TopNav.tsx`
- Create or Modify: a local `TopNavSearch` child wrapped in `Suspense` if needed to satisfy App Router search-param requirement

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
  - dùng `router.replace`, không dùng `push`

- [ ] Chỉ render search bar ở các route có course list:
  - `/dashboard`
  - `/tutor`
  - route khác: ẩn hoàn toàn

- [ ] Không gắn fetch, không filter data trực tiếp trong `TopNav`.

- [ ] Nếu phase đầu có render dropdown/autocomplete kết quả ngay trong `TopNav`, mỗi item result phải là `Link` hoặc `router.push()` tới `/courses/[slug]`.
  - Không điều hướng tới `/courses/[slug]/start`
  - Không điều hướng tới `/tutor`
  - Mặc định mở course overview/catalog page, ví dụ `/courses/cs230`

- [ ] Chốt behavior carry-over:
  - nếu user đang ở `/dashboard?q=cnn` rồi điều hướng sang `/tutor`, nav link hoặc route sync phải giữ `?q=cnn`
  - nếu user rời allowlist route sang route khác, query phải bị drop thay vì để URL bẩn

- [ ] Chốt debounce lifecycle:
  - Enter flush ngay
  - unmount/pathname change cancel timer cũ
  - không để timer cũ cập nhật URL của route mới

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
  - nếu hiển thị `q`, dùng text render mặc định của React, không inject HTML

- [ ] Giữ nguyên CTA, card, navigation hiện có.

- [ ] Search results trên dashboard nếu click course card vẫn phải đi tới route course overview hiện tại:
  - `ready` course có thể tiếp tục giữ CTA riêng theo card
  - nhưng entry từ search-result selection phải thống nhất là `/courses/[slug]`

- [ ] Thêm 1 `aria-live` region nhỏ cho result count hoặc empty-search state để screen reader nhận biết danh sách đã đổi theo query.

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

- [ ] Lock behavior `activeCourse`:
  - panel “Tiếp tục học” luôn hiển thị nếu có active course
  - search không ẩn panel này, chỉ áp vào các collection/list bên dưới

- [ ] Không đổi logic `buildUserCourseCollections`.
  - Search phải là lớp ngoài, applied-after-collection-build.

- [ ] Nếu query đang có:
  - đảm bảo count/empty copy phản ánh đúng kết quả sau filter
  - không làm sai logic `activeCourse`
  - nếu người dùng chọn 1 course từ kết quả search, route đích vẫn là `/courses/[slug]`

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

- [ ] Nếu có dropdown kết quả trong `TopNav`:
  - hiển thị title + mô tả ngắn
  - click result mở `/courses/[slug]`
  - Enter khi đang highlight một result cũng mở `/courses/[slug]`
  - Enter khi không highlight result thì chỉ commit query vào URL như bình thường

- [ ] Khi người dùng nhấn Enter:
  - flush debounce ngay
  - đồng bộ URL tức thì

- [ ] Khi route đổi:
  - input phải sync lại từ URL hiện tại

- [ ] Handle ký tự đặc biệt qua `URLSearchParams`:
  - space
  - `&`
  - `#`
  - tiếng Việt có dấu

---

## Phase 7: Testing Plan

**Objective:** Chứng minh search hoạt động mà không ảnh hưởng luồng cũ.

**Files:**
- Create: `frontend/tests/unit/course-search.test.ts`
- Modify or Create: dashboard/tutor route tests tùy cấu trúc hiện có

- [ ] Test utility thuần:
  - query rỗng trả full list
  - query dài `< 2` trả full list
  - match theo `title`
  - match theo `short_description`
  - match theo `hero_kicker`
  - case-insensitive
  - accent-insensitive cho tiếng Việt

- [ ] Test dashboard behavior:
  - `coming_soon` tab + query vẫn lọc đúng
  - `all` tab + query vẫn giữ full behavior cũ ngoài phần search
  - empty state hiển thị đúng khi query không match
  - `aria-live` region cập nhật khi kết quả đổi
  - click course result/card từ trạng thái search mở đúng `/courses/[slug]`

- [ ] Test TopNav behavior ở mức vừa đủ:
  - input phản ánh giá trị từ URL
  - nhập text cập nhật query param bằng `replace`
  - xóa text sẽ xóa `q`
  - Enter flush debounce
  - pathname change cancel debounce cũ
  - route allowlist carry-over đúng giữa `/dashboard` và `/tutor`
  - nếu có result selection UI, chọn result sẽ điều hướng tới `/courses/[slug]`

- [ ] Không mở rộng test sang backend.

---

## Phase 8: Verification Checklist

- [ ] `TopNav` search box gõ được thật.
- [ ] URL cập nhật `?q=...`.
- [ ] Reload trang vẫn giữ query.
- [ ] Điều hướng giữa `/dashboard` và `/tutor` giữ `q`.
- [ ] Điều hướng ra route ngoài allowlist không để sót `q`.
- [ ] Chọn một course result sẽ mở đúng course overview/catalog route `/courses/[slug]`.
- [ ] Dashboard tab filter vẫn hoạt động.
- [ ] Search không làm thay đổi `courseApi.catalog()` hoặc backend response.
- [ ] Tutor page không vỡ grouping logic.
- [ ] `activeCourse` panel ở tutor vẫn ổn khi query không match list bên dưới.
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
- Không áp search cho landing page `/` ở phase đầu

## Dependencies

- Search plan này giả định `/` tiếp tục là landing page. Nếu sau này có public course catalog route riêng, route đó sẽ được thêm ở phase sau thay vì nhét vào phase đầu.

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
