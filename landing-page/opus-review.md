# Review kế hoạch `landing-page/PLAN.md`

## Tổng đánh giá

Plan có cấu trúc tốt, định vị rõ, story 5 sections hợp lý. Nhưng còn nhiều **gray areas** sẽ gây mơ hồ khi vào implement. Dưới đây là các vấn đề theo thứ tự ưu tiên.

---

## 1. Vấn đề chặn (must fix trước khi build)

### 1.1. Xung đột với route hiện tại — chưa có quyết định

- `/` hiện đang là `CourseCatalog` (`frontend/app/page.tsx`), dùng cho **cả authenticated + unauthenticated**.
- Plan nói "replace homepage" nhưng **không định nghĩa** behavior khi user đã đăng nhập:
  - User đã login vào `/` → vẫn thấy landing? Hay redirect sang catalog/dashboard?
  - Catalog hiện tại chuyển đi đâu? `/courses`? Có route đó chưa?
- Acceptance criteria chỉ nói "unauthenticated visitors can access `/`" → **bỏ sót behavior cho authenticated**.

**Fix:** thêm decision matrix:

```
unauth + GET /         → landing
authed + GET /         → redirect to /courses (hoặc giữ landing? quyết định)
catalog cũ             → move tới /courses (cần migration)
```

### 1.2. Public nav vs authenticated nav — chưa quyết

- Plan đề xuất `Product / Lộ trình học / AI Tutor / Liên hệ / Đăng nhập / Đăng ký`.
- Nhưng `Lộ trình học` và `AI Tutor` là **route protected** (`/learning-path`, `/tutor`). Click từ landing → bounce qua login → confuse.
- Không rõ: tạo `TopNav` variant mới hay fork file mới? Plan viết "or a new public nav variant" — **chưa chốt**.

**Fix:** Chốt 1 trong 2:

- (a) `PublicTopNav.tsx` riêng, chỉ gồm anchor links nội trang (`#roadmap`, `#tutor`, `#contact`) + auth CTAs.
- (b) Thêm `variant="public" | "app"` vào `TopNav.tsx` hiện có.

### 1.3. Acceptance criteria thiếu tính đo lường

Hiện criteria toàn dạng định tính ("feels intentional", "visually more cohesive"). Không thể verify pass/fail.

**Fix — thêm criteria đo được:**

- LCP < 2.5s trên mobile 4G mô phỏng
- Page load không gọi authenticated API (không leak token-required endpoint)
- Unauth user click `Đăng ký ngay` → tới `/auth/register` (route thực tế cần verify)
- `prefers-reduced-motion` → tắt parallax/scroll animations
- Lighthouse a11y ≥ 95

---

## 2. Mâu thuẫn nội tại

### 2.1. "Hybrid scroll storytelling" vs "scroll snap"

- Section *Chosen UX Direction*: "light scroll snap" trên desktop.
- Section *Motion and Scroll Behavior*: "soft scroll snap on major sections".
- Section *Risks*: không liệt kê "snap gây lỡ nội dung khi section dài".

Scroll-snap với section có content > viewport height là **anti-pattern** (user cuộn không tới được footer của section). Plan chưa nói rõ snap kiểu `mandatory` hay `proximity`, và xử lý sao khi section cao hơn viewport.

**Fix:** chốt `scroll-snap-type: y proximity` desktop only, và yêu cầu mọi section ≤ 100vh hoặc disable snap cho section đó.

### 2.2. Visual constraint mâu thuẫn

- "bold but controlled gradients" + "atmospheric backgrounds" + "lighter than dark-only AI site" + "blue/cyan/teal/indigo".
- Nhưng cũng yêu cầu "more visually intentional" và "AI product look".

Quá nhiều adjective, không có **token cụ thể**. Designer/dev mỗi người implement 1 kiểu.

**Fix:** Gắn token cụ thể trước khi build:

- primary gradient: `from-indigo-600 via-cyan-500 to-teal-400` (ví dụ)
- surface base: `slate-50` / `white`
- deep section: `slate-950` (chỉ 1 section, ví dụ chatbot)
- no purple > 5% diện tích

---

## 3. Thiếu sót quan trọng

| Thiếu | Tại sao cần |
|---|---|
| **SEO/meta** | Landing là entry point public. Cần `<title>`, `og:image`, structured data, sitemap. Plan không nhắc. |
| **i18n** | Plan dùng tiếng Việt cho CTA. Codebase có hỗ trợ multi-lang không? Nếu không, lock VN luôn và ghi rõ. |
| **Analytics/conversion tracking** | "Persuades visitors to sign up" mà không có event tracking → không đo được conversion. |
| **Asset budget** | "Visual motif: roadmap cards", "conversation panel" — illustrations từ đâu? Tự design? Lottie? SVG inline? Ảnh hưởng timeline. |
| **Empty/error states** | Landing hầu như tĩnh, nhưng nếu có dynamic content (testimonial, course count) → cần fallback. |
| **A11y baseline** | Chỉ có "CTA clarity and accessibility". Cần spec: keyboard nav, focus ring, contrast AA, motion-reduce. |
| **Test plan** | Không có UAT criteria, không nói test framework (Playwright? visual regression?). |

---

## 4. Build scope chia phase chưa hợp lý

Plan chia 3 phase: content/structure → visual alignment → polish. Nhưng:

- Phase 2 "unify colors with course public pages" là **scope creep** — đụng tới `CourseOverview.tsx` rồi.
- Acceptance criteria yêu cầu "visually more cohesive than current homepage" → nghĩa là Phase 2 là blocker, không phải optional.

**Fix:** Tách rõ:

- **Phase 1 (this PR):** chỉ landing page mới, đứng độc lập, không touch course pages.
- **Phase 2 (follow-up PR):** alignment với course pages — ra khỏi scope landing.
- Risks section nên flag scope creep này.

---

## 5. Gợi ý điều chỉnh trước khi vào code

1. Thêm section **Routing Decisions** — chốt behavior auth/unauth + di chuyển catalog cũ.
2. Thêm section **Design Tokens** — tên token cụ thể, hex/tailwind class, không chỉ tính từ.
3. Thêm section **Out of Scope** — explicit list (ví dụ: không touch `/courses`, không thêm i18n, không thay auth flow).
4. Viết lại **Acceptance Criteria** thành checklist verifiable (mỗi item có cách test).
5. Thêm **Test Plan** ngắn — manual UAT steps + automated (nếu có).
6. Thêm 1 sketch/wireframe (dùng `gsd-sketch` skill) trước khi code 4 sections.

---

## Khuyến nghị thực tế

Plan **chưa sẵn sàng để code**. Đủ để làm spec thảo luận, nhưng nếu giao cho dev/agent build ngay sẽ tạo ra:

- 1 trang đẹp nhưng route conflict với catalog hiện tại
- Public nav dẫn tới protected route → bounce loop
- Không có cách verify đã đạt mục tiêu

Đề xuất: chạy `gsd-discuss-phase` hoặc bổ sung 5 mục ở §5 vào `PLAN.md`, **rồi** mới code.
