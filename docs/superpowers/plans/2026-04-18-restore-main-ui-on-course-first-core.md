# Restore Main UI On Course-First Core Implementation Plan

> **Historical plan:** This document is preserved for implementation history only. It predates the canonical runtime cutover; use `README.md` and `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md` as the active production contract.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the visual language from `main` across the current course-first flow without rolling back the refactored routing, gating, and presenter-driven behavior.

**Architecture:** Keep the current branch as the behavior source of truth and use `main` only as a presentation donor. Re-skin shared shells and page-level components by adapting restored UI patterns to the existing presenter/store/API contracts, then verify the course-first flow still passes route and learning tests.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript 5, Tailwind CSS, Zustand, Vitest, Testing Library

---

## File Map

- Modify: `frontend/app/page.tsx`
  - Reapply the `main` home shell while keeping public catalog loading and recommended/all behavior.
- Modify: `frontend/app/courses/[courseSlug]/page.tsx`
  - Wrap the overview route in restored page chrome and preserve the current start-course decision flow.
- Modify: `frontend/components/layout/TopNav.tsx`
  - Align shared top navigation with the `main` version and ensure nav items fit course-first routing.
- Modify: `frontend/components/layout/Sidebar.tsx`
  - Keep the restored sidebar/navigation shell aligned with current route names.
- Modify: `frontend/components/course/CourseCatalog.tsx`
  - Re-skin course cards/grid using `main` dashboard card language while preserving course catalog props.
- Modify: `frontend/components/course/CourseOverview.tsx`
  - Build the new overview page using the restored visual vocabulary from `main`.
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
  - Re-skin the learning route shell toward `main` without changing tutor/player behavior.
- Test: `frontend/tests/routes/course/catalog.test.tsx`
  - Assert restored shell elements on home and overview.
- Test: `frontend/tests/routes/course/personalized-catalog.test.tsx`
  - Assert recommended/all tabs still coexist with the restored home UI.
- Test: `frontend/tests/routes/learning/unit.test.tsx`
  - Assert restored learning shell keeps breadcrumb and tutor toggle behavior.

### Task 1: Restore Shared Navigation And Home Shell

**Files:**
- Modify: `frontend/components/layout/TopNav.tsx`
- Modify: `frontend/components/layout/Sidebar.tsx`
- Modify: `frontend/app/page.tsx`
- Test: `frontend/tests/routes/course/catalog.test.tsx`
- Test: `frontend/tests/routes/course/personalized-catalog.test.tsx`

- [ ] **Step 1: Write the failing UI assertions for the restored home shell**

Add checks that the home page exposes the restored shared shell and the familiar donor wording from `main` while still rendering course data:

```tsx
it("renders the restored course shell on the public catalog home", async () => {
  courseApiMock.catalog.mockResolvedValue({
    items: [CS231N_ITEM, CS224N_ITEM],
  });

  render(<HomePage />);

  await waitFor(() => {
    expect(screen.getByText("AI Learning Hub")).toBeInTheDocument();
  });

  expect(screen.getByRole("link", { name: "Courses" })).toBeInTheDocument();
  expect(screen.getByText("Tìm kiếm khóa học...")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the targeted route tests to verify the new assertions fail**

Run:

```bash
cd frontend && npm test -- --run tests/routes/course/catalog.test.tsx tests/routes/course/personalized-catalog.test.tsx
```

Expected: FAIL because the current home page still uses the refactor-era hero shell instead of the restored `main` chrome.

- [ ] **Step 3: Reapply the shared `main` navigation shell and donor home layout**

Restore the `main` navigation shape in `TopNav` and `Sidebar`, keeping current route names:

```tsx
const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/", label: "Courses", icon: Library, exact: true },
  { href: "/history", label: "Lịch sử", icon: History },
  { href: "/profile", label: "Hồ sơ", icon: User },
];
```

Use the restored shell in `frontend/app/page.tsx`, but keep presenter-driven data:

```tsx
return (
  <main className="min-h-screen px-4 py-8 md:px-6">
    <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
      <section className="space-y-2">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          {model.hero.title}
        </h1>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {model.hero.description}
        </p>
      </section>

      {model.catalog.showTabs && /* preserve current tab logic */}

      <CourseCatalog items={model.catalog.displayedCourses} />
    </div>
  </main>
);
```

- [ ] **Step 4: Run the home and personalized catalog tests again**

Run:

```bash
cd frontend && npm test -- --run tests/routes/course/catalog.test.tsx tests/routes/course/personalized-catalog.test.tsx
```

Expected: PASS with the restored shell and existing recommendation behavior both intact.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/layout/TopNav.tsx frontend/components/layout/Sidebar.tsx frontend/app/page.tsx frontend/tests/routes/course/catalog.test.tsx frontend/tests/routes/course/personalized-catalog.test.tsx
git commit -m "refactor: restore main shell for course catalog"
```

### Task 2: Re-skin Course Catalog Cards And Overview

**Files:**
- Modify: `frontend/components/course/CourseCatalog.tsx`
- Modify: `frontend/components/course/CourseOverview.tsx`
- Modify: `frontend/app/courses/[courseSlug]/page.tsx`
- Test: `frontend/tests/routes/course/catalog.test.tsx`

- [ ] **Step 1: Extend the route tests with overview-shell expectations**

Add assertions that overview now looks like an extension of the restored `main` UI:

```tsx
it("renders overview with restored page chrome and start CTA", async () => {
  courseApiMock.overview.mockResolvedValue(CS231N_OVERVIEW);

  render(<CourseOverviewPage params={{ courseSlug: "cs231n" }} />);

  await waitFor(() => {
    expect(screen.getByText("AI Learning Hub")).toBeInTheDocument();
  });

  expect(screen.getByText("What you will get")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start learning" })).toBeEnabled();
});
```

- [ ] **Step 2: Run the overview route test to verify it fails**

Run:

```bash
cd frontend && npm test -- --run tests/routes/course/catalog.test.tsx
```

Expected: FAIL because the current overview still uses the newer gradient-heavy layout instead of the restored shared shell.

- [ ] **Step 3: Rebuild course cards and overview with `main` card language**

Adapt the `main` dashboard card treatment to course catalog items:

```tsx
<div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
  {items.map((course, idx) => (
    <article key={course.slug} className="card overflow-hidden flex flex-col" style={{ padding: 0 }}>
      <div className={`relative h-36 bg-gradient-to-br ${gradientFor(idx)} flex items-center justify-center`}>
        <BookOpen className="h-12 w-12 text-white opacity-30" />
        <CourseStatusBadge status={course.status} />
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <h2 className="font-semibold leading-snug">{course.title}</h2>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {course.short_description}
        </p>
        <Link href={`/courses/${course.slug}`} className="btn-primary mt-auto">
          Open overview
        </Link>
      </div>
    </article>
  ))}
</div>
```

Reshape overview around the same shell primitives:

```tsx
<div className="space-y-8">
  <section className="card">
    <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
      Course overview
    </p>
    <h1 className="mt-2 text-3xl font-bold">{data.overview.headline}</h1>
    <p className="mt-3 text-sm leading-7" style={{ color: "var(--text-secondary)" }}>
      {data.overview.summary_markdown}
    </p>
  </section>

  <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
    {/* What you will get + Structure cards */}
  </section>
</div>
```

Keep the current `handleStart` decision and `coming_soon` disabling behavior untouched.

- [ ] **Step 4: Run the catalog/overview route tests and typecheck**

Run:

```bash
cd frontend && npm test -- --run tests/routes/course/catalog.test.tsx
cd frontend && ./node_modules/.bin/tsc --noEmit
```

Expected: PASS for both commands.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/course/CourseCatalog.tsx frontend/components/course/CourseOverview.tsx frontend/app/courses/[courseSlug]/page.tsx frontend/tests/routes/course/catalog.test.tsx
git commit -m "refactor: restore main styling for catalog and overview"
```

### Task 3: Re-skin The Learning Route Without Touching Behavior

**Files:**
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
- Test: `frontend/tests/routes/learning/unit.test.tsx`

- [ ] **Step 1: Add a failing test for the restored learning shell framing**

Add assertions for restored shell cues that must coexist with the existing tutor behavior:

```tsx
it("renders the restored learning shell chrome with tutor toggle intact", async () => {
  courseApiMock.learningUnit.mockResolvedValue(LECTURE_1_UNIT);

  render(
    <LearningPage params={{ courseSlug: "cs231n", unitSlug: "lecture-1-introduction" }} />,
  );

  await waitFor(() => {
    expect(screen.getByText("Lecture 1: Introduction")).toBeInTheDocument();
  });

  expect(screen.getByText("Chapters")).toBeInTheDocument();
  expect(screen.getByText("AI Tutor")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the learning route test to confirm the framing assertions fail**

Run:

```bash
cd frontend && npm test -- --run tests/routes/learning/unit.test.tsx
```

Expected: FAIL once the new shell assertions are added and before the learning page is reskinned.

- [ ] **Step 3: Re-skin the learning shell toward `main` while preserving player/tutor logic**

Keep all existing behavior, but move container styling toward the restored shell:

```tsx
return (
  <div className="min-h-[calc(100vh-4rem)] bg-[var(--bg-page)]">
    <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
      <section className="card flex-1 overflow-hidden p-0">
        {/* breadcrumb bar, video/content, progress, chapters */}
      </section>

      {tutor.enabled && tutorOpen && (
        <aside className="card w-[22rem] overflow-hidden p-0">
          <InContextTutor ... />
        </aside>
      )}
    </div>
  </div>
);
```

Do not change:

```tsx
const decision = await courseApi.learningUnit(courseSlug, unitSlug);
api.get(`/api/lectures/${legacyLectureId}/toc`)
captureFrame()
```

- [ ] **Step 4: Run the learning route test, shared route tests, and typecheck**

Run:

```bash
cd frontend && npm test -- --run tests/routes/learning/unit.test.tsx tests/routes/course/catalog.test.tsx tests/routes/course/personalized-catalog.test.tsx tests/routes/course/start.test.tsx tests/routes/learning/legacy-tutor-redirect.test.tsx
cd frontend && ./node_modules/.bin/tsc --noEmit
```

Expected: PASS for all route tests and typecheck.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/learn/LearningUnitShell.tsx frontend/tests/routes/learning/unit.test.tsx
git commit -m "refactor: align learning shell with restored main ui"
```

## Self-Review

- Spec coverage checked:
  - restored shared shell: Task 1
  - catalog and overview restoration: Task 2
  - learning shell re-skin: Task 3
  - preservation of course-first behavior is enforced by keeping presenter/store/gating files out of scope and rerunning existing route tests after each task
- Placeholder scan completed:
  - no `TODO`, `TBD`, or unnamed files remain
- Type consistency checked:
  - file paths, test names, and component names match the current branch
