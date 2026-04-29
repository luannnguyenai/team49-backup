# Phase 1 Product Color System Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the landing page and app UI under one shared color system derived from the landing palette, while isolating all work to tokens, utilities, and presentational styling only.

**Architecture:** This is a token-first, color-only rebrand. The implementation defines a semantic color layer in `frontend/app/globals.css`, exposes those semantics through Tailwind utilities in `frontend/tailwind.config.ts`, migrates shared primitives and shells to those utilities, and then repaints page-level hard-coded color usage. No API contracts, handlers, routing, state, or business logic may change.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript 5, Tailwind CSS, CSS custom properties, `next-themes`, Vitest, Testing Library

---

## Scope

- This plan covers **color system rebranding only**.
- It does **not** cover typography, spacing, copywriting, information architecture, or behavior redesign.
- This is **Phase 1**, not a full end-to-end redesign.

## Constraints

- Only the design language may change.
- Do not modify backend code, API contracts, fetch behavior, form submission logic, auth behavior, routing semantics, or state management.
- Do not change button handlers, link destinations, search behavior, or presenter logic.
- Keep success, warning, and error semantics distinct from the new brand palette.
- Light mode is the primary target.
- Dark mode may receive token plumbing required for safety, but no deep visual redesign is in scope.

## Target Design Language

- **Base neutrals:** `slate-50`, `white`, `slate-100`, `slate-950`, `slate-700`, `slate-500`
- **Primary action color:** cyan-led brand primary
- **Accent color:** cyan
- **Depth/supportive color:** indigo
- **Gradient tail:** teal
- **Usage rule:** Most UI remains neutral; saturated color is reserved for primary actions, accents, highlights, and selected hero surfaces.
- **Primary button rule:** standard `.btn-primary` is flat brand color; gradients are reserved for explicit hero treatments only.

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

**Verification**
- Create: `frontend/tests/unit/ui/button-theme.test.tsx`
- Create: `frontend/tests/unit/layout/topnav-theme.test.tsx`
- Create: `frontend/tests/unit/course/course-status-badge-theme.test.tsx`

## Non-Goals

- No typography scale redesign
- No spacing system redesign
- No copy rewrite
- No information architecture changes
- No business-logic cleanup
- No dark-mode restyling beyond safety and regression control

## Implementation Rules

- Preserve the full `primary-50 ... primary-950` ramp in Tailwind. Re-tint it if needed, but do not remove steps because the existing codebase already depends on them.
- Register semantic Tailwind colors for text and surfaces so page adoption uses classes like `bg-surface-page`, `bg-surface-card`, `text-text-strong`, `text-text-body`, `text-text-muted`, `bg-brand-accent-soft`, `text-brand-accent`.
- Do not add new `style={{ color: "var(--...)" }}` usage unless there is no practical class-based option.
- Do not hard-code `bg-cyan-*`, `text-cyan-*`, or similar brand literals in adoption tasks when semantic utilities can express the same intent.
- Do not apply gradients to every standard primary button.

### Task 1: Define Semantic Brand Tokens and Tailwind Utilities

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`
- Test: `frontend/tests/unit/ui/button-theme.test.tsx`

- [ ] **Step 1: Write the failing render-based token-consumption test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Button from "@/components/ui/Button";

describe("Button theme contract", () => {
  it("keeps the primary button on the semantic button class", () => {
    render(<Button>Continue</Button>);

    const button = screen.getByRole("button", { name: "Continue" });
    expect(button.className).toContain("btn-primary");
  });
});
```

- [ ] **Step 2: Run test to verify the baseline**

Run: `npm test -- --run frontend/tests/unit/ui/button-theme.test.tsx`

Expected: PASS baseline. This is a guard that later token and utility changes must continue to flow through the shared button primitive.

- [ ] **Step 3: Add the semantic token layer and semantic Tailwind bridge**

```css
:root {
  --surface-page: #f8fafc;
  --surface-card: #ffffff;
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
    50: "#ecfeff",
    100: "#cffafe",
    200: "#a5f3fc",
    300: "#67e8f9",
    400: "#22d3ee",
    500: "#06b6d4",
    600: "#0891b2",
    700: "#0e7490",
    800: "#155e75",
    900: "#164e63",
    950: "#083344",
  },
  brand: {
    indigo: "#4f46e5",
    cyan: "#06b6d4",
    teal: "#2dd4bf",
    ink: "#020617",
  },
  surface: {
    page: "var(--surface-page)",
    card: "var(--surface-card)",
    elevated: "var(--surface-elevated)",
    "accent-soft": "var(--surface-accent-soft)",
  },
  text: {
    strong: "var(--text-strong)",
    body: "var(--text-body)",
    muted: "var(--text-muted)",
  },
  border: {
    subtle: "var(--border-subtle)",
  },
},
boxShadow: {
  card: "0 18px 55px rgba(15,23,42,0.08)",
  "brand-soft": "0 20px 60px -30px rgba(8,145,178,0.32)",
},
```

- [ ] **Step 4: Re-run the button contract test**

Run: `npm test -- --run frontend/tests/unit/ui/button-theme.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/globals.css frontend/tailwind.config.ts frontend/tests/unit/ui/button-theme.test.tsx
git commit -m "design: add semantic brand tokens and tailwind utilities"
```

### Task 2: Re-theme Shared Primitives Without Changing Behavior

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/components/ui/Button.tsx`
- Modify: `frontend/components/ui/Input.tsx`
- Modify: `frontend/components/ui/LoadingSpinner.tsx`
- Test: `frontend/tests/unit/ui/button-theme.test.tsx`

- [ ] **Step 1: Write the failing class-contract test for button variants**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Button from "@/components/ui/Button";

describe("Button variant contract", () => {
  it("keeps primary and secondary variants mapped to shared utility classes", () => {
    render(
      <>
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
      </>,
    );

    expect(screen.getByRole("button", { name: "Primary" }).className).toContain("btn-primary");
    expect(screen.getByRole("button", { name: "Secondary" }).className).toContain("btn-secondary");
  });
});
```

- [ ] **Step 2: Run test to verify the baseline**

Run: `npm test -- --run frontend/tests/unit/ui/button-theme.test.tsx`

Expected: PASS baseline

- [ ] **Step 3: Update primitive styling to semantic utilities and flat primary buttons**

```css
.card {
  @apply rounded-xl border p-6 bg-surface-card shadow-card;
  border-color: var(--border-subtle);
}

.btn-primary {
  @apply inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2;
  border-color: transparent;
}

.btn-secondary {
  @apply inline-flex items-center justify-center gap-2 rounded-lg border bg-surface-card px-4 py-2.5 text-sm font-semibold text-text-body transition-all duration-150 hover:bg-surface-page active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2;
  border-color: var(--border-subtle);
}

.btn-ghost {
  @apply inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-text-body transition-all duration-150 hover:bg-surface-page active:scale-[0.98] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2;
}

.input-base {
  @apply w-full rounded-lg border bg-surface-card px-3.5 py-2.5 text-sm text-text-strong outline-none transition-all duration-150;
  border-color: var(--border-subtle);
}

.input-base:focus {
  @apply border-primary-500;
  box-shadow: 0 0 0 3px var(--ring-brand);
}
```

- [ ] **Step 4: Re-run the button variant contract test**

Run: `npm test -- --run frontend/tests/unit/ui/button-theme.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/globals.css frontend/components/ui/Button.tsx frontend/components/ui/Input.tsx frontend/components/ui/LoadingSpinner.tsx frontend/tests/unit/ui/button-theme.test.tsx
git commit -m "design: re-theme shared ui primitives with semantic utilities"
```

### Task 3: Align Public and Protected Navigation to the New Brand

**Files:**
- Modify: `frontend/components/layout/PublicTopNav.tsx`
- Modify: `frontend/components/layout/TopNav.tsx`
- Modify: `frontend/components/layout/BrandLogo.tsx`
- Modify: `frontend/components/layout/Sidebar.tsx`
- Modify: `frontend/components/layout/TopBar.tsx`
- Test: `frontend/tests/unit/layout/topnav-theme.test.tsx`

- [ ] **Step 1: Write the nav-shell contract test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PublicTopNav from "@/components/layout/PublicTopNav";

describe("PublicTopNav theme contract", () => {
  it("keeps a translucent shell and a strong primary CTA", () => {
    render(<PublicTopNav />);

    expect(screen.getByRole("banner").className).toMatch(/backdrop-blur/);
    expect(screen.getByRole("link", { name: /đăng ký/i }).className).toMatch(/bg-slate-950|btn-primary/);
  });
});
```

- [ ] **Step 2: Run test to verify the baseline**

Run: `npm test -- --run frontend/tests/unit/layout/topnav-theme.test.tsx`

Expected: PASS baseline

- [ ] **Step 3: Normalize nav shell and active states using semantic classes, not raw cyan literals**

```tsx
<header className="sticky top-0 z-40 border-b border-white/60 bg-white/75 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85">
```

```tsx
className={cn(
  "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
  active
    ? "bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300"
    : "text-text-body hover:bg-surface-page dark:hover:bg-slate-800",
)}
```

```tsx
className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300"
```

- [ ] **Step 4: Re-run the nav-shell contract test**

Run: `npm test -- --run frontend/tests/unit/layout/topnav-theme.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/layout/PublicTopNav.tsx frontend/components/layout/TopNav.tsx frontend/components/layout/BrandLogo.tsx frontend/components/layout/Sidebar.tsx frontend/components/layout/TopBar.tsx frontend/tests/unit/layout/topnav-theme.test.tsx
git commit -m "design: align navigation shells with semantic brand utilities"
```

### Task 4: Preserve Semantic Status Colors While Refreshing Badge Presentation

**Files:**
- Modify: `frontend/components/course/CourseStatusBadge.tsx`
- Test: `frontend/tests/unit/course/course-status-badge-theme.test.tsx`

- [ ] **Step 1: Write the badge contract test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CourseStatusBadge from "@/components/course/CourseStatusBadge";

describe("CourseStatusBadge", () => {
  it("keeps semantic status colors and the pill badge shape", () => {
    render(<CourseStatusBadge status="ready" />);

    const badge = screen.getByText("Ready");
    expect(badge.className).toContain("rounded-full");
    expect(badge.className).toContain("border-emerald-200");
    expect(badge.className).toContain("bg-emerald-50");
  });
});
```

- [ ] **Step 2: Run test to verify the baseline**

Run: `npm test -- --run frontend/tests/unit/course/course-status-badge-theme.test.tsx`

Expected: PASS baseline

- [ ] **Step 3: Refresh badge shape and polish without altering semantic colors**

```tsx
className={cn(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-widest-xs shadow-sm",
  copy.className,
)}
```

Implementation note: keep `ready`, `coming_soon`, and `metadata_partial` mapped to semantic green/amber/cyan families. Do not fold them into the brand primary.

- [ ] **Step 4: Re-run the badge contract test**

Run: `npm test -- --run frontend/tests/unit/course/course-status-badge-theme.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/course/CourseStatusBadge.tsx frontend/tests/unit/course/course-status-badge-theme.test.tsx
git commit -m "design: refresh status badge presentation without changing semantics"
```

### Task 5: Converge Landing and App Shell on the Same Token Vocabulary

**Files:**
- Modify: `frontend/components/landing/LandingPage.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Inspect repeated neutral and shell classes on the landing page**

```txt
Look for repeated uses of:
- bg-slate-50 / bg-white / text-slate-950 / text-slate-600
- border-slate-200 / dark:border-slate-800
- card-like shells that should share the app token vocabulary
```

- [ ] **Step 2: Replace repeated neutral shells with shared semantic utilities where safe**

```tsx
className="bg-surface-page text-text-strong dark:bg-slate-950 dark:text-white"
```

```tsx
className="rounded-[28px] border border-border-subtle bg-surface-card p-6 shadow-card dark:border-slate-800 dark:bg-slate-900"
```

Implementation note: keep hero gradients, glows, and accent moments from the landing page. This task converges the repeated neutral shell language only.

- [ ] **Step 3: Verify by inspection that the approved landing gradient axis is still intact**

```txt
Must remain present in the hero surfaces:
- from-indigo-600
- via-cyan-500
- to-teal-400
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/landing/LandingPage.tsx frontend/app/globals.css
git commit -m "design: converge landing neutrals with shared color system"
```

### Task 6: Repaint Dashboard With Tokens and Utilities Only

**Files:**
- Modify: `frontend/app/(protected)/dashboard/page.tsx`
- Test: `frontend/tests/unit/dashboard/presenters.test.ts`

- [ ] **Step 1: Run the existing dashboard presenter test as a behavior guard**

Run: `npm test -- --run frontend/tests/unit/dashboard/presenters.test.ts`

Expected: PASS baseline

- [ ] **Step 2: Replace hard-coded page colors with semantic utility classes**

```tsx
<div className="card flex flex-col overflow-hidden p-0 transition-shadow group hover:shadow-brand-soft">
```

```tsx
<div className="relative flex h-36 items-center justify-center bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400">
```

```tsx
className="text-text-strong"
className="text-text-body"
className="bg-surface-page"
```

Implementation note: do not change `historyApi.list`, `filterDashboardCourses`, active tab logic, or CTA href generation. Do not add new inline `style={{ color: ... }}` where Tailwind utilities can express the same intent.

- [ ] **Step 3: Re-run the dashboard presenter test**

Run: `npm test -- --run frontend/tests/unit/dashboard/presenters.test.ts`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/app/(protected)/dashboard/page.tsx frontend/tests/unit/dashboard/presenters.test.ts
git commit -m "design: repaint dashboard with semantic color utilities"
```

### Task 7: Repaint Tutor, Profile, and History Without Touching Logic

**Files:**
- Modify: `frontend/app/tutor/page.tsx`
- Modify: `frontend/app/(protected)/profile/page.tsx`
- Modify: `frontend/app/(protected)/history/page.tsx`

- [ ] **Step 1: Run existing tutor behavior tests before repaint**

Run: `npm test -- --run frontend/tests/unit/tutor/in-context-tutor.test.tsx`

Expected: PASS baseline

- [ ] **Step 2: Replace page-local hard-coded brand colors with semantic utilities**

```tsx
className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300"
```

```tsx
className="rounded-full bg-surface-accent-soft px-2 py-0.5 text-xs font-semibold text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300"
```

```tsx
className="border-border-subtle bg-surface-card text-text-strong"
className="text-text-body"
className="text-text-muted"
```

Implementation note: do not edit `sessionStorage` usage, history fetches, profile calculations, sorting, filtering, pagination, or expansion behavior. Do not bypass the token layer with raw `bg-cyan-*` or inline CSS variables if semantic classes are available.

- [ ] **Step 3: Re-run existing tutor behavior tests**

Run: `npm test -- --run frontend/tests/unit/tutor/in-context-tutor.test.tsx`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/app/tutor/page.tsx frontend/app/(protected)/profile/page.tsx frontend/app/(protected)/history/page.tsx frontend/tests/unit/tutor/in-context-tutor.test.tsx
git commit -m "design: repaint tutor profile and history with semantic utilities"
```

### Task 8: Final QA for Light Mode, Dark Mode Safety, and Contrast

**Files:**
- Modify: `redesign.md`

- [ ] **Step 1: Run targeted verification commands**

Run: `npm run type-check`

Expected: PASS

Run: `npm test -- --run frontend/tests/unit/ui/button-theme.test.tsx frontend/tests/unit/layout/topnav-theme.test.tsx frontend/tests/unit/course/course-status-badge-theme.test.tsx frontend/tests/unit/dashboard/presenters.test.ts frontend/tests/unit/tutor/in-context-tutor.test.tsx`

Expected: PASS

- [ ] **Step 2: Run accessibility and quality checks**

Run: `npm run build`

Expected: PASS

Run: `npx lighthouse http://localhost:3000 --only-categories=accessibility --preset=desktop`

Expected: accessibility report completes with no new contrast regression caused by the rebrand

- [ ] **Step 3: Do a manual visual sweep in light mode**

Check:

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
- Standard primary buttons are flat brand color, not gradient
- Accent cyan appears as signal, not body text
- Most backgrounds remain neutral
- No page still looks like the old blue-first app
- Success / warning / error colors still read semantically
- Focus rings remain visible on inputs and buttons
```

- [ ] **Step 4: Do a dark-mode safety sweep**

Check:

```txt
1. Protected TopNav
2. Primary and secondary buttons
3. Card/background separation
4. Input focus ring visibility
5. Badge readability
```

Expected:

```txt
- No unreadable text
- No broken contrast on active states
- No accidental landing-style glow overuse
```

- [ ] **Step 5: Record remaining color debt**

```txt
If any component still uses stale hard-coded blue/violet classes, append a short follow-up list here before implementation review.
```

- [ ] **Step 6: Commit**

```bash
git add redesign.md
git commit -m "docs: finalize phase 1 color-system rebrand plan"
```

## Self-Review

- Accepted Claude review points incorporated:
  - Keep full `primary-50 ... 950` ramp
  - Expose semantic Tailwind utilities for text and surfaces
  - Avoid decorative string-match pseudo-tests as the main verification layer
  - Use flat standard primary buttons; reserve gradients for hero treatments
  - Do not bypass the token layer with raw `bg-cyan-*` adoption classes
  - Avoid adding more inline CSS variable style blocks where utilities suffice
  - Make the scope explicit as a **Phase 1 color-system rebrand**
  - Add dark-mode safety QA and accessibility checks
- Intentionally not expanded in this phase:
  - Typography redesign
  - Spacing redesign
  - Copy/UX rewrite

## Review Gate

This revised plan is saved to `redesign.md` per user preference and is intended for Claude review before any implementation starts.
