# Phase 3 — Định Nghĩa Token Cho Decorative Palette

**Ưu tiên:** 🟠 P1
**Phụ thuộc:** Không (foundation phase, cho phép Phase 4 chạy)
**Thời lượng ước tính:** 1.5 giờ

## Vấn Đề

Phase 1 (`redesign.md`) chỉ tokenize **brand + neutral surface**. Các palette decorative còn dùng raw color hoặc hex hardcoded ở nhiều nơi:

| Concept | Hiện tại (raw) | Số file dùng | Drift |
|---|---|---|---|
| Bloom taxonomy | `#38bdf8 #a78bfa #fbbf24 #f87171` (history.tsx) + `bg-sky-100 bg-violet-100 bg-amber-100 bg-rose-100` (assessment.tsx) | 2 | ❌ 2 nguồn độc lập, không cùng hue |
| Session type | `bg-violet-100 bg-blue-100 bg-amber-100 bg-slate-100` | 1 (history) | ⚠️ |
| Achievement tier | `border-blue-400 border-emerald-400 border-yellow-400 border-violet-400` | 1 (profile) | ⚠️ |
| Stat icon | `text-blue-600 text-emerald-600 text-violet-600 text-amber-600` | 3 (dashboard, profile, history) | ⚠️ |
| Insight/Hint card | `bg-blue-50 text-blue-800` | 3+ (history, quiz, module-test) | ⚠️ |
| State (success/error/warning) | `bg-emerald-50/red-50/amber-50` | nhiều | ⚠️ |

**Phase 3 chỉ định nghĩa và wire token. KHÔNG migrate page** — migrate ở Phase 4.

## Files Cần Touch

- `frontend/app/globals.css`
- `frontend/tailwind.config.ts`
- `frontend/tests/unit/tokens/decorative-tokens.test.tsx` *(mới)*

## Token Mới Đề Xuất

### `globals.css` thêm vào `:root`

```css
:root {
  /* === Bloom taxonomy === */
  --bloom-remember:        #0ea5e9;   /* sky-500 */
  --bloom-remember-soft:   #e0f2fe;   /* sky-100 */
  --bloom-understand:      #8b5cf6;   /* violet-500 */
  --bloom-understand-soft: #ede9fe;   /* violet-100 */
  --bloom-apply:           #f59e0b;   /* amber-500 */
  --bloom-apply-soft:      #fef3c7;   /* amber-100 */
  --bloom-analyze:         #ef4444;   /* red-500 */
  --bloom-analyze-soft:    #fee2e2;   /* red-100 */
  --bloom-evaluate:        #ec4899;   /* pink-500 — dự phòng */
  --bloom-evaluate-soft:   #fce7f3;
  --bloom-create:          #14b8a6;   /* teal-500 — dự phòng */
  --bloom-create-soft:     #ccfbf1;

  /* === Session type === */
  --session-assessment:      #8b5cf6;
  --session-assessment-soft: #ede9fe;
  --session-quiz:            #3b82f6;
  --session-quiz-soft:       #dbeafe;
  --session-module-test:     #f59e0b;
  --session-module-test-soft:#fef3c7;
  --session-practice:        #64748b;
  --session-practice-soft:   #f1f5f9;

  /* === Achievement tier === */
  --tier-bronze:    #b45309;   /* amber-700 */
  --tier-bronze-soft:#fef3c7;
  --tier-silver:    #475569;   /* slate-600 */
  --tier-silver-soft:#f1f5f9;
  --tier-gold:      #ca8a04;   /* yellow-600 */
  --tier-gold-soft: #fef9c3;
  --tier-platinum:  #4f46e5;   /* indigo-600 — brand */
  --tier-platinum-soft:#e0e7ff;

  /* === Insight / Hint surface === */
  --insight-bg:     #ecfeff;   /* primary-50 (cyan-50) */
  --insight-fg:     #0e7490;   /* primary-700 */
  --insight-border: #a5f3fc;   /* primary-200 */

  /* === State surfaces === */
  --state-success-bg:     #ecfdf5;
  --state-success-fg:     #047857;
  --state-success-border: #6ee7b7;
  --state-error-bg:       #fef2f2;
  --state-error-fg:       #b91c1c;
  --state-error-border:   #fca5a5;
  --state-warning-bg:     #fffbeb;
  --state-warning-fg:     #b45309;
  --state-warning-border: #fcd34d;

  /* === Chart categorical (Phase 5) === */
  --chart-1: #0891b2;   /* primary-600 cyan */
  --chart-2: #4f46e5;   /* indigo-600 */
  --chart-3: #2dd4bf;   /* teal-400 */
  --chart-4: #f59e0b;   /* amber-500 */
  --chart-5: #ec4899;   /* pink-500 */
}
```

### `globals.css` thêm vào `.dark`

```css
.dark {
  /* Bloom — softs về tối hơn, fg sáng */
  --bloom-remember-soft:   rgba(14, 165, 233, 0.18);
  --bloom-understand-soft: rgba(139, 92, 246, 0.18);
  --bloom-apply-soft:      rgba(245, 158, 11, 0.18);
  --bloom-analyze-soft:    rgba(239, 68, 68, 0.18);
  /* … tương tự cho session/tier/state … */

  --insight-bg:     rgba(8, 145, 178, 0.14);
  --insight-fg:     #67e8f9;
  --insight-border: rgba(34, 211, 238, 0.34);

  --state-success-bg:     rgba(16, 185, 129, 0.16);
  --state-success-fg:     #6ee7b7;
  --state-error-bg:       rgba(239, 68, 68, 0.16);
  --state-error-fg:       #fca5a5;
  --state-warning-bg:     rgba(245, 158, 11, 0.16);
  --state-warning-fg:     #fcd34d;
}
```

### `tailwind.config.ts` thêm vào `theme.extend.colors`

```ts
colors: {
  // ... existing surface, text, primary, brand ...

  bloom: {
    remember:        "var(--bloom-remember)",
    "remember-soft": "var(--bloom-remember-soft)",
    understand:        "var(--bloom-understand)",
    "understand-soft": "var(--bloom-understand-soft)",
    apply:        "var(--bloom-apply)",
    "apply-soft": "var(--bloom-apply-soft)",
    analyze:        "var(--bloom-analyze)",
    "analyze-soft": "var(--bloom-analyze-soft)",
    evaluate:        "var(--bloom-evaluate)",
    "evaluate-soft": "var(--bloom-evaluate-soft)",
    create:        "var(--bloom-create)",
    "create-soft": "var(--bloom-create-soft)",
  },
  session: {
    assessment:        "var(--session-assessment)",
    "assessment-soft": "var(--session-assessment-soft)",
    quiz:        "var(--session-quiz)",
    "quiz-soft": "var(--session-quiz-soft)",
    "module-test":        "var(--session-module-test)",
    "module-test-soft":   "var(--session-module-test-soft)",
    practice:        "var(--session-practice)",
    "practice-soft": "var(--session-practice-soft)",
  },
  tier: {
    bronze:        "var(--tier-bronze)",
    "bronze-soft": "var(--tier-bronze-soft)",
    silver:        "var(--tier-silver)",
    "silver-soft": "var(--tier-silver-soft)",
    gold:        "var(--tier-gold)",
    "gold-soft": "var(--tier-gold-soft)",
    platinum:        "var(--tier-platinum)",
    "platinum-soft": "var(--tier-platinum-soft)",
  },
  insight: {
    DEFAULT: "var(--insight-fg)",
    soft:    "var(--insight-bg)",
    border:  "var(--insight-border)",
  },
  state: {
    "success-bg":     "var(--state-success-bg)",
    "success-fg":     "var(--state-success-fg)",
    "success-border": "var(--state-success-border)",
    "error-bg":     "var(--state-error-bg)",
    "error-fg":     "var(--state-error-fg)",
    "error-border": "var(--state-error-border)",
    "warning-bg":     "var(--state-warning-bg)",
    "warning-fg":     "var(--state-warning-fg)",
    "warning-border": "var(--state-warning-border)",
  },
  chart: {
    1: "var(--chart-1)",
    2: "var(--chart-2)",
    3: "var(--chart-3)",
    4: "var(--chart-4)",
    5: "var(--chart-5)",
  },
},
```

### Tiện Ích Hỗ Trợ (Optional)

```css
/* globals.css thêm component class */
.insight-card {
  @apply rounded-lg border px-3 py-2 text-sm;
  background: var(--insight-bg);
  color: var(--insight-fg);
  border-color: var(--insight-border);
}
.state-success { background: var(--state-success-bg); color: var(--state-success-fg); border-color: var(--state-success-border); }
.state-error   { background: var(--state-error-bg);   color: var(--state-error-fg);   border-color: var(--state-error-border); }
.state-warning { background: var(--state-warning-bg); color: var(--state-warning-fg); border-color: var(--state-warning-border); }
```

## DoD Checklist

- [ ] `globals.css` có đủ variable cho 6 nhóm: bloom, session, tier, insight, state, chart
- [ ] `.dark` có parity cho 6 nhóm
- [ ] `tailwind.config.ts` map đủ utility: `bg-bloom-{level}`, `bg-bloom-{level}-soft`, `text-bloom-{level}`, tương tự session/tier/insight/state/chart
- [ ] 3 helper class: `.insight-card`, `.state-success`, `.state-error`, `.state-warning` (optional)
- [ ] Type check pass
- [ ] Tailwind build OK (no unknown class errors)
- [ ] **Không có file page nào được sửa trong phase này** (chỉ token + config)
- [ ] Token contract test pass
- [ ] Commit: `design(sync-ui): add decorative semantic tokens for bloom/session/tier/insight/state/chart`

## Unit Tests

### `frontend/tests/unit/tokens/decorative-tokens.test.tsx`

```tsx
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("Decorative tokens are wired in Tailwind", () => {
  // Test bằng cách render 1 div và check class generated có style đúng
  it("bloom utilities resolve to CSS vars", () => {
    const { container } = render(
      <>
        <div data-testid="bloom-remember" className="bg-bloom-remember-soft text-bloom-remember" />
        <div data-testid="bloom-apply"    className="bg-bloom-apply-soft text-bloom-apply" />
      </>,
    );
    const remember = container.querySelector('[data-testid="bloom-remember"]')!;
    const apply    = container.querySelector('[data-testid="bloom-apply"]')!;
    expect(remember.className).toContain("bg-bloom-remember-soft");
    expect(apply.className).toContain("text-bloom-apply");
  });

  it("session, tier, insight, state utilities are accepted as classes", () => {
    const { container } = render(
      <>
        <div className="bg-session-quiz-soft text-session-quiz" />
        <div className="border-tier-gold bg-tier-gold-soft" />
        <div className="bg-insight-soft text-insight border-insight-border" />
        <div className="bg-state-success-bg text-state-success-fg" />
      </>,
    );
    expect(container.children.length).toBe(4);
  });
});
```

> **Note:** JSDOM không apply Tailwind compiled CSS, nên test chỉ assert class string. Test "thực sự áp đúng màu" cần Storybook visual hoặc Playwright screenshot (Phase 4 sẽ cover khi migrate page).

## Verify

```bash
cd frontend
npm run type-check
npm test -- --run frontend/tests/unit/tokens/decorative-tokens.test.tsx
npm run build  # Tailwind generate CSS không lỗi unknown utility
```

## Rollback

```bash
git revert <commit-sha>
```
