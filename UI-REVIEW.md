# Standalone — UI Review

**Audited:** 2026-04-20
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md)
**Screenshots:** Not captured (no dev server running on ports 3000, 5173, or 8080)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | Mixed Vietnamese/English with developer debug text left in production views |
| 2. Visuals | 3/4 | Strong gradient system and icon usage; no empty-state illustrations |
| 3. Color | 2/4 | Hardcoded hex/rgb values scattered across quiz and chart components; cyan accent added outside design system |
| 4. Typography | 3/4 | Mostly consistent; one arbitrary `text-[10px]` and multiple raw `tracking-[0.24em]` arbitrary values |
| 5. Spacing | 3/4 | Standard Tailwind scale used consistently; arbitrary `rounded-[28px]`/`rounded-[32px]` values not in config |
| 6. Experience Design | 3/4 | Solid loading/error coverage; no global ErrorBoundary; progress always shows 0% for new users |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Developer debug text visible on Dashboard** — Users reading "Dashboard giờ dùng cùng course catalog với landing page, nên mỗi card sẽ dẫn đúng flow học tương ứng." on the authenticated home screen will lose trust in the product. Remove the paragraph at `app/(protected)/dashboard/page.tsx:164` and replace with a genuine value statement or remove it entirely.

2. **Hard-coded hex/rgb colors bypass the design system** — In `app/quiz/[topicId]/page.tsx` (lines 372–408) and `app/quiz/[topicId]/results/page.tsx` (lines 34–60, 280, 294, 321) 20+ color values are defined as raw `rgb()` and hex literals. These will not respond to dark mode or future rebranding. Replace with Tailwind semantic classes (`text-green-600`, `bg-red-50`, etc.) or CSS custom properties.

3. **"Stanford Course Demo" hardcoded in CourseCatalog** — The string "Stanford Course Demo" is hardcoded at `components/course/CourseCatalog.tsx:60` in the course card kicker. This is placeholder copy leaking into production. The field should be driven by course metadata (`course.provider` or similar), or the kicker removed until data is available.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**Issues found:**

**Developer debug text exposed to users:**
- `app/(protected)/dashboard/page.tsx:164` — subtitle reads "Dashboard giờ dùng cùng course catalog với landing page, nên mỗi card sẽ dẫn đúng flow học tương ứng." This is clearly an internal implementation note, not user-facing copy.

**Hardcoded placeholder strings:**
- `components/course/CourseCatalog.tsx:60` — "Stanford Course Demo" kicker rendered on every course card regardless of the actual course provider. Should come from course data.
- `components/course/CourseCatalog.tsx:78` — "Included course preview" / "Preview available in overview" are vague filler strings that add no value. Replace with meaningful metadata (topic count, module count).
- `components/course/CourseCatalog.tsx:90` — CTA "Open overview" is generic. Consider "Xem khóa học" or "Bắt đầu" to maintain language consistency.
- `app/page.tsx:92` — "Loading course catalog..." is English on a Vietnamese-first app. Replace with "Đang tải danh sách khóa học...".

**Mixed language inconsistency:**
- The app is Vietnamese-first, but the course catalog component uses English in key CTAs: "Open overview", "Recommended", "Explore overview", "Preview available in overview". Other parts of the app use Vietnamese throughout (`Đăng nhập`, `Đăng ký ngay`, etc.). This creates a jarring bilingual experience.

**Progress placeholder not resolved:**
- `app/(protected)/dashboard/page.tsx:118` — "Tiến độ: 0%" is hardcoded with no dynamic calculation. Even for new users this should either be conditionally hidden or computed from real data.

**What works well:**
- Auth forms (`LoginForm`, `RegisterForm`) have specific, natural Vietnamese copy: "Chào mừng trở lại", "Quên mật khẩu?", "Chưa có tài khoản?".
- Validation error messages are specific: "Mật khẩu phải ít nhất 8 ký tự", "Email không hợp lệ".
- Onboarding steps have clear step titles and subtitles.
- Error strings in async paths are contextual: "Không thể tải nội dung. Vui lòng thử lại." (`app/learn/[topicId]/page.tsx:62`).
- Password strength labels ("Yếu", "Trung bình", "Tốt", "Mạnh") are contextual.

---

### Pillar 2: Visuals (3/4)

**Issues found:**

**No empty-state illustrations:**
- `components/course/CourseCatalog.tsx:29-34` — empty state renders only a text label "No courses are available in this view yet." (also note: English). No icon, illustration, or guidance on what action the user can take.
- Dashboard tab empty state (`app/(protected)/dashboard/page.tsx:238-244`) uses a plain "Không có khóa học nào trong mục này." text-only message.

**Icon-only buttons with adequate labels (passing):**
- Dark mode toggle: `aria-label="Chuyển giao diện"` — good.
- Bell/notification: `aria-label="Thông báo"` — good.
- Sidebar collapse: `aria-label="Mở rộng sidebar"` — good.
- Password show/hide: `aria-label="Ẩn mật khẩu"` / `aria-label="Hiện mật khẩu"` — good.

**Visual hierarchy:**
- Auth layout uses a clear focal point: centered card with logo mark, brand name, then form.
- Course cards (CourseCatalog) use gradient hero sections to establish visual weight — effective.
- Onboarding stepper with animated progress bar provides good context.
- Dashboard stat cards with coloured icon backgrounds create readable scannable layout.

**Loading states visual treatment:**
- `LoadingSpinner` is minimal (SVG spinner only). For the main course catalog load on the landing page, this results in `app/page.tsx:91` showing a card with "Loading course catalog..." text and no visual affordance. A skeleton loader would be a stronger pattern for a content-heavy page.

**What works well:**
- Gradient system across course cards is diverse and visually interesting.
- Decorative blobs on auth/onboarding pages add depth without being distracting (`aria-hidden`).
- Radar chart on profile is a distinctive data visualisation choice.
- Password strength meter with segmented bars gives immediate feedback.

---

### Pillar 3: Color (2/4)

**Issues found:**

**Hardcoded hex values outside the design system (20+ instances):**

In `app/quiz/[topicId]/page.tsx` (lines 372–408):
```
borderStyle = "rgb(34,197,94)";   // green-500 — use text-green-500 class
bgStyle = "rgb(240,253,244)";     // green-50
textStyle = "rgb(21,128,61)";     // green-700
borderStyle = "rgb(239,68,68)";   // red-500
bgStyle = "rgb(254,242,242)";     // red-50
textStyle = "rgb(185,28,28)";     // red-700
```

In `app/quiz/[topicId]/results/page.tsx` (lines 34–60, 280, 294, 321):
- Skill level colors: `#94a3b8`, `#ef4444`, `#f97316`, `#3b82f6`, `#10b981`
- Bloom taxonomy colors: `#ef4444`, `#f97316`, `#3b82f6`, `#8b5cf6`
- Inline style: `color: result.mastery_after >= result.mastery_before ? "#10b981" : "#ef4444"`

In `components/assessment/RadarChart.tsx` (lines 35–38, 141, 143, 150, 184, 193):
- Skill level map: `#f87171`, `#fb923c`, `#60a5fa`, `#34d399`
- SVG `fill="#2563EB"` and `stroke="#2563EB"` — these match primary-600 but bypass the token system

Also in `app/(protected)/profile/page.tsx` (lines 27–32): duplicated skill color map as hardcoded hex.

**Cyan accent added outside design system:**
- `app/page.tsx:45` and `components/course/CourseOverview.tsx:26` use `text-cyan-700` for kicker text. Cyan is not defined in `tailwind.config.ts` as a brand color — it is a raw Tailwind utility class. If it is intentionally a secondary accent, it should be added to the color tokens.

**Accent (primary-600) usage — broadly appropriate:**
- 199 `text-primary-*` / `bg-primary-*` / `border-primary-*` matches across 33 files. While high in count, many are in a shared CSS layer (`globals.css` component classes: `btn-primary`, `input-base`, `sidebar-item.active`), so the effective overuse surface is smaller. Active nav items, primary buttons, and focus rings all use primary-600 consistently.

**Dark mode color coverage:**
- Design tokens cover both light and dark via CSS custom properties (`var(--bg-page)`, `var(--text-primary)`) — well structured.
- Hardcoded hex values in SVG attributes and inline styles will not adapt to dark mode.

**Profile page skill color duplication:**
- `SKILL_COLORS` object is defined twice with different values: `app/(protected)/profile/page.tsx:26-32` and implicitly mirrored in `components/assessment/RadarChart.tsx:34-39`. These should be extracted to a shared constant.

---

### Pillar 4: Typography (3/4)

**Font sizes in use across application files:**

`text-xs`, `text-sm`, `text-base`, `text-lg`, `text-xl`, `text-2xl`, `text-3xl`, `text-4xl` — 8 distinct sizes. This exceeds the ideal 4-size limit for a tightly constrained scale.

In practice the distribution is:
- `text-xs` — meta labels, badges, captions
- `text-sm` — body, form labels, secondary text
- `text-base` — body paragraphs
- `text-lg` — section headings
- `text-xl` — page sub-titles
- `text-2xl` / `text-3xl` — page titles
- `text-4xl` — hero headline (landing page)

The range from xs to 4xl is justified by the page variety (landing, dashboard, learning shell, quiz). However `text-3xl` and `text-4xl` are used only on the landing page — collapse to one hero size to reduce scale width.

**Arbitrary font size:**
- `components/learn/LearningUnitShell.tsx:173` — `text-[10px]` is an arbitrary value below the Tailwind `text-xs` (12px) minimum. Replace with `text-xs` and adjust tracking if needed.

**Font weights in use:**
- `font-medium`, `font-semibold`, `font-bold` — 3 weights. This is within the 2-weight guideline but only barely. All three are semantically distinct: body emphasis / UI labels / page headings. Acceptable.

**Arbitrary tracking values:**
- `tracking-[0.24em]` appears 4 times (`app/page.tsx:45`, `components/course/CourseCatalog.tsx:59`, `components/course/CourseOverview.tsx:26`, `components/course/CourseOverview.tsx:105`).
- `tracking-[0.22em]` appears 3 times (`CourseOverview.tsx:65`, `CourseOverview.tsx:122`, `LearningUnitShell.tsx:292`).
- `tracking-[0.16em]` appears in `CourseStatusBadge.tsx:28`.

These should be consolidated into a single `tracking-widest` or a custom token in `tailwind.config.ts` to avoid drift.

**Inter font family:** Correctly declared in `tailwind.config.ts` and loaded from Google Fonts. No issues.

**Line-height:** `leading-7` (body paragraphs) and `leading-snug` (card titles) are used contextually. `leading-tight` on hero headlines. Consistent hierarchy.

---

### Pillar 5: Spacing (3/4)

**Standard Tailwind spacing scale usage:**
- Components use standard scale values: `p-3`, `p-4`, `p-6`, `p-7`, `p-8`, `p-10`, `px-3.5`, `py-2.5`, `gap-1`, `gap-2`, `gap-3`, `gap-4`, `gap-5`, `gap-6`. The half-step values (`p-3.5`, `px-3.5`, `py-2.5`) are Tailwind built-ins and acceptable.
- Layout rhythm is consistent: page containers use `space-y-8`, card internals use `space-y-4` / `space-y-6`.

**Arbitrary border-radius values (notable pattern):**
- `rounded-[28px]` — used 6+ times across `CourseCatalog`, `CourseOverviewInteractive`, `app/page.tsx`, `courses/loading.tsx`
- `rounded-[32px]` — used in `CourseOverview.tsx:22` and `LearningUnitShell.tsx:100`
- `rounded-[24px]` — used in `LearningUnitShell.tsx:235`, `LearningUnitShell.tsx:285`
- `rounded-[2xl]` (32px) and `rounded-[28px]` are close to Tailwind's `rounded-3xl` (24px) and `rounded-full` — consider standardising on `rounded-3xl` or adding a custom radius token.

**Arbitrary box-shadow values:**
- `shadow-[0_18px_55px_rgba(15,23,42,0.08)]` appears 3+ times.
- `shadow-[0_24px_70px_rgba(15,23,42,0.12)]` appears on hover.
- `shadow-[0_10px_30px_rgba(15,23,42,0.08)]` in `LearningUnitShell`.

These could be added to `tailwind.config.ts` as named shadow tokens (`shadow-card`, `shadow-card-hover`) to reduce duplication and enable theming.

**Arbitrary height:**
- `min-h-[40vh]` in `app/tutor/page.tsx:80`, `min-h-[60vh]` in `app/learn/[topicId]/page.tsx:100,113`.
- `h-[calc(100vh-4.5rem)]` in `LearningUnitShell.tsx:100` — viewport arithmetic is unavoidable here for sticky layout.
- `min-h-[160px]` in `CourseCatalog.tsx:50` — acceptable for enforcing card image min height.
- `max-w-[180px]` in `history/page.tsx:816` — column width constraint, reasonable.
- `w-[22rem]` for tutor sidebar in `LearningUnitShell.tsx:332` — fixed pixel-equivalent width. Could use `w-80` (320px) or `w-96` (384px) from the scale.

**Layout consistency:** Page containers respect `max-w-7xl` / `max-w-5xl` / `max-w-2xl` consistently. The `mx-auto` pattern is applied correctly.

---

### Pillar 6: Experience Design (3/4)

**Loading states — well covered:**
- Auth layout guard: full-screen spinner while checking token (`app/(protected)/layout.tsx:47-52`).
- Dashboard: spinner during data fetch (`app/(protected)/dashboard/page.tsx:169-172`).
- Profile: spinner during parallel API calls.
- Onboarding: spinner with "Đang tải nội dung..." label while fetching modules.
- `LoadingSpinner` component has `aria-label="Loading"` and three size variants.
- Per-page loading states are present on: quiz, assessment, learn topic, tutor, history.

**Error states — adequate but incomplete:**
- Auth forms surface API errors in a styled banner with animation.
- `app/tutor/page.tsx:56` catches API failure: "Không thể tải danh sách khoá học. Vui lòng thử lại."
- `app/learn/[topicId]/page.tsx:62` — contextual error message on fetch failure.
- **Gap:** `app/(protected)/dashboard/page.tsx:148` — `.catch(() => {})` silently swallows errors. Users see an empty dashboard with no explanation if the API fails.
- **Gap:** `components/learn/LearningUnitShell.tsx:75` — `.catch(() => setChapters([]))` silently fails. No visible feedback.
- **No global ErrorBoundary** — zero occurrences found in the codebase. An uncaught React render error will crash the full page with no recovery UI.

**Empty states — partially handled:**
- Dashboard tab empty: "Không có khóa học nào trong mục này." with a border box — text-only, no action.
- CourseCatalog empty: "No courses are available in this view yet." — English, text-only.
- Achievements empty on profile: helpful contextual message "Hoàn thành assessment hoặc các phiên học đầu tiên để mở khóa thành tích." — good.

**Disabled states:**
- `Button` component correctly implements `disabled || loading` to prevent double-submit.
- `btn-primary` has `disabled:opacity-50 disabled:cursor-not-allowed` in the design system.
- Form submit buttons are disabled during API calls — consistent.

**Confirmation for destructive actions:**
- Module test has a confirmation dialog for submit (`app/module-test/[moduleId]/page.tsx:717`).
- Logout does NOT have a confirmation dialog — users can accidentally log out. Low severity but worth noting.

**Accessibility:**
- `aria-label` present on icon-only buttons (32 total occurrences across 13 files) — good coverage.
- `Input` component correctly uses `aria-invalid`, `aria-describedby`, and `role="alert"` on error messages.
- Tab panel uses `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls` on landing page — thorough.
- `aria-current="page"` on active nav links — correct.
- `LoadingSpinner` has `aria-label="Loading"` — but it should be `role="status"` per ARIA spec for live regions. The `aria-label` without a role will not be announced by all screen readers.
- Notification bell at `TopNav.tsx:130-136` has a decorative `<span>` red dot for the unread indicator with no text alternative. Screen reader users cannot determine if they have notifications.

**Progress calculation:**
- Dashboard course cards always show "Tiến độ: 0%" (`app/(protected)/dashboard/page.tsx:118`) — the progress bar width is hardcoded `w-0`. No API integration for actual progress.

---

## Files Audited

**App routes:**
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/app/globals.css`
- `frontend/app/(auth)/layout.tsx`
- `frontend/app/(auth)/login/page.tsx`
- `frontend/app/(auth)/register/page.tsx`
- `frontend/app/(auth)/forgot-password/page.tsx`
- `frontend/app/(protected)/layout.tsx`
- `frontend/app/(protected)/dashboard/page.tsx`
- `frontend/app/(protected)/profile/page.tsx`
- `frontend/app/(protected)/history/page.tsx` (partial)
- `frontend/app/onboarding/page.tsx`
- `frontend/app/assessment/page.tsx` (partial)
- `frontend/app/quiz/[topicId]/page.tsx` (partial)
- `frontend/app/quiz/[topicId]/results/page.tsx` (partial)
- `frontend/app/learn/[topicId]/page.tsx` (partial)
- `frontend/app/tutor/page.tsx` (partial)

**Components:**
- `frontend/components/layout/TopNav.tsx`
- `frontend/components/layout/Sidebar.tsx`
- `frontend/components/ui/Button.tsx`
- `frontend/components/ui/Input.tsx`
- `frontend/components/ui/LoadingSpinner.tsx`
- `frontend/components/auth/LoginForm.tsx`
- `frontend/components/auth/RegisterForm.tsx`
- `frontend/components/course/CourseCatalog.tsx`
- `frontend/components/course/CourseOverview.tsx`
- `frontend/components/learn/LearningUnitShell.tsx` (partial)
- `frontend/components/assessment/RadarChart.tsx` (partial)

**Config:**
- `frontend/tailwind.config.ts`
- `frontend/package.json`
