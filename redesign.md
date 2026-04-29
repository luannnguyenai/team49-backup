# Product-Wide Visual Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current mixed visual language with one unified product-wide color system derived from the landing page, while isolating all changes to design tokens, styling classes, and presentational components only.

**Architecture:** This rebrand is token-first. The implementation starts by defining a new semantic color layer in `frontend/app/globals.css` and updating the Tailwind bridge in `frontend/tailwind.config.ts`, then migrates shared UI primitives and shell components before touching page-level hard-coded colors. No API contracts, state logic, routing, business logic, or backend behavior may change.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript 5, Tailwind CSS, CSS custom properties, `next-themes`

---

## Constraints

- Only the design language may change.
- Do not modify backend code, API contracts, data flow, state management, routing semantics, or business logic.
- Do not change button handlers, form submission logic, auth logic, or fetch behavior.
- Keep success, warning, and error semantics distinct from the new brand palette.
- Light mode is the primary target. Dark mode should remain stable and readable, but deep dark-mode redesign is out of scope for this pass.

## Target Design Language

- **Base neutrals:** `slate-50`, `white`, `slate-100`, `slate-950`, `slate-700`, `slate-500`
- **Primary brand axis:** `indigo -> cyan`
- **Accent axis:** `cyan`
- **Gradient tail / supportive accent:** `teal`
- **Visual principle:** Most UI remains neutral; saturated color appears only in CTA, accents, highlights, and hero surfaces.

## File Structure

**Core token and config files**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`

**Shared UI primitives**
- Modify: `frontend/components/ui/Button.tsx`
- Modify: `frontend/components/ui/Input.tsx`
- Modify: `frontend/components/ui/LoadingSpinner.tsx`

**Shared layout and shell**
- Modify: `frontend/components/layout/PublicTopNav.tsx`
- Modify: `frontend/components/layout/TopNav.tsx`
- Modify: `frontend/components/layout/BrandLogo.tsx`
- Modify: `frontend/components/layout/Sidebar.tsx`
- Modify: `frontend/components/layout/TopBar.tsx`

**Shared course presentation**
- Modify: `frontend/components/course/CourseStatusBadge.tsx`
- Modify: `frontend/components/course/CourseCatalog.tsx`
- Modify: `frontend/components/course/CourseOverview.tsx`
- Modify: `frontend/components/course/CourseOverviewInteractive.tsx`

**Landing**
- Modify: `frontend/components/landing/LandingPage.tsx`

**Protected pages with hard-coded colors**
- Modify: `frontend/app/(protected)/dashboard/page.tsx`
- Modify: `frontend/app/(protected)/profile/page.tsx`
- Modify: `frontend/app/(protected)/history/page.tsx`
- Modify: `frontend/app/tutor/page.tsx`

**Optional follow-up sweep if color debt remains**
- Inspect and modify only if needed: `frontend/app/assessment/page.tsx`
- Inspect and modify only if needed: `frontend/app/module-test/[sectionId]/results/page.tsx`
- Inspect and modify only if needed: `frontend/components/learn/LearningUnitShell.tsx`
- Inspect and modify only if needed: `frontend/components/learn/InContextTutor.tsx`

**Verification**
- Create: `frontend/tests/unit/ui/theme-tokens.test.ts`
- Create: `frontend/tests/unit/layout/topnav-theme.test.tsx`
- Create: `frontend/tests/unit/course/course-status-badge-theme.test.tsx`

## Non-Goals

- No redesign of information architecture
- No copy rewrite
- No component behavior changes
- No accessibility refactor beyond preserving or improving color contrast and focus visibility
- No attempt to make dark mode visually match landing page one-to-one

### Task 1: Define Semantic Brand Tokens

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`
- Test: `frontend/tests/unit/ui/theme-tokens.test.ts`

- [ ] **Step 1: Write the failing token presence test**

```ts
import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

describe("theme token contract", () => {
  it("defines the product-wide light-mode brand tokens", () => {
    const css = fs.readFileSync(
      path.join(process.cwd(), "app/globals.css"),
      "utf8",
    );

    expect(css).toContain("--surface-page:");
    expect(css).toContain("--surface-card:");
    expect(css).toContain("--surface-elevated:");
    expect(css).toContain("--text-strong:");
    expect(css).toContain("--text-body:");
    expect(css).toContain("--text-muted:");
    expect(css).toContain("--brand-primary:");
    expect(css).toContain("--brand-primary-hover:");
    expect(css).toContain("--brand-accent:");
    expect(css).toContain("--brand-accent-soft:");
    expect(css).toContain("--ring-brand:");
    expect(css).toContain("--shadow-brand-soft:");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run frontend/tests/unit/ui/theme-tokens.test.ts`

Expected: FAIL because the new semantic token names do not exist yet.

- [ ] **Step 3: Add the semantic token layer and Tailwind bridge**

```css
:root {
  --surface-page: #f8fafc;
  --surface-card: rgba(255, 255, 255, 0.92);
  --surface-elevated: #ffffff;
  --surface-accent-soft: #ecfeff;
  --text-strong: #020617;
  --text-body: #334155;
  --text-muted: #64748b;
  --border-subtle: rgba(148, 163, 184, 0.24);
  --brand-primary: #0891b2;
  --brand-primary-hover: #0e7490;
  --brand-primary-strong: #4f46e5;
  --brand-accent: #06b6d4;
  --brand-accent-soft: rgba(34, 211, 238, 0.12);
  --ring-brand: rgba(34, 211, 238, 0.34);
  --shadow-brand-soft: 0 20px 60px -30px rgba(8, 145, 178, 0.32);
}

.dark {
  --surface-page: #0f172a;
  --surface-card: #1e293b;
  --surface-elevated: #111827;
  --surface-accent-soft: rgba(8, 47, 73, 0.35);
  --text-strong: #f8fafc;
  --text-body: #e2e8f0;
  --text-muted: #cbd5e1;
  --border-subtle: #334155;
  --brand-primary: #22d3ee;
  --brand-primary-hover: #67e8f9;
  --brand-primary-strong: #818cf8;
  --brand-accent: #67e8f9;
  --brand-accent-soft: rgba(34, 211, 238, 0.16);
  --ring-brand: rgba(103, 232, 249, 0.36);
  --shadow-brand-soft: 0 20px 60px -30px rgba(34, 211, 238, 0.28);
}
```

```ts
colors: {
  primary: {
    500: "#0891b2",
    600: "#0891b2",
    700: "#0e7490",
  },
  brand: {
    indigo: "#4f46e5",
    cyan: "#06b6d4",
    teal: "#2dd4bf",
    ink: "#020617",
  },
},
boxShadow: {
  card: "0 18px 55px rgba(15,23,42,0.08)",
  "brand-soft": "0 20px 60px -30px rgba(8,145,178,0.32)",
},
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run frontend/tests/unit/ui/theme-tokens.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/globals.css frontend/tailwind.config.ts frontend/tests/unit/ui/theme-tokens.test.ts
git commit -m "design: add semantic brand token layer"
```

### Task 2: Re-theme Shared Primitives Without Changing Behavior

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/components/ui/Button.tsx`
- Modify: `frontend/components/ui/Input.tsx`
- Modify: `frontend/components/ui/LoadingSpinner.tsx`
- Test: `frontend/tests/unit/ui/theme-tokens.test.ts`

- [ ] **Step 1: Write the failing primitive-style assertions**

```ts
import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

describe("primitive brand usage", () => {
  it("maps button and input utility classes to semantic brand tokens", () => {
    const css = fs.readFileSync(
      path.join(process.cwd(), "app/globals.css"),
      "utf8",
    );

    expect(css).toContain(".btn-primary");
    expect(css).toContain("var(--brand-primary)");
    expect(css).toContain("var(--brand-primary-hover)");
    expect(css).toContain("var(--ring-brand)");
    expect(css).toContain(".input-base:focus");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run frontend/tests/unit/ui/theme-tokens.test.ts`

Expected: FAIL because the utilities still point to the old `primary-*` and neutral focus styling.

- [ ] **Step 3: Update primitive styling only**

```css
.card {
  @apply rounded-xl border p-6;
  background-color: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-brand-soft);
}

.btn-primary {
  @apply inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-white transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2;
  background: linear-gradient(135deg, var(--brand-primary-strong), var(--brand-primary));
}

.btn-primary:hover {
  filter: brightness(0.96);
}

.btn-primary:focus-visible {
  box-shadow: 0 0 0 3px var(--ring-brand);
}

.btn-secondary {
  @apply inline-flex items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-semibold transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2;
  background-color: rgba(255, 255, 255, 0.78);
  border-color: var(--border-subtle);
  color: var(--text-body);
}

.input-base:focus {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px var(--ring-brand);
}
```

```tsx
const variantClass: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
  danger: "inline-flex items-center justify-center gap-2 rounded-lg bg-red-500 px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-red-600 active:scale-[0.98] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500",
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run frontend/tests/unit/ui/theme-tokens.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/globals.css frontend/components/ui/Button.tsx frontend/components/ui/Input.tsx frontend/components/ui/LoadingSpinner.tsx frontend/tests/unit/ui/theme-tokens.test.ts
git commit -m "design: re-theme shared ui primitives"
```

### Task 3: Align Public and Protected Navigation to the New Brand

**Files:**
- Modify: `frontend/components/layout/PublicTopNav.tsx`
- Modify: `frontend/components/layout/TopNav.tsx`
- Modify: `frontend/components/layout/BrandLogo.tsx`
- Modify: `frontend/components/layout/Sidebar.tsx`
- Modify: `frontend/components/layout/TopBar.tsx`
- Test: `frontend/tests/unit/layout/topnav-theme.test.tsx`

- [ ] **Step 1: Write the failing nav-theme test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PublicTopNav from "@/components/layout/PublicTopNav";

describe("PublicTopNav theme", () => {
  it("renders the brand CTA and translucent shell classes", () => {
    render(<PublicTopNav />);

    expect(screen.getByRole("link", { name: /đăng ký/i }).className).toMatch(/bg-slate-950|bg-\[|rounded-full/);
    expect(screen.getByRole("banner").className).toMatch(/backdrop-blur|border-white\/60/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run frontend/tests/unit/layout/topnav-theme.test.tsx`

Expected: FAIL because `banner` role/classes are not asserted in a stable branded way yet.

- [ ] **Step 3: Normalize nav shell and active states to brand tokens**

```tsx
<header className="sticky top-0 z-40 border-b border-white/60 bg-white/75 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85">
```

```tsx
className={cn(
  "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
  active
    ? "bg-cyan-50 text-cyan-700 dark:bg-cyan-950/30 dark:text-cyan-200"
    : "hover:bg-white/70 dark:hover:bg-slate-800",
)}
```

```tsx
className="flex h-9 w-9 items-center justify-center rounded-full bg-cyan-50 text-cyan-700 dark:bg-cyan-950/30 dark:text-cyan-200"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run frontend/tests/unit/layout/topnav-theme.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/layout/PublicTopNav.tsx frontend/components/layout/TopNav.tsx frontend/components/layout/BrandLogo.tsx frontend/components/layout/Sidebar.tsx frontend/components/layout/TopBar.tsx frontend/tests/unit/layout/topnav-theme.test.tsx
git commit -m "design: align navigation shells with brand palette"
```

### Task 4: Preserve Semantic Status Colors While Reframing Their Presentation

**Files:**
- Modify: `frontend/components/course/CourseStatusBadge.tsx`
- Test: `frontend/tests/unit/course/course-status-badge-theme.test.tsx`

- [ ] **Step 1: Write the failing badge contract test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CourseStatusBadge from "@/components/course/CourseStatusBadge";

describe("CourseStatusBadge", () => {
  it("keeps semantic status colors while using the updated badge shape", () => {
    render(<CourseStatusBadge status="ready" />);

    const badge = screen.getByText("Ready");
    expect(badge.className).toMatch(/rounded-full/);
    expect(badge.className).toMatch(/border-emerald-200/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run frontend/tests/unit/course/course-status-badge-theme.test.tsx`

Expected: FAIL if the new badge shape, spacing, or emphasis has not been stabilized yet.

- [ ] **Step 3: Update badge presentation but keep semantic meaning**

```tsx
const STATUS_COPY: Record<CourseStatus, { label: string; className: string }> = {
  ready: {
    label: "Ready",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  coming_soon: {
    label: "Coming soon",
    className: "border-amber-200 bg-amber-50 text-amber-700",
  },
  metadata_partial: {
    label: "Metadata partial",
    className: "border-cyan-200 bg-cyan-50 text-cyan-700",
  },
};
```

```tsx
className={cn(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-widest-xs shadow-sm",
  copy.className,
)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run frontend/tests/unit/course/course-status-badge-theme.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/course/CourseStatusBadge.tsx frontend/tests/unit/course/course-status-badge-theme.test.tsx
git commit -m "design: refresh course status badge presentation"
```

### Task 5: Converge Landing and App Shell on the Same Token Vocabulary

**Files:**
- Modify: `frontend/components/landing/LandingPage.tsx`
- Modify: `frontend/app/globals.css`
- Test: `frontend/tests/unit/ui/theme-tokens.test.ts`

- [ ] **Step 1: Write the failing landing token usage test**

```ts
import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

describe("landing/app token convergence", () => {
  it("keeps the landing gradient palette while referencing the shared brand vocabulary", () => {
    const source = fs.readFileSync(
      path.join(process.cwd(), "components/landing/LandingPage.tsx"),
      "utf8",
    );

    expect(source).toContain("from-indigo-600");
    expect(source).toContain("via-cyan-500");
    expect(source).toContain("to-teal-400");
  });
});
```

- [ ] **Step 2: Run test to verify it fails only if convergence work removes the approved palette**

Run: `npm test -- --run frontend/tests/unit/ui/theme-tokens.test.ts`

Expected: PASS before edits or FAIL if the landing palette has drifted away from the approved brand axis.

- [ ] **Step 3: Replace repeated one-off neutrals with shared surfaces where safe**

```tsx
<div className="bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-white">
```

```css
.card {
  background-color: var(--surface-card);
}
```

```tsx
className="rounded-[28px] border border-slate-200 bg-slate-50 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
```

Implementation note: keep hero gradients, glows, and accent moments from the landing page; only converge repeated neutral and shell styling with the new token layer.

- [ ] **Step 4: Run test to verify approved palette remains intact**

Run: `npm test -- --run frontend/tests/unit/ui/theme-tokens.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/landing/LandingPage.tsx frontend/app/globals.css frontend/tests/unit/ui/theme-tokens.test.ts
git commit -m "design: converge landing and app shell styling"
```

### Task 6: Repaint Dashboard With Tokens Only

**Files:**
- Modify: `frontend/app/(protected)/dashboard/page.tsx`
- Modify: `frontend/features/dashboard/presenters.ts`
- Test: `frontend/tests/unit/dashboard/presenters.test.ts`

- [ ] **Step 1: Write the failing dashboard-style assertion**

```ts
import { buildDashboardCourseCardModel } from "@/features/dashboard/presenters";
import { describe, expect, it } from "vitest";

describe("dashboard presenter contract", () => {
  it("keeps CTA routing semantics unchanged during the visual rebrand", () => {
    const model = buildDashboardCourseCardModel({
      id: "1",
      slug: "intro-ai",
      title: "Intro AI",
      short_description: "desc",
      status: "ready",
      is_recommended: false,
    } as never);

    expect(model.href).toBe("/courses/intro-ai/start");
    expect(model.ctaLabel).toBe("Bắt đầu học");
  });
});
```

- [ ] **Step 2: Run test to verify the behavior baseline**

Run: `npm test -- --run frontend/tests/unit/dashboard/presenters.test.ts`

Expected: PASS and serves as a guard that styling changes must not alter dashboard routing semantics.

- [ ] **Step 3: Replace hard-coded page colors with the new design language**

```tsx
<div className="card flex flex-col overflow-hidden transition-shadow group hover:shadow-brand-soft" style={{ backgroundColor: "var(--surface-card)", padding: 0 }}>
```

```tsx
<div className={`relative flex h-36 items-center justify-center bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400`}>
```

```tsx
style={{ color: "var(--text-strong)" }}
style={{ color: "var(--text-body)" }}
style={{ backgroundColor: "var(--surface-page)" }}
```

Implementation note: do not change `historyApi.list`, `filterDashboardCourses`, tab logic, or CTA href generation.

- [ ] **Step 4: Run test to verify semantics remain unchanged**

Run: `npm test -- --run frontend/tests/unit/dashboard/presenters.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(protected)/dashboard/page.tsx frontend/features/dashboard/presenters.ts frontend/tests/unit/dashboard/presenters.test.ts
git commit -m "design: repaint dashboard with shared brand tokens"
```

### Task 7: Repaint Tutor, Profile, and History Without Touching Logic

**Files:**
- Modify: `frontend/app/tutor/page.tsx`
- Modify: `frontend/app/(protected)/profile/page.tsx`
- Modify: `frontend/app/(protected)/history/page.tsx`
- Test: `frontend/tests/unit/tutor/in-context-tutor.test.tsx`

- [ ] **Step 1: Write a routing/behavior guard for tutor page dependencies**

```ts
import { describe, expect, it } from "vitest";
import { buildUserCourseCollections } from "@/features/course-membership/presenters";

describe("tutor page behavior guard", () => {
  it("keeps joined and recommended course separation unchanged", () => {
    const result = buildUserCourseCollections(
      [
        { slug: "a", is_recommended: true },
        { slug: "b", is_recommended: true },
      ] as never,
      [{ course_slug: "a" }] as never,
      null,
    );

    expect(result.joinedCourses.map((item) => item.slug)).toEqual(["a"]);
    expect(result.recommendedCourses.map((item) => item.slug)).toEqual(["b"]);
  });
});
```

- [ ] **Step 2: Run behavior guards before visual edits**

Run: `npm test -- --run frontend/tests/unit/tutor/in-context-tutor.test.tsx`

Expected: PASS baseline. If a dedicated presenter test is added during implementation, run it here as well.

- [ ] **Step 3: Replace page-local hard-coded blues/violets with brand tokens and approved gradients**

```tsx
className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700 dark:bg-cyan-950/30 dark:text-cyan-200"
```

```tsx
style={{ borderColor: "var(--border-subtle)", backgroundColor: "var(--surface-card)" }}
style={{ color: "var(--text-strong)" }}
style={{ color: "var(--text-body)" }}
style={{ color: "var(--text-muted)" }}
```

```tsx
className="rounded-full bg-cyan-50 px-2 py-0.5 text-xs font-semibold text-cyan-700 dark:bg-cyan-950/30 dark:text-cyan-200"
```

Implementation note: do not edit `sessionStorage` usage, history fetches, profile calculations, sorting, filtering, pagination, or expansion behavior.

- [ ] **Step 4: Run behavior guards after the repaint**

Run: `npm test -- --run frontend/tests/unit/tutor/in-context-tutor.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/tutor/page.tsx frontend/app/(protected)/profile/page.tsx frontend/app/(protected)/history/page.tsx frontend/tests/unit/tutor/in-context-tutor.test.tsx
git commit -m "design: repaint tutor profile and history pages"
```

### Task 8: Final Brand QA and Regression Verification

**Files:**
- Modify: `redesign.md`

- [ ] **Step 1: Run targeted verification commands**

Run: `npm run type-check`
Expected: PASS

Run: `npm test -- --run frontend/tests/unit/ui/theme-tokens.test.ts frontend/tests/unit/layout/topnav-theme.test.tsx frontend/tests/unit/course/course-status-badge-theme.test.tsx frontend/tests/unit/dashboard/presenters.test.ts frontend/tests/unit/tutor/in-context-tutor.test.tsx`
Expected: PASS

- [ ] **Step 2: Do a manual visual sweep in light mode**

Check these exact surfaces:

```txt
1. Landing hero CTA, chips, glow cards
2. PublicTopNav and protected TopNav active states
3. Dashboard stat cards, tabs, course cards, CTA buttons
4. Tutor header, active course panel, recommendation sections
5. Profile avatar card, achievement badges, radar surrounding surfaces
6. History filters, table headers, badges, expanded panels
```

Expected:

```txt
- CTA hierarchy is clearer than before
- Accent cyan appears as signal, not body text
- Most backgrounds remain neutral
- No page still looks like the old blue-first app
- Success / warning / error colors still read semantically
- Focus rings remain visible on inputs and buttons
```

- [ ] **Step 3: Record any remaining color debt**

```txt
If any component still uses stale hard-coded blue/violet classes, append a short follow-up list here before opening implementation review.
```

- [ ] **Step 4: Commit**

```bash
git add redesign.md
git commit -m "docs: finalize product-wide visual rebrand plan"
```

## Self-Review

- Spec coverage:
  - Product-wide palette unification: covered by Tasks 1, 5
  - Isolation from backend/API/logic: enforced in Constraints and Tasks 6-7
  - Landing-derived visual language: covered by Tasks 1, 3, 5
  - Light-mode-first rollout: reflected in token definitions and QA
- Placeholder scan: no `TODO`, `TBD`, or “implement later” placeholders remain.
- Type consistency: existing file paths, component names, and presenter names match the codebase inspected during planning.

## Review Gate

This plan is saved to `redesign.md` per user preference and is intended for Claude review before any implementation starts.
