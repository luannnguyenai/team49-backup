# Phase 0 — Extract shared course-display helpers

## Task duy nhất

Trích các helper liên quan đến hiển thị tên/code course từ `RoadmapPlanner.tsx` ra một module dùng chung để Phase 2 (`JourneyStrip`) và Phase 1 (`ContinueLearningHero`) tái sử dụng. **Pure refactor, no behavior change.**

## Files cần touch

| File | Action |
|------|--------|
| `frontend/features/learning-path/lib/course-display.ts` | **New** — chứa `slugify`, `isUuidLike`, `courseCodeFromTitle`, `cleanCourseTitle`, `courseDisplay` |
| `frontend/features/learning-path/components/RoadmapPlanner.tsx` | Edit — xóa các function nội bộ tương ứng, import từ `lib/course-display` |
| `frontend/features/learning-path/lib/__tests__/course-display.test.ts` | **New** — unit tests |

Không đụng file khác.

## API export (lib/course-display.ts)

```ts
export function slugify(value: string): string;
export function isUuidLike(value: string | null | undefined): boolean;
export function courseCodeFromTitle(title: string): string | null;
export function cleanCourseTitle(title: string): string;
export interface CourseDisplay { code: string | null; title: string }
export function courseDisplay(input: { title: string; courseId: string | null }): CourseDisplay;
```

> Lưu ý: chữ ký `courseDisplay` đổi nhẹ — nhận `{ title, courseId }` thay vì `CourseGroup` để dùng được cho cả hero (chỉ có `PathItemResponse`). Trong `RoadmapPlanner.tsx` adapt tại call site.

## DoD checklist

- [ ] Tạo `lib/course-display.ts` với 5 export trên, không phụ thuộc React.
- [ ] Logic giữ nguyên 1:1 với code hiện tại trong `RoadmapPlanner.tsx` (lines liên quan: `slugify`, `isUuidLike`, `courseCodeFromTitle`, `cleanCourseTitle`, `courseDisplay`).
- [ ] `RoadmapPlanner.tsx` import từ `lib/course-display` thay vì định nghĩa nội bộ.
- [ ] `npm run typecheck` (hoặc `tsc --noEmit`) pass.
- [ ] `npm run lint` pass cho 2 file đã đổi.
- [ ] Render trang `/learn` thủ công: tên course, code badge hiển thị y hệt trước refactor.
- [ ] Không thay đổi snapshot test khác (nếu có).

## Unit tests (`__tests__/course-display.test.ts`)

Dùng vitest hoặc jest theo convention frontend hiện tại — verify trước khi viết.

```ts
describe("slugify", () => {
  it("lowercases and removes diacritics", () => expect(slugify("Học Máy")).toBe("hoc-may"));
  it("collapses non-alphanumeric to single dash", () => expect(slugify("CS  231 / N")).toBe("cs-231-n"));
  it("trims leading and trailing dashes", () => expect(slugify("--hello--")).toBe("hello"));
  it("returns 'group' for empty result", () => expect(slugify("---")).toBe("group"));
});

describe("isUuidLike", () => {
  it("matches v4-shaped UUID", () => expect(isUuidLike("550e8400-e29b-41d4-a716-446655440000")).toBe(true));
  it("rejects plain code", () => expect(isUuidLike("CS231N")).toBe(false));
  it("handles null/undefined", () => {
    expect(isUuidLike(null)).toBe(false);
    expect(isUuidLike(undefined)).toBe(false);
  });
});

describe("courseCodeFromTitle", () => {
  it("extracts code prefix", () => expect(courseCodeFromTitle("CS231N: Deep Learning")).toBe("CS231N"));
  it("returns null when no prefix", () => expect(courseCodeFromTitle("Intro to AI")).toBeNull());
  it("supports trailing letter", () => expect(courseCodeFromTitle("CS50x: Title")).toBe("CS50x"));
});

describe("cleanCourseTitle", () => {
  it("strips code prefix", () => expect(cleanCourseTitle("CS231N: Deep Learning for Vision")).toBe("Vision"));
  it("strips 'Deep Learning for ' prefix", () => expect(cleanCourseTitle("Deep Learning for NLP")).toBe("NLP"));
  it("returns original when no match", () => expect(cleanCourseTitle("Linear Algebra")).toBe("Linear Algebra"));
});

describe("courseDisplay", () => {
  it("prefers code from title over courseId", () => {
    expect(courseDisplay({ title: "CS231N: Vision", courseId: "abc-123" }))
      .toEqual({ code: "CS231N", title: "Vision" });
  });
  it("falls back to non-uuid courseId", () => {
    expect(courseDisplay({ title: "Vision", courseId: "CS231N" }))
      .toEqual({ code: "CS231N", title: "Vision" });
  });
  it("ignores uuid-like courseId", () => {
    expect(courseDisplay({ title: "Vision", courseId: "550e8400-e29b-41d4-a716-446655440000" }))
      .toEqual({ code: null, title: "Vision" });
  });
});
```

Run: `npm run test -- course-display` (hoặc lệnh tương đương theo `package.json` của frontend).
