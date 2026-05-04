# Phase 5 — Admin Chart Palette + KPI Card Token

**Ưu tiên:** 🟡 P2
**Phụ thuộc:** Phase 3 (cần `--chart-1..5` token)
**Thời lượng ước tính:** 1.5 giờ

## Vấn Đề

Admin pages có 7 route (`admin/`, `admin/users`, `admin/logs`, `admin/traffic`, `admin/system`, `admin/llm`, `admin/langfuse`) nhưng:
- Chart sử dụng màu ad-hoc, mỗi page khác nhau.
- KPI card dùng `rounded-2xl` + custom shadow, lệch `.card` (`rounded-xl`).
- Một số page có hero gradient đúng brand, một số thì không.
- 7 raw color matches ở `admin/llm/page.tsx`, 4 ở `admin/langfuse`, 3 ở `admin/users`.

## Files Cần Touch

- `frontend/components/admin/KpiCard.tsx` (nếu tồn tại)
- `frontend/components/admin/KpiGroup.tsx` (nếu tồn tại)
- `frontend/components/admin/ChartCard.tsx` (nếu tồn tại)
- `frontend/app/admin/page.tsx`
- `frontend/app/admin/users/page.tsx`
- `frontend/app/admin/logs/page.tsx`
- `frontend/app/admin/traffic/page.tsx`
- `frontend/app/admin/system/page.tsx`
- `frontend/app/admin/llm/page.tsx`
- `frontend/app/admin/langfuse/page.tsx`
- `frontend/lib/admin/chart-theme.ts` *(mới — central palette)*
- `frontend/tests/unit/admin/chart-theme.test.tsx` *(mới)*

## Implementation

### Step 1 — Inspect Trước

Liệt kê admin component hiện có:

```bash
find frontend/components/admin -name "*.tsx"
find frontend/app/admin -name "page.tsx"
grep -rn "Chart\|Recharts\|d3\|nivo" frontend/app/admin frontend/components/admin
```

Identify thư viện chart đang dùng (Recharts? Tremor? Custom?). Cập nhật phase này theo thực tế.

### Step 2 — Central Chart Palette

Tạo `frontend/lib/admin/chart-theme.ts`:

```ts
// Single source of truth cho mọi chart color trong admin
export const CHART_PALETTE = {
  primary:    "var(--chart-1)",  // cyan brand
  secondary:  "var(--chart-2)",  // indigo
  tertiary:   "var(--chart-3)",  // teal
  quaternary: "var(--chart-4)",  // amber
  quinary:    "var(--chart-5)",  // pink
} as const;

export const CHART_SERIES = [
  CHART_PALETTE.primary,
  CHART_PALETTE.secondary,
  CHART_PALETTE.tertiary,
  CHART_PALETTE.quaternary,
  CHART_PALETTE.quinary,
];

// Status colors cho chart (success/error/warning trends)
export const CHART_STATUS = {
  success: "var(--state-success-fg)",
  error:   "var(--state-error-fg)",
  warning: "var(--state-warning-fg)",
  neutral: "var(--text-muted-2)",
};

export const CHART_GRID = {
  stroke: "var(--border-subtle)",
  background: "var(--surface-card)",
};
```

### Step 3 — KPI Card Đồng Bộ

```tsx
// Nếu KpiCard custom shadow, gộp về .card
// Before
<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-md">

// After
<div className="card">
```

Nếu KPI cần variant "highlighted" (số nổi bật), thêm:
```css
.card-kpi {
  @apply card;
}
.card-kpi[data-variant="accent"] {
  background: var(--surface-accent-soft);
  border-color: var(--brand-accent);
}
```

### Step 4 — Migrate Mỗi Admin Page

Mỗi page:
1. Import `CHART_SERIES`, `CHART_STATUS` từ `@/lib/admin/chart-theme`.
2. Thay thế hex hoặc raw color trong props chart.
3. Thay thế card wrapper raw → `.card`.
4. Hero header: nếu có, dùng gradient `from-indigo-600 via-cyan-500 to-teal-400` (đã chuẩn).
5. Filter / button → `.btn-primary` / `.btn-secondary`.

## Scope

**Không động:**
- Data fetching, mutation, query keys
- Endpoint của admin API
- Permission / role check

**Chỉ động:** chart color props, card className, button className.

## DoD Checklist

- [ ] `lib/admin/chart-theme.ts` export `CHART_PALETTE`, `CHART_SERIES`, `CHART_STATUS`, `CHART_GRID`
- [ ] 7 admin page import từ `chart-theme.ts`, không còn hex literal trong chart props
- [ ] KPI card dùng `.card` hoặc `.card-kpi`
- [ ] Hero gradient nhất quán (nếu page có hero)
- [ ] Type check pass
- [ ] Existing admin tests (nếu có) vẫn pass
- [ ] Token contract test mới pass
- [ ] Visual smoke: `/admin`, `/admin/users`, `/admin/logs`, `/admin/traffic`, `/admin/system`, `/admin/llm`, `/admin/langfuse` light + dark
- [ ] Chart legend màu khớp giữa các page (vd: cyan = "Total users" ở mọi page nói về user)
- [ ] Commit: `design(sync-ui): unify admin chart palette and KPI card`

## Unit Tests

### `frontend/tests/unit/admin/chart-theme.test.tsx`

```tsx
import { describe, expect, it } from "vitest";
import { CHART_PALETTE, CHART_SERIES, CHART_STATUS } from "@/lib/admin/chart-theme";

describe("Admin chart theme contract", () => {
  it("palette uses CSS variables, not raw hex", () => {
    Object.values(CHART_PALETTE).forEach((c) => {
      expect(c).toMatch(/^var\(--chart-/);
    });
  });

  it("status colors use state-* tokens", () => {
    expect(CHART_STATUS.success).toMatch(/var\(--state-success/);
    expect(CHART_STATUS.error).toMatch(/var\(--state-error/);
    expect(CHART_STATUS.warning).toMatch(/var\(--state-warning/);
  });

  it("series has at least 5 distinct entries", () => {
    expect(new Set(CHART_SERIES).size).toBeGreaterThanOrEqual(5);
  });
});
```

### Per-page guards (optional)

Snapshot test render 1 chart trên admin page, assert chart series receives `var(--chart-*)` value (không phải hex).

## Verify

```bash
cd frontend
npm run type-check
npm test -- --run frontend/tests/unit/admin/chart-theme.test.tsx

# Grep guard: không hex trong chart props
grep -rn -E '"#[0-9a-fA-F]{6}"' frontend/app/admin/ frontend/components/admin/
# Expected: chỉ còn hex trong file chart-theme nguồn (nếu có), 0 ở page

npm run build
npm run dev
# Manual: mở 7 admin page, switch dark mode, kiểm tra chart legend đồng bộ
```

## Rollback

```bash
git revert <commit-sha>
```
