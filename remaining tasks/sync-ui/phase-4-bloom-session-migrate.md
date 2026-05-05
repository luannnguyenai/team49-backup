# Phase 4 — Migrate Pages Sang Decorative Token

**Ưu tiên:** 🟡 P2
**Phụ thuộc:** **Bắt buộc** Phase 3 (token đã wire)
**Thời lượng ước tính:** 2.5–3 giờ

## Vấn Đề

Sau Phase 3, token decorative đã sẵn nhưng các page vẫn dùng raw color / hex. Phase 4 migrate.

| File | Raw color hiện tại | Đổi sang |
|---|---|---|
| `frontend/app/(protected)/history/page.tsx` | `TYPE_COLORS` raw, `BLOOM_BAR_COLOR` hex, `bg-blue-50` explanation, stat icons | session token + bloom token + insight-card + stat token |
| `frontend/app/assessment/page.tsx` | `BLOOM_BADGE` (sky/violet/amber/rose) | bloom token |
| `frontend/app/(protected)/profile/page.tsx` | achievement `border-blue-400 bg-blue-50` x4 | tier token |
| `frontend/app/(protected)/dashboard/page.tsx` | StatCard `text-blue-600 text-emerald-600 text-violet-600` | giữ multi-hue qua **stat token mới** hoặc gộp về `text-primary-600` (DECISION POINT) |
| `frontend/app/quiz/[learningUnitId]/page.tsx` | `bg-emerald-600`, `bg-red-50`, hint card raw | `.btn-primary`, state-success/error, insight-card |
| `frontend/app/module-test/[sectionId]/page.tsx` | tương tự quiz | tương tự |
| `frontend/app/learning-path/page.tsx` | `bg-cyan-50 border-cyan-200` | `bg-surface-accent-soft border-primary-200` |

## Decision Point Trước Khi Migrate

**Stat icon palette (dashboard, profile, history):** giữ multi-hue (Courses=blue, Time=violet, Progress=emerald, Completed=amber) hay đồng nhất 1 màu?

- **Option A — Giữ multi-hue:** thêm token `--stat-courses`, `--stat-time`, `--stat-progress`, `--stat-completed` ở Phase 3 (xem Bảng 4 trong README plan tổng) → có visual differentiation rõ ràng.
- **Option B — Gộp:** dùng `bg-surface-accent-soft text-primary-600` cho tất cả → đồng bộ tuyệt đối nhưng mất visual cue.

**Khuyến nghị:** Option A — multi-hue có giá trị trải nghiệm. Nếu chọn Option A, **bổ sung vào Phase 3** trước khi Phase 4 migrate.

## Files Cần Touch

- `frontend/app/(protected)/history/page.tsx`
- `frontend/app/assessment/page.tsx`
- `frontend/app/(protected)/profile/page.tsx`
- `frontend/app/(protected)/dashboard/page.tsx`
- `frontend/app/quiz/[learningUnitId]/page.tsx`
- `frontend/app/quiz/[learningUnitId]/results/page.tsx`
- `frontend/app/module-test/[sectionId]/page.tsx`
- `frontend/app/module-test/[sectionId]/results/page.tsx`
- `frontend/app/learning-path/page.tsx`
- Tests: thêm assertions vào file tests đã có

## Mapping Cụ Thể

### History `TYPE_COLORS`

```ts
// Before
const TYPE_COLORS: Record<SessionType, string> = {
  assessment:  "bg-violet-100 text-violet-700",
  quiz:        "bg-blue-100 text-blue-700",
  module_test: "bg-amber-100 text-amber-700",
  practice:    "bg-slate-100 text-slate-600",
};

// After
const TYPE_COLORS: Record<SessionType, string> = {
  assessment:  "bg-session-assessment-soft text-session-assessment",
  quiz:        "bg-session-quiz-soft text-session-quiz",
  module_test: "bg-session-module-test-soft text-session-module-test",
  practice:    "bg-session-practice-soft text-session-practice",
};
```

### History `BLOOM_BAR_COLOR`

```ts
// Before
const BLOOM_BAR_COLOR: Record<string, string> = {
  remember:   "#38bdf8",
  understand: "#a78bfa",
  apply:      "#fbbf24",
  analyze:    "#f87171",
};

// After
const BLOOM_BAR_COLOR: Record<string, string> = {
  remember:   "var(--bloom-remember)",
  understand: "var(--bloom-understand)",
  apply:      "var(--bloom-apply)",
  analyze:    "var(--bloom-analyze)",
};
```

### Assessment `BLOOM_BADGE`

```ts
// Before
const BLOOM_BADGE: Record<string, { label: string; color: string }> = {
  remember:   { label: "Remember",   color: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300" },
  understand: { label: "Understand", color: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300" },
  apply:      { label: "Apply",      color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" },
  analyze:    { label: "Analyze",    color: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300" },
};

// After
const BLOOM_BADGE: Record<string, { label: string; color: string }> = {
  remember:   { label: "Remember",   color: "bg-bloom-remember-soft text-bloom-remember" },
  understand: { label: "Understand", color: "bg-bloom-understand-soft text-bloom-understand" },
  apply:      { label: "Apply",      color: "bg-bloom-apply-soft text-bloom-apply" },
  analyze:    { label: "Analyze",    color: "bg-bloom-analyze-soft text-bloom-analyze" },
};
```

### Profile Achievement Badges

```ts
// Before
const ACHIEVEMENTS = [
  { title: "Skill profile unlocked", color: "border-blue-400 bg-blue-50 dark:bg-blue-900/20" },
  { title: "First learning session", color: "border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20" },
  { title: "Consistent learner",     color: "border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20" },
  { title: "Persistent",             color: "border-violet-400 bg-violet-50 dark:bg-violet-900/20" },
];

// After — quyết định mapping tier:
const ACHIEVEMENTS = [
  { title: "Skill profile unlocked", color: "border-tier-bronze bg-tier-bronze-soft" },
  { title: "First learning session", color: "border-tier-silver bg-tier-silver-soft" },
  { title: "Consistent learner",     color: "border-tier-gold bg-tier-gold-soft" },
  { title: "Persistent",             color: "border-tier-platinum bg-tier-platinum-soft" },
];
```

### Insight / Hint Cards

```tsx
// Before (history)
<div className="flex items-start gap-2 rounded-lg bg-blue-50 px-3 py-2 dark:bg-blue-900/20">
  <Lightbulb size={13} className="mt-0.5 shrink-0 text-blue-500" />
  <div className="text-xs leading-relaxed text-blue-800 dark:text-blue-200">
    <MarkdownRenderer text={q.explanation_text} />
  </div>
</div>

// After
<div className="insight-card flex items-start gap-2">
  <Lightbulb size={13} className="mt-0.5 shrink-0 text-insight" />
  <div className="text-xs leading-relaxed text-insight">
    <MarkdownRenderer text={q.explanation_text} />
  </div>
</div>
```

### Quiz / Module-test State

```tsx
// Before
<div className="rounded-lg bg-red-50 border border-red-300 p-3 text-red-800">
  Sai rồi
</div>

// After
<div className="state-error rounded-lg border p-3">
  Sai rồi
</div>
```

### Learning Path

```tsx
// Before
<div className="rounded-lg bg-cyan-50 border border-cyan-200 p-4">

// After
<div className="rounded-lg bg-surface-accent-soft border border-primary-200 p-4">
```

## Scope

**Không động:**
- Logic fetch / state / sort / filter / pagination
- Schema response từ API
- Test behavior hiện có (chỉ thêm assertion về class)

**Chỉ migrate:** className strings + hex constants ở record/map.

## DoD Checklist

### History
- [ ] `TYPE_COLORS` dùng `bg-session-*`
- [ ] `BLOOM_BAR_COLOR` dùng `var(--bloom-*)`
- [ ] Explanation card dùng `.insight-card`
- [ ] StatCard icons dùng stat token (nếu chọn Option A) hoặc gộp về primary
- [ ] 0 raw color literal trong `.tsx` (`grep -E 'bg-(blue|violet|amber|rose|emerald|sky|red|yellow)-' frontend/app/\(protected\)/history/page.tsx` → empty)

### Assessment
- [ ] `BLOOM_BADGE` dùng `bg-bloom-*-soft text-bloom-*`
- [ ] 0 raw `bg-sky-* bg-violet-* bg-amber-* bg-rose-*`

### Profile
- [ ] Achievement dùng `border-tier-* bg-tier-*-soft`
- [ ] StatRow icons dùng stat token / primary

### Dashboard
- [ ] StatCard icons theo decision (Option A/B)

### Quiz / Module-test
- [ ] Action button dùng `.btn-primary`
- [ ] Error/success/warning panel dùng `.state-error/.state-success/.state-warning`
- [ ] Hint/explanation dùng `.insight-card`

### Learning Path
- [ ] Bỏ `bg-cyan-50 border-cyan-200`

### Global
- [ ] Type check pass
- [ ] All existing tests pass (history presenters, assessment presenters, dashboard presenters, quiz, module-test)
- [ ] Token contract assertions thêm vào test file phù hợp pass
- [ ] Visual smoke light + dark trên: history, assessment, profile, dashboard, quiz/sample, module-test/sample, learning-path
- [ ] Commit: `design(sync-ui): migrate decorative palette to semantic tokens`

## Unit Tests Bổ Sung

Thêm assertions vào tests hiện có:

### `frontend/tests/unit/history/type-colors.test.tsx` *(mới)*
```tsx
import { TYPE_COLORS } from "@/app/(protected)/history/page";
import { describe, expect, it } from "vitest";

describe("History TYPE_COLORS contract", () => {
  it("uses session-* tokens, not raw tailwind", () => {
    Object.values(TYPE_COLORS).forEach((cls) => {
      expect(cls).toMatch(/session-/);
      expect(cls).not.toMatch(/bg-(violet|blue|amber)-100/);
    });
  });
});
```

> **Note:** Cần export `TYPE_COLORS`, `BLOOM_BAR_COLOR`, `BLOOM_BADGE`, `ACHIEVEMENTS` từ page để test được. Nếu không export được, viết snapshot test render rồi assert class string.

### `frontend/tests/unit/assessment/bloom-badge.test.tsx` *(mới)*
```tsx
describe("BLOOM_BADGE contract", () => {
  it("all bloom levels use bloom-* tokens", () => {
    Object.values(BLOOM_BADGE).forEach(({ color }) => {
      expect(color).toMatch(/bloom-/);
    });
  });
});
```

### `frontend/tests/unit/profile/achievement-tier.test.tsx` *(mới)*
```tsx
describe("Profile achievement tier contract", () => {
  it("all achievement tiers use tier-* tokens", () => {
    ACHIEVEMENTS.forEach(({ color }) => {
      expect(color).toMatch(/tier-/);
    });
  });
});
```

## Verify

```bash
cd frontend
npm run type-check

# Run all migrated-page tests
npm test -- --run frontend/tests/unit/history \
  frontend/tests/unit/assessment \
  frontend/tests/unit/profile \
  frontend/tests/unit/dashboard \
  frontend/tests/unit/tokens

# Grep guard: no raw multi-hue tailwind in migrated pages
grep -rn -E 'bg-(blue|violet|amber|rose|sky|red|yellow|emerald|cyan)-(50|100|200|300|400|500|600|700|800|900)' \
  frontend/app/\(protected\)/ \
  frontend/app/assessment/ \
  frontend/app/quiz/ \
  frontend/app/module-test/ \
  frontend/app/learning-path/
# Expected: chỉ còn các trường hợp có chủ đích (hero gradient hex hoặc hardcoded inline cần thiết)

npm run build
npm run dev
# Visual sweep — trang nào trang nấy
```

## Rollback

```bash
git revert <commit-sha>
```

> Phase 4 không động backend → revert an toàn.
