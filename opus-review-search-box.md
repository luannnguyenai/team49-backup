# Review `search_box.md` (kế hoạch GPT-5.4)

## Tổng đánh giá

Plan **chắc chắn về scope**, biết tránh đụng backend, có rollback, có test. Đây là điểm mạnh — hơn nhiều plan khác. Nhưng có **5 lỗ hổng kiến trúc** và vài thiếu sót UX cần xử lý trước khi code.

---

## 1. Lỗ hổng kiến trúc

### 1.1. "Catalog đã tải sẵn" không tồn tại như một nguồn duy nhất

Plan viết: *"lọc cục bộ trên catalog đã tải sẵn"*. Nhưng:

- `/` dùng `useCourseCatalogStore`
- `/dashboard` có store/presenter riêng
- `/tutor` có `buildUserCourseCollections` riêng

→ Không có **một** dataset chung. Mỗi page filter dataset của chính nó. Plan đã ngầm thừa nhận điều này (Phase 3 vs Phase 4 tách riêng), nhưng câu mở đầu "Architecture" gây hiểu nhầm. **Sửa lại 1 dòng** để rõ: "filter cục bộ tại từng page, mỗi page tự quản lý dataset của mình; utility `course-search.ts` chỉ làm pure-filter".

### 1.2. Search box đặt trong `TopNav` global → mismatch route

`TopNav` render ở mọi route, nhưng search chỉ hợp lệ trên 2-3 page. Plan phase 2 viết:

> "ở route khác vẫn có thể hiển thị nhưng disabled/readonly by design, hoặc ẩn hẳn tùy code hiện tại thuận hơn"

→ **Defer quyết định = nợ kỹ thuật.** Đề xuất chốt:

- Allowlist routes trong `TopNav` qua `usePathname()`: `["/", "/dashboard", "/tutor"]` → render input.
- Route khác: ẩn hẳn (không "disabled" — confuse user, lãng phí non-zero space).

### 1.3. Behavior `q` khi đổi route — chưa định nghĩa

User đang ở `/dashboard?q=cnn`, click sang `/tutor`. Hai lựa chọn:

- (a) Drop `q` (URL mới không có `q`) → user phải gõ lại → annoy.
- (b) Carry `q` sang `/tutor?q=cnn` → consistent search experience.

Plan không nói. **Phase 6 nhắc "khi route đổi: input phải sync lại từ URL hiện tại"** — chỉ giải quyết một chiều. Cần chốt strategy carry-over.

### 1.4. Debounced `router.replace` race với navigation

TopNav debounce ~250ms → `router.replace(?q=...)`. Nếu user gõ rồi click nav link nhanh:

- Debounce fire **sau** navigation → ghi `?q=` vào URL của route mới (ngoài allowlist) → URL dirty.

**Fix:** flush hoặc cancel debounce khi `pathname` đổi (dùng `useEffect` cleanup). Plan không nhắc.

### 1.5. `router.push` vs `router.replace` không nói

Mỗi keystroke debounced thành 1 entry history → back button trở nên vô dụng. **Phải `router.replace`.** Cần ghi rõ trong Phase 2.

---

## 2. Thiếu sót UX quan trọng

### 2.1. Vietnamese diacritics

Search "nhap mon" phải match "Nhập môn". Plan chỉ nói "case-insensitive", không nhắc accent-insensitive. Với product VN → **bắt buộc**. Thêm vào `normalizeCourseSearchQuery`:

```ts
str.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase()
```

### 2.2. Min query length / trim

Query 1 ký tự match quá rộng (UX kém + perf nếu dataset lớn). Đề xuất min 2 ký tự sau trim, query < min thì coi như rỗng.

### 2.3. `useSearchParams` cần Suspense boundary

Next 14 App Router: client component dùng `useSearchParams` cần Suspense boundary cha (build sẽ fail nếu không có). Plan không nhắc. `TopNav` đã ở root layout — kiểm tra layout đã wrap Suspense chưa. Nếu chưa → phải thêm.

### 2.4. Tutor page: `activeCourse` có thể bị filter mất

Phase 4 viết "không làm sai logic `activeCourse`" — quá lỏng. Nếu user đang học course X mà gõ "abc" filter ra → activeCourse biến mất khỏi UI? Cần spec rõ:

- Search chỉ áp lên grid recommended/others, KHÔNG áp lên activeCourse panel? Hay áp luôn?
- Quyết định trước, không deferred.

### 2.5. A11y: announce result count

Khi filter thay đổi, không có `aria-live` thông báo "5 kết quả cho 'cnn'" → screen reader user bị mù thay đổi. Thêm 1 region nhỏ.

---

## 3. Thiếu sót khác

| Thiếu | Mức độ |
|---|---|
| Behavior khi `q` có nhưng không page nào nhận (route ngoài allowlist) → URL still có `q`, lãng phí. Có nên auto-strip không? | thấp |
| Plan claim "Light mode không đổi ngoài search interaction" / "Dark mode readable" trong Verification — không có cách test. Không phải verification thực sự, chỉ là regression check chung chung. | thấp |
| Không nhắc URL encoding với ký tự đặc biệt (`&`, `#`, space) — `URLSearchParams` xử lý được nhưng cần ghi rõ test case. | thấp |
| Không có guard nào cho XSS trong query render (nếu hiển thị "Không tìm thấy với từ khóa: {q}"). React tự escape, nhưng nên ghi explicit. | thấp |
| `mock-course-catalog.test.ts` mention mơ hồ "only if needed" — bỏ luôn cho gọn. | thấp |

---

## 4. Mâu thuẫn nhỏ với plan landing-page

`landing-page/PLAN.md` đề xuất biến `/` thành landing (không có catalog). Plan này vẫn coi `/` là catalog route. **Hai plan đang lệch pha.** Cần align thứ tự thực hiện:

- Nếu landing-page xong trước → bỏ `/` khỏi search allowlist, thêm `/courses` (route mới).
- Nếu search xong trước → landing PR sẽ phải gỡ search khỏi `/`.

Ghi vào Non-Goals hoặc Dependencies.

---

## 5. Đánh giá tính sẵn sàng

| Tiêu chí | Trạng thái |
|---|---|
| Scope rõ | Tốt |
| File map cụ thể | Tốt |
| Test plan | Tốt (utility), trung bình (integration) |
| UX edge cases | **Yếu** (diacritics, route change, debounce race) |
| Routing decisions | **Chưa đủ** (allowlist, q carry-over) |
| Phối hợp với plan khác | **Chưa nhắc** (landing-page) |

**Verdict:** plan có thể implement được, nhưng dev sẽ phải tự quyết §1.2, §1.3, §1.4, §1.5, §2.1 trong lúc code → mỗi quyết định ngầm là 1 PR comment phía sau. Đề xuất bổ sung 1 section **"Decisions Locked"** vào plan trước khi vào Phase 1, gồm:

```
- Allowlist routes: ["/", "/dashboard", "/tutor"]
- q carry-over khi đổi route: YES (giữ q trong URL mới nếu route trong allowlist), drop nếu out
- router.replace, không push
- Debounce 250ms, flush on Enter, cancel on pathname change
- Normalize: lowercase + NFD strip diacritics + trim
- Min query length: 2
- activeCourse trên /tutor: KHÔNG bị filter (luôn hiển thị nếu có)
- Suspense boundary: verify root layout đã có
```
