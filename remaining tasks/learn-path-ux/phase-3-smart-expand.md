# Phase 3 — Smart default expand + slim done courses

## Task duy nhất

Trong `RoadmapPlanner.tsx`, thay default behavior:

1. **Auto-expand** lecture chứa `recommendedNextId` lúc mount; các lecture khác đóng.
2. **Slim done courses**: course đã 100% done → render header thu gọn (1 dòng, ✓), KHÔNG map lectures.
3. Toggle thủ công của user vẫn giữ nguyên qua re-render.
4. Khi `recommendedNextId` thay đổi (do progress update từ store) → add lecture mới vào set expanded mà không reset cái user đang mở.

Không phụ thuộc các phase khác.

## Files cần touch

| File | Action |
|------|--------|
| `frontend/features/learning-path/components/RoadmapPlanner.tsx` | Edit — đổi `useState` initializer + `useEffect` khi `recommendedNextId` đổi + branch slim cho done course |
| `frontend/features/learning-path/components/__tests__/RoadmapPlanner.test.tsx` | **New** hoặc Edit (nếu đã có) |

## Implementation outline

```tsx
const recommendedNextId = useMemo(() => computeRecommendedNext(items), [items]);

const recommendedLectureKey = useMemo(() => {
  if (!recommendedNextId) return null;
  for (const course of groupedCourses) {
    for (const lecture of course.lectures) {
      if (lecture.items.some((i) => i.id === recommendedNextId)) return lecture.key;
    }
  }
  return null;
}, [groupedCourses, recommendedNextId]);

const [expandedLectureKeys, setExpandedLectureKeys] = useState<Set<string>>(
  () => (recommendedLectureKey ? new Set([recommendedLectureKey]) : new Set()),
);

useEffect(() => {
  if (!recommendedLectureKey) return;
  setExpandedLectureKeys((curr) => {
    if (curr.has(recommendedLectureKey)) return curr;
    const next = new Set(curr);
    next.add(recommendedLectureKey);
    return next;
  });
}, [recommendedLectureKey]);
```

Slim done course (trong vòng map `groupedCourses`):

```tsx
const isAllDone = course.items.every(isDoneForPlannerProgress);
if (isAllDone) {
  return <SlimCourseHeader key={course.key} course={course} />; // 1 dòng + CheckCircle
}
```

`SlimCourseHeader` là một sub-component nội bộ, click → expand lại (set state để override, hoặc nhấn để scroll xem chi tiết) — phase này chỉ cần render thu gọn, click handler có thể là no-op + tooltip "Course complete".

## DoD checklist

- [ ] Mount lần đầu: lecture chứa next-up auto-expand, các lecture khác đóng (verify thủ công + test).
- [ ] User collapse lecture đang auto-expand → state respect, không bị mở lại trừ khi `recommendedNextId` đổi sang lecture đó (giữ behavior cũ là OK).
- [ ] User expand lecture khác → state cộng dồn, không bị reset khi store update items.
- [ ] Course 100% done → render thu gọn, không có ChevronDown, không có grid units.
- [ ] Course 0% và không phải current course → vẫn render đầy đủ (collapsed lectures) — KHÔNG slim 0%.
- [ ] Khi `recommendedNextId` đổi (do `updateStatus`) → lecture mới được auto-add vào set, lecture cũ user mở vẫn giữ.
- [ ] Không regression visual cho course đang học (giữ pixel-equivalent với current state khi `expandedLectureKeys` bằng `{recommendedLectureKey}`).
- [ ] `npm run typecheck` + `npm run lint` pass.

## Unit tests (`__tests__/RoadmapPlanner.test.tsx`)

```ts
const recommendedItem = makeItem({ id: "u-rec", section_title: "Lecture 3" });
const otherItem = makeItem({ id: "u-other", section_title: "Lecture 1" });
const items = [otherItem, recommendedItem];

describe("RoadmapPlanner default expand", () => {
  it("auto-expands the lecture containing the recommended next item", () => {
    render(<RoadmapPlanner items={items} />);
    expect(screen.getByRole("region", { name: /Lecture 3/ })).toBeVisible();
    expect(screen.queryByText(otherItem.learning_unit_title)).not.toBeVisible();
  });

  it("preserves user-expanded lectures when items prop updates", async () => {
    const { rerender } = render(<RoadmapPlanner items={items} />);
    await userEvent.click(screen.getByRole("button", { name: /Lecture 1/ }));
    expect(screen.getByText(otherItem.learning_unit_title)).toBeVisible();
    rerender(<RoadmapPlanner items={[...items]} />); // shallow change
    expect(screen.getByText(otherItem.learning_unit_title)).toBeVisible();
  });

  it("adds new recommended lecture without collapsing existing", async () => {
    const { rerender } = render(<RoadmapPlanner items={items} />);
    await userEvent.click(screen.getByRole("button", { name: /Lecture 1/ }));
    const updated = items.map((i) => (i.id === "u-rec" ? { ...i, status: "completed" } : i));
    // assume next recommended now lives in a different lecture
    rerender(<RoadmapPlanner items={updated} />);
    expect(screen.getByText(otherItem.learning_unit_title)).toBeVisible();
  });
});

describe("RoadmapPlanner slim done courses", () => {
  it("renders done course in compact form", () => {
    const done = [
      makeItem({ id: "a", course_id: "c1", course_title: "Calc", status: "completed" }),
      makeItem({ id: "b", course_id: "c1", course_title: "Calc", status: "completed" }),
    ];
    render(<RoadmapPlanner items={done} />);
    expect(screen.getByText("Calc")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Lecture/ })).not.toBeInTheDocument();
  });

  it("does NOT slim a 0% course that is not active", () => {
    const items = [
      makeItem({ id: "a", course_id: "c1", course_title: "Active", status: "in_progress" }),
      makeItem({ id: "b", course_id: "c2", course_title: "Future", status: "not_started" }),
    ];
    render(<RoadmapPlanner items={items} />);
    expect(screen.getAllByText(/Lecture/).length).toBeGreaterThan(0);
  });
});
```

Run: `npm run test -- RoadmapPlanner`.
