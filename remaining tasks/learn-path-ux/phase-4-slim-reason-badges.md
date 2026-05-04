# Phase 4 — Giảm noise của reason badges

## Task duy nhất

Trong `UnitCard` (hiện ở `RoadmapPlanner.tsx`):

- Thay vì `slice(0, 4)` reason badges trên mỗi card → chỉ render **1 badge ưu tiên cao nhất**.
- Ưu tiên: `critical_kp` > `required_prerequisite` > `quiz_available` > `high_salience` > `quick_review` > `skip_by_mastery` > `reference_only` > (none).
- Card không-recommended và priority badge là `reference_only`/`skip_by_mastery` → ẩn hoàn toàn (giảm 70% visual weight).
- Đẩy danh sách đầy đủ reason codes vào `LearningUnitDrawer` dưới mục **"Why this is suggested"**.

Không phụ thuộc các phase khác.

## Files cần touch

| File | Action |
|------|--------|
| `frontend/features/learning-path/components/RoadmapPlanner.tsx` | Edit — thêm `pickPrimaryReason()` helper, sửa `UnitCard` render |
| `frontend/features/learning-path/components/LearningUnitDrawer.tsx` | Edit — thêm section render full reason codes (verify section đã có; nếu có rồi → đảm bảo render đầy đủ list, không slice) |
| `frontend/features/learning-path/lib/__tests__/pick-primary-reason.test.ts` | **New** |
| `frontend/features/learning-path/components/__tests__/UnitCard.test.tsx` | **New** hoặc Edit |

## Implementation outline

```ts
const REASON_PRIORITY: ReadonlyArray<string> = [
  "critical_kp",
  "required_prerequisite",
  "quiz_available",
  "high_salience",
  "quick_review",
  "skip_by_mastery",
  "reference_only",
];

export function pickPrimaryReason(codes: readonly string[] | null | undefined): string | null {
  if (!codes?.length) return null;
  const set = new Set(codes);
  for (const code of REASON_PRIORITY) {
    if (set.has(code)) return code;
  }
  return codes[0] ?? null;
}
```

Trong `UnitCard`:

```tsx
const primaryReason = pickPrimaryReason(item.reason_codes);
const showReasonBadge =
  primaryReason &&
  (isRecommended || !["reference_only", "skip_by_mastery"].includes(primaryReason));
```

Render: bỏ block `slice(0, 4).map(...)` — thay bằng 1 badge duy nhất khi `showReasonBadge`.

Quiz block riêng (`reason_codes.includes("quiz_available")`) hợp nhất vào logic chung — `quiz_available` đã có trong priority list ở vị trí #3.

## DoD checklist

- [ ] Helper `pickPrimaryReason` export từ `lib/` (hoặc inline trong `RoadmapPlanner.tsx` nếu chỉ dùng ở 1 chỗ — verify không có chỗ thứ 2 cần dùng).
- [ ] `UnitCard` render tối đa 1 reason badge.
- [ ] Card không-recommended với reason `reference_only` hoặc `skip_by_mastery` → KHÔNG hiện badge nào.
- [ ] Card recommended (`isRecommended=true`) → vẫn hiện badge dù priority thấp.
- [ ] `LearningUnitDrawer` render đầy đủ reason codes của unit hiện chọn (verify visual khi click 1 unit có nhiều reasons).
- [ ] Status icon, "Next up" badge, "Upcoming" badge, "Skip" badge, time badge — KHÔNG bị ảnh hưởng.
- [ ] Pixel snapshot diff hợp lý: chỉ giảm height/badges, không lỗi layout.
- [ ] `npm run typecheck` + `npm run lint` pass.

## Unit tests

### `lib/__tests__/pick-primary-reason.test.ts`

```ts
describe("pickPrimaryReason", () => {
  it("returns null for empty/null/undefined", () => {
    expect(pickPrimaryReason(null)).toBeNull();
    expect(pickPrimaryReason(undefined)).toBeNull();
    expect(pickPrimaryReason([])).toBeNull();
  });
  it("respects priority order", () => {
    expect(pickPrimaryReason(["high_salience", "critical_kp"])).toBe("critical_kp");
    expect(pickPrimaryReason(["reference_only", "quiz_available"])).toBe("quiz_available");
    expect(pickPrimaryReason(["quick_review", "high_salience"])).toBe("high_salience");
  });
  it("returns first code when none in priority list", () => {
    expect(pickPrimaryReason(["unknown_a", "unknown_b"])).toBe("unknown_a");
  });
});
```

### `components/__tests__/UnitCard.test.tsx`

```ts
describe("UnitCard reason badge", () => {
  it("renders only the highest-priority reason badge", () => {
    const item = makeItem({
      reason_codes: ["high_salience", "critical_kp", "quick_review"],
    });
    render(<UnitCard item={item} isRecommended={false} />);
    expect(screen.getByText(/critical/i)).toBeInTheDocument();
    expect(screen.queryByText(/high_salience|quick_review/i)).not.toBeInTheDocument();
  });

  it("hides reference_only badge on non-recommended card", () => {
    const item = makeItem({ reason_codes: ["reference_only"] });
    render(<UnitCard item={item} isRecommended={false} />);
    expect(screen.queryByText(/reference/i)).not.toBeInTheDocument();
  });

  it("shows reference_only badge when card is recommended", () => {
    const item = makeItem({ reason_codes: ["reference_only"] });
    render(<UnitCard item={item} isRecommended={true} />);
    expect(screen.getByText(/reference/i)).toBeInTheDocument();
  });

  it("renders no reason section when reason_codes empty", () => {
    const item = makeItem({ reason_codes: [] });
    const { container } = render(<UnitCard item={item} isRecommended={false} />);
    expect(container.querySelectorAll("[data-testid='reason-badge']")).toHaveLength(0);
  });
});
```

Run: `npm run test -- pick-primary-reason UnitCard`.
