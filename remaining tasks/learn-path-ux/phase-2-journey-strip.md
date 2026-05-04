# Phase 2 — Journey strip (bird's-eye các course)

## Task duy nhất

Tạo component `JourneyStrip` đặt trên đầu `RoadmapCanvas`: 1 hàng ngang chip cho mỗi course với progress %, trạng thái current/done/upcoming. Click chip → smooth-scroll đến `<section>` tương ứng trong `RoadmapPlanner`.

**Phụ thuộc Phase 0** (dùng `courseDisplay` từ `lib/course-display.ts`).

## Files cần touch

| File | Action |
|------|--------|
| `frontend/features/learning-path/components/JourneyStrip.tsx` | **New** |
| `frontend/features/learning-path/components/RoadmapCanvas.tsx` | Edit — render `<JourneyStrip />` trước `<RoadmapPlanner />` |
| `frontend/features/learning-path/components/RoadmapPlanner.tsx` | Edit — thêm `id={`course-${course.key}`}` cho `<section>` để scroll target |
| `frontend/features/learning-path/components/__tests__/JourneyStrip.test.tsx` | **New** |

## Behavior

- Đọc `items` từ store, group theo course (dùng helper `groupItemsByCourseAndLecture` → tách ra `lib/group-by-course.ts` nếu cần share, hoặc tạo helper nội bộ trong component này gọi pure function).
- Mỗi chip hiển thị:
  - Code badge (nếu có) — small.
  - Tên course (đã clean) — truncate ở 1 dòng.
  - Progress bar mảnh + `% done`.
  - Status: `done` (✓ + opacity 60), `current` (highlight border + ring), `upcoming` (default).
  - Course "current" = course đầu tiên có ít nhất 1 item `not_started` hoặc `in_progress`. Logic: tìm course chứa `recommendedNextId`.
- Click chip → `document.getElementById(\`course-\${course.key}\`)?.scrollIntoView({ behavior: "smooth", block: "start" })`.
- Sticky: `sticky top-0 z-20` với background `var(--bg-card)` + shadow nhẹ khi scroll qua hero.
- Khi chỉ có 1 course → **không render** strip (return `null`).
- Horizontal scroll khi N course nhiều: `overflow-x-auto`, mỗi chip `flex-shrink-0`.

## DoD checklist

- [ ] Strip render đúng số chip = số course từ `groupItemsByCourseAndLecture(items).length`.
- [ ] `% done` của mỗi chip khớp với header `% done` trong `RoadmapPlanner` (cùng `countCompleted` / `totalUnits`).
- [ ] Click chip → trang scroll smooth đến đúng course section (test thủ công).
- [ ] Khi chỉ có 1 course → strip không render.
- [ ] Sticky hoạt động đúng khi scroll dọc.
- [ ] Course chứa "next up" có style `current` rõ ràng.
- [ ] Course đã 100% done có opacity giảm + icon ✓.
- [ ] Strip chỉ render trong view `graph` (không hiện ở timeline) — vì mounted trong `RoadmapCanvas`.
- [ ] `npm run typecheck` + `npm run lint` pass.

## Unit tests (`__tests__/JourneyStrip.test.tsx`)

```ts
const items = [
  makeItem({ id: "a1", course_id: "c1", course_title: "CS231N: Vision", status: "completed" }),
  makeItem({ id: "a2", course_id: "c1", course_title: "CS231N: Vision", status: "completed" }),
  makeItem({ id: "b1", course_id: "c2", course_title: "CS224N: NLP", status: "in_progress" }),
  makeItem({ id: "b2", course_id: "c2", course_title: "CS224N: NLP", status: "not_started" }),
  makeItem({ id: "c1", course_id: "c3", course_title: "Intro to RL", status: "not_started" }),
];

describe("JourneyStrip", () => {
  it("renders one chip per course", () => {
    mockStore({ items });
    render(<JourneyStrip />);
    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("computes correct progress per chip", () => {
    mockStore({ items });
    render(<JourneyStrip />);
    expect(screen.getByText("100%")).toBeInTheDocument(); // c1
    expect(screen.getByText("0%")).toBeInTheDocument();   // c2 in progress but no completed
  });

  it("marks course containing recommendedNext as current", () => {
    mockStore({ items });
    render(<JourneyStrip />);
    const currentChip = screen.getByRole("button", { name: /CS224N/ });
    expect(currentChip).toHaveAttribute("data-state", "current");
  });

  it("marks 100% completed course as done", () => {
    mockStore({ items });
    render(<JourneyStrip />);
    const doneChip = screen.getByRole("button", { name: /CS231N/ });
    expect(doneChip).toHaveAttribute("data-state", "done");
  });

  it("scrolls section into view on click", async () => {
    mockStore({ items });
    const section = document.createElement("section");
    section.id = "course-c2";
    section.scrollIntoView = vi.fn();
    document.body.appendChild(section);
    render(<JourneyStrip />);
    await userEvent.click(screen.getByRole("button", { name: /CS224N/ }));
    expect(section.scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
  });

  it("returns null when only one course", () => {
    mockStore({ items: items.filter((i) => i.course_id === "c1") });
    const { container } = render(<JourneyStrip />);
    expect(container.firstChild).toBeNull();
  });
});
```

Run: `npm run test -- JourneyStrip`.
