# Phase 1 — Hero "Continue learning" card

## Task duy nhất

Tạo component `ContinueLearningHero` đặt ngay dưới `PlannerHeader` trong `LearningPathShell`, hiển thị **1 hành động duy nhất** (Resume / Start) cho unit được `computeRecommendedNext` trả về. Khi user đã hoàn thành tất cả → trạng thái "All caught up".

Không phụ thuộc Phase 0/2/3/4.

## Files cần touch

| File | Action |
|------|--------|
| `frontend/features/learning-path/components/ContinueLearningHero.tsx` | **New** |
| `frontend/features/learning-path/components/LearningPathShell.tsx` | Edit — mount `<ContinueLearningHero />` giữa `<ProfileChangeBanner />` và phần view content |
| `frontend/features/learning-path/components/__tests__/ContinueLearningHero.test.tsx` | **New** |

## Behavior

- Đọc state từ `useLearningPathStore`: `items`, `currentProgress`, `selectItem`.
- Tính `recommendedId = computeRecommendedNext(items)`. Tìm `item` tương ứng.
- Trường hợp **có recommended**: render card với
  - Breadcrumb nhỏ: `course title → section title`.
  - Tiêu đề: `learning_unit_title`.
  - Hàng meta: `formatDurationFromHours(estimated_hours)`, `PlayerInsightBadge` (nếu `currentProgress.learning_unit_id === item.learning_unit_id`).
  - 1 dòng "Why this next?": `describePlannerReason(item.reason_codes[0]).label` (nếu có).
  - 1 nút CTA chính: text `"Resume"` nếu insight hiển thị progress > 0, ngược lại `"Start"`. `onClick → selectItem(item.id)`.
- Trường hợp **không có recommended** (tất cả `completed` hoặc list rỗng): render trạng thái "All caught up" với mô tả ngắn + CTA phụ "Review previous units" (no-op cho phase này, chỉ scroll lên đầu danh sách).
- Loading state: nếu `loading === true` → render skeleton (1 khối).

## DoD checklist

- [ ] Component được render đúng vị trí trong `LearningPathShell` (ngay sau `<ProfileChangeBanner />`, trước `view === "graph" ? ... : ...`).
- [ ] Click "Resume/Start" gọi `selectItem(item.id)` → mở `LearningUnitDrawer` với đúng unit (verify thủ công trong browser).
- [ ] Không render khi `!profile` hoặc `items.length === 0` (early return ở `LearningPathShell` đã handle).
- [ ] Trạng thái "All caught up" hiển thị khi mọi item đều `status === "completed"`.
- [ ] Skeleton hiển thị khi `loading === true` cùng với CanvasSkeleton/TimelineSkeleton.
- [ ] Tailwind tokens dùng `var(--border)`, `var(--bg-card)`, `var(--text-secondary)`, `bg-primary-600` (đồng bộ với `LearningPathShell.tsx`).
- [ ] `npm run typecheck` pass.
- [ ] `npm run lint` pass.
- [ ] Visual check `/learn` ở 3 trạng thái: chưa start, đang học giữa chừng, hoàn thành tất cả.

## Unit tests (`__tests__/ContinueLearningHero.test.tsx`)

Dùng `@testing-library/react` + mock store theo convention của frontend (verify trước trong các test hiện có của learning-path).

```ts
const baseItem = {
  id: "u1",
  learning_unit_id: "lu1",
  learning_unit_title: "Vectors and matrices",
  course_title: "CS231N: Vision",
  section_title: "Lecture 1",
  status: "not_started",
  action: "do",
  estimated_hours: 0.5,
  segment_policy: "core",
  reason_codes: ["high_salience"],
  // ...other required fields with sane defaults
} as const;

describe("ContinueLearningHero", () => {
  it("renders recommended unit title and Start CTA when no progress", () => {
    mockStore({ items: [baseItem], currentProgress: null });
    render(<ContinueLearningHero />);
    expect(screen.getByText("Vectors and matrices")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start/i })).toBeInTheDocument();
  });

  it("renders Resume CTA when player has progress on the unit", () => {
    mockStore({
      items: [baseItem],
      currentProgress: { learning_unit_id: "lu1", watch_percent: 35, video_progress_s: 120 },
    });
    render(<ContinueLearningHero />);
    expect(screen.getByRole("button", { name: /resume/i })).toBeInTheDocument();
  });

  it("calls selectItem with item.id on CTA click", async () => {
    const selectItem = vi.fn();
    mockStore({ items: [baseItem], selectItem });
    render(<ContinueLearningHero />);
    await userEvent.click(screen.getByRole("button", { name: /start/i }));
    expect(selectItem).toHaveBeenCalledWith("u1");
  });

  it("renders 'All caught up' when every item is completed", () => {
    mockStore({ items: [{ ...baseItem, status: "completed" }] });
    render(<ContinueLearningHero />);
    expect(screen.getByText(/all caught up/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /start|resume/i })).not.toBeInTheDocument();
  });

  it("renders skeleton when loading", () => {
    mockStore({ items: [], loading: true });
    const { container } = render(<ContinueLearningHero />);
    expect(container.querySelector("[data-testid='hero-skeleton']")).toBeInTheDocument();
  });

  it("renders breadcrumb course → section", () => {
    mockStore({ items: [baseItem] });
    render(<ContinueLearningHero />);
    expect(screen.getByText(/CS231N/)).toBeInTheDocument();
    expect(screen.getByText(/Lecture 1/)).toBeInTheDocument();
  });
});
```

Run: `npm run test -- ContinueLearningHero`.
