# Phase 0 — Re-tint `.btn-primary` & `.btn-secondary` Theo Landing

**Ưu tiên:** 🔴 P0
**Phụ thuộc:** Không
**Thời lượng ước tính:** 1 giờ

## Vấn Đề

Phase 1 trong `redesign.md` định nghĩa `.btn-primary = bg-primary-600` (cyan) và `.btn-secondary = bg-surface-card border-border-subtle` (`rounded-lg`). Điều này **lệch khỏi Landing** — Landing dùng:

- Primary CTA: `bg-slate-950 text-white rounded-full hover:bg-slate-800`
- Secondary CTA: `border-slate-200 bg-white/80 text-slate-700 rounded-full`

Vì Landing là chuẩn, ta **redefine `.btn-primary` và `.btn-secondary`** ngay trong `globals.css`. Mọi nơi đã dùng `.btn-primary` (dashboard, tutor, history…) sẽ tự động đồng bộ.

## Files Cần Touch

- `frontend/app/globals.css`
- `frontend/tailwind.config.ts` *(thêm token nếu cần)*
- `frontend/tests/unit/ui/button-theme.test.tsx` *(cập nhật contract)*

## Implementation

### Step 1 — Cập nhật `globals.css`

**Thêm CSS var cho ink:**

```css
:root {
  /* === Brand ink — primary CTA color (matches Landing) === */
  --brand-ink:           #020617;   /* slate-950 */
  --brand-ink-hover:     #1e293b;   /* slate-800 */
  --brand-ink-fg:        #ffffff;

  /* Glass secondary CTA */
  --glass-bg:            rgba(255, 255, 255, 0.80);
  --glass-bg-hover:      #ffffff;
  --glass-border:        #e2e8f0;   /* slate-200 */
  --glass-fg:            #334155;   /* slate-700 */

  /* Existing: brand-primary (cyan), brand-accent, surface-*, text-*, border-subtle... giữ nguyên */
}

.dark {
  --brand-ink:           #f8fafc;
  --brand-ink-hover:     #e2e8f0;
  --brand-ink-fg:        #020617;

  --glass-bg:            rgba(15, 23, 42, 0.80);
  --glass-bg-hover:      #0f172a;
  --glass-border:        #334155;
  --glass-fg:            #f1f5f9;
}
```

**Redefine `.btn-primary` và `.btn-secondary`:**

```css
.btn-primary {
  @apply inline-flex items-center justify-center gap-2 rounded-full
         px-5 py-2.5 text-sm font-semibold
         transition-all duration-150
         active:scale-[0.98]
         disabled:cursor-not-allowed disabled:opacity-50
         focus-visible:outline-none focus-visible:ring-2
         focus-visible:ring-offset-2;
  background-color: var(--brand-ink);
  color: var(--brand-ink-fg);
  border: 1px solid transparent;
}
.btn-primary:hover { background-color: var(--brand-ink-hover); }
.btn-primary:focus-visible { box-shadow: 0 0 0 3px var(--ring-brand); }

.btn-secondary {
  @apply inline-flex items-center justify-center gap-2 rounded-full
         px-5 py-2.5 text-sm font-semibold
         transition-all duration-150
         active:scale-[0.98]
         disabled:cursor-not-allowed disabled:opacity-50
         focus-visible:outline-none focus-visible:ring-2
         focus-visible:ring-offset-2;
  background-color: var(--glass-bg);
  color: var(--glass-fg);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(8px);
}
.btn-secondary:hover {
  background-color: var(--glass-bg-hover);
  border-color: #cbd5e1; /* slate-300 */
}

/* .btn-ghost giữ nguyên — không phải primary CTA */
```

**Thêm helper class cho hero/feature card (Phase 3 sẽ dùng):**

```css
.card-glass {
  @apply rounded-3xl p-6 backdrop-blur;
  background-color: var(--glass-bg);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 20px 60px -35px rgba(15, 23, 42, 0.35);
}
.dark .card-glass {
  border-color: #1e293b;
  background-color: rgba(15, 23, 42, 0.75);
}

.card-ink {
  @apply rounded-[32px] p-6 text-white;
  background-color: var(--brand-ink);
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 30px 80px -40px rgba(8, 145, 178, 0.65);
}
```

> Note: `.card` cho protected pages giữ nguyên `rounded-xl` — đó là dạng dense, khác hero/feature surface.

### Step 2 — Cập nhật `tailwind.config.ts`

```ts
colors: {
  // ... existing surface, text, border, primary (cyan), brand ...
  brand: {
    ink:        "var(--brand-ink)",
    "ink-hover":"var(--brand-ink-hover)",
    "ink-fg":   "var(--brand-ink-fg)",
    indigo:     "#4f46e5",
    cyan:       "#06b6d4",
    teal:       "#2dd4bf",
  },
  glass: {
    bg:     "var(--glass-bg)",
    border: "var(--glass-border)",
    fg:     "var(--glass-fg)",
  },
},
```

→ Cho phép utility `bg-brand-ink`, `text-brand-ink-fg`, `bg-glass-bg`, `border-glass-border` khi cần build CTA tùy biến ngoài `.btn-*`.

## Scope

**Không động:**
- File `.tsx` page (sẽ migrate ad-hoc CTA ở Phase 1)
- Cyan `.btn-primary` cũ trong test contracts không liên quan token
- `.card`, `.input-base`, `.label`, `.btn-ghost`, `.error-msg`, `.sidebar-item`, `.link`
- Backend / API / handler

**Chỉ động:** `globals.css` (token + 2 class redefine + 2 class glass/ink mới) và `tailwind.config.ts` (thêm `brand.ink*` và `glass.*`).

## DoD Checklist

- [ ] `--brand-ink`, `--brand-ink-hover`, `--brand-ink-fg` định nghĩa ở `:root` và `.dark`
- [ ] `--glass-bg`, `--glass-bg-hover`, `--glass-border`, `--glass-fg` định nghĩa ở `:root` và `.dark`
- [ ] `.btn-primary` dùng `var(--brand-ink)`, `rounded-full`, không còn `bg-primary-600`
- [ ] `.btn-secondary` dùng glass: `var(--glass-bg)`, `var(--glass-border)`, `rounded-full`, có `backdrop-filter: blur`
- [ ] `.card-glass` và `.card-ink` thêm vào globals.css
- [ ] `tailwind.config.ts` map `brand.ink*` và `glass.*` thành utility
- [ ] Type check pass: `npm run type-check`
- [ ] Build pass: `npm run build`
- [ ] Test contract `button-theme.test.tsx` cập nhật và pass
- [ ] **Visual smoke quan trọng:** mọi page sử dụng `.btn-primary` (Dashboard course CTA, Tutor, History expand button…) đã tự động chuyển sang ink — KHÔNG được vỡ layout
- [ ] Light mode + Dark mode parity
- [ ] Commit: `design(sync-ui phase-0): re-tint btn-primary to ink and btn-secondary to glass per landing`

## Unit Tests

### Cập nhật `frontend/tests/unit/ui/button-theme.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Button from "@/components/ui/Button";

describe("Button theme contract — landing-aligned ink/glass", () => {
  it("primary button uses btn-primary class (ink CTA)", () => {
    render(<Button>Continue</Button>);
    const btn = screen.getByRole("button", { name: "Continue" });
    expect(btn.className).toContain("btn-primary");
  });

  it("secondary button uses btn-secondary class (glass CTA)", () => {
    render(<Button variant="secondary">Cancel</Button>);
    const btn = screen.getByRole("button", { name: "Cancel" });
    expect(btn.className).toContain("btn-secondary");
  });
});
```

### Mới: `frontend/tests/unit/ui/button-computed-style.test.tsx`

> Test computed style để xác nhận token được resolve đúng (cần JSDOM + import globals.css trong setup).

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Button from "@/components/ui/Button";

describe("Button resolves to ink/glass tokens", () => {
  it("primary button border-radius is full pill", () => {
    render(<Button>Go</Button>);
    const btn = screen.getByRole("button", { name: "Go" });
    const style = window.getComputedStyle(btn);
    // Pill button — border-radius rất lớn
    expect(parseInt(style.borderRadius)).toBeGreaterThan(99);
  });
});
```

> Nếu setup JSDOM không nạp được Tailwind compiled CSS, skip test này và rely vào visual sweep.

## Verify

```bash
cd frontend
npm run type-check
npm test -- --run frontend/tests/unit/ui/button-theme.test.tsx
npm run build
npm run dev

# Visual sweep — tất cả các page có .btn-primary phải hiển thị ink rounded-full:
# - http://localhost:3000  → Landing CTA "Create account" (đã ink, không đổi nhưng giờ cùng class)
# - /dashboard             → "Continue" course CTA → ink ✓
# - /tutor                 → các button → ink ✓
# - /history               → expand button → ink ✓
# - /profile               → save button → ink ✓
# - Auth pages chưa migrate → vẫn inline (Phase 2 sẽ fix)
```

## Rollback

```bash
git revert <commit-sha>
```

## Lưu Ý Quan Trọng

- Vì đây là **token-level change**, nó tác động lên TẤT CẢ component dùng `.btn-primary`/`.btn-secondary`. Phải visual sweep kỹ trước khi merge.
- Nếu có chỗ tự build button không qua `.btn-primary` (ví dụ raw `bg-primary-600` literal) thì **không bị ảnh hưởng** — sẽ xử lý ở Phase 1.
- `bg-primary-600` (cyan utility) vẫn còn dùng được ở các chỗ khác (ví dụ progress bar, badge active state) — chỉ là không phải button bg primary nữa.
