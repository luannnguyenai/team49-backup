# Phase 1 — Migrate Ad-Hoc CTA Sang `.btn-primary` Mới (Ink)

**Ưu tiên:** 🔴 P0
**Phụ thuộc:** **Phase 0 phải xong** (`.btn-primary` đã re-tint thành ink rounded-full)
**Thời lượng ước tính:** 45 phút

## Vấn Đề

Sau khi Phase 0 redefine `.btn-primary` → ink rounded-full, các CTA tự build / ad-hoc bypass class này vẫn còn lệch:

| File | Hiện tại | Phải về |
|---|---|---|
| `frontend/components/landing/LandingPage.tsx` "Create your account" | tự build `inline-flex ... rounded-full bg-slate-950 ... hover:bg-slate-800` | `.btn-primary` (auto ink, auto rounded-full) |
| `frontend/components/landing/LandingPage.tsx` "Sign in" | tự build `border-slate-200 bg-white/80 rounded-full` | `.btn-secondary` (auto glass) |
| `frontend/components/layout/PublicTopNav.tsx` "Đăng ký" | tự build `bg-slate-950 rounded-full` | `.btn-primary` |
| `frontend/components/layout/PublicTopNav.tsx` "Đăng nhập" | tự build outline | `.btn-secondary` |
| `frontend/app/assessment/results/page.tsx` Continue CTA | `bg-blue-600` | `.btn-primary` |
| `frontend/app/quiz/[learningUnitId]/page.tsx` action button | `bg-emerald-600` (có thể là Submit) | `.btn-primary` (nếu là primary action) |
| `frontend/app/module-test/[sectionId]/page.tsx` action button | tương tự quiz | `.btn-primary` |

**Mục tiêu:** Sau Phase 1, không còn ad-hoc primary CTA tự build trên public + assessment + quiz. Mọi primary action đều đi qua `.btn-primary`.

## Files Cần Touch

- `frontend/components/landing/LandingPage.tsx`
- `frontend/components/layout/PublicTopNav.tsx`
- `frontend/app/assessment/results/page.tsx`
- `frontend/app/quiz/[learningUnitId]/page.tsx` *(chỉ button primary action — không động đáp án selection)*
- `frontend/app/module-test/[sectionId]/page.tsx` *(tương tự)*
- `frontend/tests/unit/landing/landing-cta.test.tsx` *(mới)*
- `frontend/tests/unit/layout/publictopnav-cta.test.tsx` *(mới)*
- `frontend/tests/unit/assessment/results-cta.test.tsx` *(mới)*

## Scope

**Chỉ đổi className. Không động:**
- `href`, `onClick`, handler
- Form submit logic
- Icon, padding (trừ khi `.btn-primary` đã có sẵn padding khác)
- Hero gradient, glass card, background, layout
- Quiz answer button (đó là input choice, không phải primary CTA)

## Implementation

### Step 1 — Landing CTA

```tsx
// Before
<Link
  href="/register"
  className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
>
  Create your account
  <ArrowRight className="h-4 w-4" />
</Link>
<Link
  href="/login"
  className="inline-flex items-center rounded-full border border-slate-200 bg-white/80 px-6 py-3 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-white dark:border-slate-700 dark:bg-slate-900/80 dark:text-white"
>
  Sign in
</Link>

// After
<Link href="/register" className="btn-primary px-6 py-3">
  Create your account
  <ArrowRight className="h-4 w-4" />
</Link>
<Link href="/login" className="btn-secondary px-6 py-3">
  Sign in
</Link>
```

> Class `btn-primary` đã tự có `rounded-full`, `bg-slate-950`, `hover:bg-slate-800`, `text-white` từ Phase 0.

### Step 2 — PublicTopNav

```tsx
// Sign up
<Link href="/register" className="btn-primary px-4 py-2">
  Đăng ký
</Link>

// Sign in (nếu là button secondary)
<Link href="/login" className="btn-secondary px-4 py-2">
  Đăng nhập
</Link>
```

### Step 3 — Assessment Results

Tìm `bg-blue-600` trong `frontend/app/assessment/results/page.tsx`:

```tsx
// Before
<button onClick={...} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg ...">
  Continue
</button>

// After
<button onClick={...} className="btn-primary">
  Continue
</button>
```

### Step 4 — Quiz / Module-test Submit Button

Chỉ migrate **primary action button** (Submit, Next, Continue). Answer choice buttons (`bg-emerald-600` khi đúng, `bg-red-50` khi sai) **giữ nguyên** — đó là state UI, sẽ migrate ở Phase 4 qua `state-success/error` token.

```tsx
// Submit / Next button
// Before
<button className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-lg">
  Submit
</button>

// After
<button className="btn-primary">
  Submit
</button>
```

## DoD Checklist

- [ ] Landing `LandingPage.tsx`: 2 CTA (Create account + Sign in) đã dùng `.btn-primary` / `.btn-secondary`
- [ ] PublicTopNav: 2 CTA dùng class chuẩn
- [ ] Assessment results: 0 raw `bg-blue-600` trên primary CTA
- [ ] Quiz / Module-test: primary action button dùng `.btn-primary`
- [ ] Visual: 5 page primary CTA giống hệt nhau (ink rounded-full hover bg-slate-800)
- [ ] Visual: 5 page secondary CTA giống hệt nhau (glass outline rounded-full)
- [ ] Không thay đổi href / handler / submit logic
- [ ] Type check pass: `npm run type-check`
- [ ] 3 unit test mới pass
- [ ] Existing tests (assessment, quiz, module-test, landing) vẫn pass
- [ ] Manual smoke: register flow OK, login flow OK, assessment submit OK, quiz submit OK
- [ ] Light + dark mode parity
- [ ] Commit: `design(sync-ui phase-1): migrate ad-hoc CTAs to landing-aligned btn-primary`

## Unit Tests

### `frontend/tests/unit/landing/landing-cta.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LandingPage from "@/components/landing/LandingPage";

describe("Landing CTA contract", () => {
  it("create-account uses btn-primary, no raw bg-slate-950 utility", () => {
    render(<LandingPage />);
    const cta = screen.getByRole("link", { name: /create your account/i });
    expect(cta.className).toContain("btn-primary");
    // Allow class .btn-primary (which internally uses var(--brand-ink)) but no raw bg-slate-950 utility on the link itself
    expect(cta.className).not.toMatch(/\bbg-slate-950\b/);
  });

  it("sign-in uses btn-secondary", () => {
    render(<LandingPage />);
    const cta = screen.getByRole("link", { name: /^sign in$/i });
    expect(cta.className).toContain("btn-secondary");
  });
});
```

### `frontend/tests/unit/layout/publictopnav-cta.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PublicTopNav from "@/components/layout/PublicTopNav";

describe("PublicTopNav CTA contract", () => {
  it("sign-up uses btn-primary", () => {
    render(<PublicTopNav />);
    const cta = screen.getByRole("link", { name: /đăng ký|sign up/i });
    expect(cta.className).toContain("btn-primary");
    expect(cta.className).not.toMatch(/\bbg-slate-950\b/);
  });
});
```

### `frontend/tests/unit/assessment/results-cta.test.tsx`

```tsx
import { describe, expect, it } from "vitest";
// Nếu CTA nằm trong client subcomponent, render component đó.
// Nếu page là async server component khó render, extract sub-component (e.g. <ResultsContinueButton />)
// rồi assert:
//   expect(button.className).toContain("btn-primary");
//   expect(button.className).not.toMatch(/\bbg-blue-600\b/);

describe("Assessment results CTA contract", () => {
  it.todo("renders Continue with btn-primary, no bg-blue-600");
});
```

## Verify

```bash
cd frontend
npm run type-check

npm test -- --run frontend/tests/unit/landing/landing-cta.test.tsx \
  frontend/tests/unit/layout/publictopnav-cta.test.tsx \
  frontend/tests/unit/assessment/results-cta.test.tsx

# Grep guard
grep -rn -E '\bbg-(blue|emerald)-600\b' \
  frontend/app/assessment/ \
  frontend/app/quiz/ \
  frontend/app/module-test/ \
  frontend/components/landing/ \
  frontend/components/layout/
# Expected: chỉ còn ở những nơi chính đáng (ví dụ answer-correct background trong quiz)

npm run dev
# Visual: scroll qua landing → public nav → /register → /login → assessment → quiz → module-test
# Tất cả primary CTA: ink rounded-full
# Tất cả secondary CTA: glass outline rounded-full
```

## Rollback

```bash
git revert <commit-sha>
```
