# Mobile UX Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the frontend so core mobile flows feel intentionally designed for small screens without changing backend contracts, data shape, auth logic, or planner/learning business logic.

**Architecture:** This is a frontend-only remediation plan split by user flow: global navigation, public discovery, protected discovery, planner, and learning player. Each phase isolates visual structure and interaction-model changes behind presentational components and UI-only hooks so existing API/store/state logic remains intact.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript 5, Tailwind CSS, Zustand, Lucide React, existing frontend test stack with Vitest and route/component tests.

---

## Scope Guardrails

- Keep this plan frontend-only.
- Do not change backend API routes, response schemas, auth token format, learning-path payload shape, or planner recommendation logic.
- Do not change `lib/api.ts` request contracts unless a purely additive UI helper is unavoidable.
- Reuse existing stores and selectors whenever possible instead of moving state into new global stores.
- Prefer extracting UI wrappers over editing business logic in `presenters.ts`, `store.ts`, `profile.ts`, or canonical mapping utilities.

## Mobile UX Target

The mobile experience should optimize for three primary jobs:

1. Discover what to study.
2. Decide what to do next.
3. Study without losing context.

Desktop-only affordances that disappear on mobile must be converted into mobile-native affordances, not simply hidden.

## File Structure Map

### Existing files expected to change

- `frontend/app/globals.css`
  Central place for shared mobile spacing, bottom-safe-area, sheet, and navigation utility classes.

- `frontend/app/(protected)/layout.tsx`
  Protected shell padding and mobile viewport strategy.

- `frontend/components/layout/TopNav.tsx`
  Protected mobile header, search trigger behavior, mobile navigation model, reduced action density.

- `frontend/components/layout/PublicTopNav.tsx`
  Public mobile header and CTA prioritization.

- `frontend/components/layout/navItems.ts`
  Single source of truth for primary navigation and mobile nav prioritization.

- `frontend/components/landing/LandingPage.tsx`
  Public landing mobile hierarchy, hero density, section spacing, CTA order.

- `frontend/app/(protected)/dashboard/page.tsx`
  Mobile dashboard header, stats density, tab/filter control treatment, course card hierarchy.

- `frontend/components/course/CourseCatalog.tsx`
  Mobile card density and content priority.

- `frontend/components/course/CourseOverview.tsx`
  Mobile course-detail hierarchy and CTA placement.

- `frontend/components/course/CourseOverviewInteractive.tsx`
  Keep only interaction wiring; ensure new mobile layout remains presentational.

- `frontend/features/learning-path/components/LearningPathShell.tsx`
  View defaults, mobile-specific composition, graph/timeline gating, bottom-sheet integration.

- `frontend/features/learning-path/components/PlannerHeader.tsx`
  Mobile planner header prioritization, path switcher behavior, action grouping.

- `frontend/features/learning-path/components/ViewToggle.tsx`
  Mobile-first control sizing and graph/timeline treatment.

- `frontend/features/learning-path/components/TimelineBoard.tsx`
  Mobile weekly plan readability and collapsed/expanded behavior.

- `frontend/features/learning-path/components/RoadmapPlanner.tsx`
  Explicit mobile fallback strategy; may become tablet/desktop only.

- `frontend/features/learning-path/components/LearningUnitDrawer.tsx`
  Convert from side drawer semantics to mobile bottom-sheet semantics.

- `frontend/components/learn/LearningPageScreen.tsx`
  Mobile screen container spacing and full-bleed learning shell behavior.

- `frontend/components/learn/LearningUnitShell.tsx`
  Biggest mobile remediation area: lesson access, tutor access, checkpoints, overlays, action placement.

### New files likely to be added

- `frontend/components/layout/MobileBottomNav.tsx`
  Bottom navigation for protected mobile flows.

- `frontend/components/layout/MobileMenuSheet.tsx`
  Shared sheet for overflow/account actions if needed.

- `frontend/components/layout/MobileSearchSheet.tsx`
  Full-screen or sheet-based search UI using existing course-search logic.

- `frontend/components/ui/BottomSheet.tsx`
  Shared, reusable UI primitive for mobile sheets/drawers.

- `frontend/components/ui/SegmentedControl.tsx`
  Shared mobile-safe segmented control for dashboard/planner toggles.

- `frontend/components/learn/MobileStudyToolbar.tsx`
  Sticky mobile toolbar for Lessons, Tutor, and Key Ideas entry points.

- `frontend/components/learn/MobileLessonSheet.tsx`
  Mobile lesson list replacing hidden left desktop rail.

- `frontend/components/learn/MobileTutorSheet.tsx`
  Mobile wrapper around `InContextTutor`.

- `frontend/components/learn/MobileKeyIdeasSheet.tsx`
  Mobile wrapper around active chapter takeaways / timestamps.

- `frontend/tests/unit/layout/mobile-bottom-nav.test.tsx`
- `frontend/tests/unit/layout/mobile-search-sheet.test.tsx`
- `frontend/tests/routes/dashboard/mobile-layout.test.tsx`
- `frontend/tests/unit/learning-path/learning-unit-drawer-mobile.test.tsx`
- `frontend/tests/routes/learning/mobile-shell.test.tsx`

## Backend Isolation Rules

These files are treated as read-only from a logic perspective during this plan:

- `frontend/lib/api.ts`
- `frontend/features/learning-path/store.ts`
- `frontend/features/learning-path/presenters.ts`
- `frontend/features/dashboard/presenters.ts`
- `frontend/stores/authStore.ts`
- `frontend/lib/course-search.ts`
- `frontend/lib/course-catalog-cache.ts`
- `frontend/lib/*canonical*`

Allowed changes in these modules:

- Type-only imports
- New UI adapters that wrap existing results without changing returned values
- Additive helper selectors only if they do not alter existing behavior

Disallowed changes in these modules:

- Renaming response fields
- Reordering planner business logic
- Changing search/filter semantics
- Changing auth redirect rules
- Changing quiz unlock logic
- Changing course-start routing semantics

## Phase 0: Baseline, Tokens, and Safety Rails

**Objective:** Establish mobile-safe primitives before touching user-facing flows.

**Files**

- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/(protected)/layout.tsx`
- Create: `frontend/components/ui/BottomSheet.tsx`
- Create: `frontend/components/ui/SegmentedControl.tsx`
- Test: `frontend/tests/unit/tokens/decorative-tokens.test.tsx`

**Component changes**

- Add safe-area-aware spacing utilities for bottom nav, sheets, and sticky mobile actions.
- Standardize mobile interaction primitives: sheet container, sheet header, sticky footer, segmented controls.
- Adjust protected layout padding so content does not collide with future bottom navigation.

**Isolation strategy**

- No data flow changes.
- No route behavior changes.
- Only presentational wrappers and spacing primitives.

**Implementation breakdown**

- [ ] Add CSS tokens/utilities for `safe-area-inset-bottom`, mobile sticky footer spacing, and mobile sheet backdrop/container styles.
- [ ] Add a shared `BottomSheet` primitive with controlled open/close props and focus-safe close behavior.
- [ ] Add a shared `SegmentedControl` component for compact mobile tab/filter use.
- [ ] Update protected layout to reserve bottom space when mobile bottom navigation is active.
- [ ] Add or update tests for token classes and ensure no existing theme tests break.

**Definition of Done**

- [ ] Mobile-safe CSS utilities exist in one shared location.
- [ ] A reusable sheet primitive is available for planner and learning player.
- [ ] Protected layout supports sticky bottom UI without clipping content.
- [ ] No backend/store/business-logic files were modified.
- [ ] Existing layout/theme tests still pass.

## Phase 1: Global Mobile Navigation and Search

**Objective:** Replace compressed desktop header behavior with mobile-native navigation and search entry points.

**Files**

- Modify: `frontend/components/layout/TopNav.tsx`
- Modify: `frontend/components/layout/PublicTopNav.tsx`
- Modify: `frontend/components/layout/navItems.ts`
- Create: `frontend/components/layout/MobileBottomNav.tsx`
- Create: `frontend/components/layout/MobileMenuSheet.tsx`
- Create: `frontend/components/layout/MobileSearchSheet.tsx`
- Test: `frontend/tests/unit/layout/mobile-bottom-nav.test.tsx`
- Test: `frontend/tests/unit/layout/topnav-theme.test.tsx`

**Component changes**

- Protected area:
  Reduce top header to logo/title, primary page action, and compact menu/search triggers.
- Public area:
  Reduce CTA competition and give mobile users one primary action plus a menu/sheet path.
- Search:
  Move course search from inline compressed header input into a dedicated mobile sheet using existing course catalog + filtering utilities.
- Navigation:
  Introduce bottom nav for the most important protected destinations: `Dashboard`, `Learn`, `AI Assistant`, `History`, `Profile` or overflow.

**Isolation strategy**

- Reuse current `NAV_ITEMS`.
- Reuse existing course search functions and router pushes.
- Do not change route names or auth redirects.

**Implementation breakdown**

- [ ] Define mobile nav priority and overflow rules in `navItems.ts` without changing URLs.
- [ ] Extract mobile bottom navigation into its own component.
- [ ] Replace inline mobile search with a trigger that opens `MobileSearchSheet`.
- [ ] Keep desktop search/nav behavior intact above the mobile breakpoint.
- [ ] Refactor public top nav into compact mobile mode with one visible CTA and menu access to secondary actions.
- [ ] Add tests covering mobile search open/close, active nav state, and route-link integrity.

**Definition of Done**

- [ ] Protected mobile header fits on one line without content collision.
- [ ] Mobile users can access primary navigation without opening a crowded top menu.
- [ ] Search is usable on mobile as a focused flow, not as a compressed header input.
- [ ] Desktop nav behavior remains functionally unchanged.
- [ ] Route wiring and auth-dependent action behavior remain unchanged.

## Phase 2: Discovery Flow Remediation

**Objective:** Improve mobile-first readability and CTA clarity on landing, dashboard, catalog, and course overview flows.

**Files**

- Modify: `frontend/components/landing/LandingPage.tsx`
- Modify: `frontend/app/(protected)/dashboard/page.tsx`
- Modify: `frontend/components/course/CourseCatalog.tsx`
- Modify: `frontend/components/course/CourseOverview.tsx`
- Modify: `frontend/components/course/CourseOverviewInteractive.tsx`
- Test: `frontend/tests/unit/landing/landing-cta.test.tsx`
- Test: `frontend/tests/routes/dashboard/page.test.tsx`
- Test: `frontend/tests/routes/course/catalog.test.tsx`
- Test: `frontend/tests/routes/course/course-catalog.test.tsx`
- Test: `frontend/tests/routes/course/start.test.tsx`

**Component changes**

- Landing:
  Reduce above-the-fold density, tighten hero height, bring single CTA higher, reduce simultaneous card noise.
- Dashboard:
  Convert tab strip to mobile-safe segmented control or horizontal chips with scroll fallback.
- Dashboard stats:
  Reduce visual weight and prioritize progress/action instead of equal-size KPI boxes.
- Course catalog:
  Increase clarity of title, progress/status, and CTA; reduce decorative area on mobile.
- Course overview:
  Ensure start CTA and course status are visible early without long scroll.

**Isolation strategy**

- Preserve current course filtering, recommendation, and start-course behavior.
- Preserve `buildDashboardCourseCardModel` semantics.
- Preserve course overview start action and unauthorized redirect behavior.

**Implementation breakdown**

- [ ] Rework landing mobile hero and CTA grouping while preserving copy and route targets.
- [ ] Replace dashboard mobile tab treatment with shared segmented control or scrollable chip row.
- [ ] Reorder dashboard section blocks so “what to do next” appears before less critical summary content.
- [ ] Compress mobile course cards by lowering hero height and simplifying badge density.
- [ ] Rework course overview mobile layout to prioritize summary + CTA + next step.
- [ ] Update route/component tests to assert visible CTA and stable link behavior.

**Definition of Done**

- [ ] Landing mobile shows a clear primary CTA without excessive initial scroll.
- [ ] Dashboard filters are easy to use on narrow screens.
- [ ] Course cards remain readable and actionable at phone width.
- [ ] Course overview exposes the next action near the top on mobile.
- [ ] No search/filter/start behavior changed semantically.

## Phase 3: Planner Mobile-First Experience

**Objective:** Make the planner genuinely usable on phones by making timeline the default and turning detail exploration into sheet-driven flows.

**Files**

- Modify: `frontend/features/learning-path/components/LearningPathShell.tsx`
- Modify: `frontend/features/learning-path/components/PlannerHeader.tsx`
- Modify: `frontend/features/learning-path/components/ViewToggle.tsx`
- Modify: `frontend/features/learning-path/components/TimelineBoard.tsx`
- Modify: `frontend/features/learning-path/components/RoadmapPlanner.tsx`
- Modify: `frontend/features/learning-path/components/LearningUnitDrawer.tsx`
- Test: `frontend/tests/unit/learning-path/planner-header.test.tsx`
- Test: `frontend/tests/unit/learning-path/timeline-board.test.tsx`
- Test: `frontend/tests/unit/learning-path/learning-unit-drawer.test.tsx`
- Create: `frontend/tests/unit/learning-path/learning-unit-drawer-mobile.test.tsx`

**Component changes**

- Default phones to `timeline` view and visually de-emphasize graph mode on small screens.
- Convert drawer interaction into mobile bottom sheet semantics.
- Simplify planner header on mobile: path name, weekly target, and one primary planner action.
- Make weekly timeline cards easier to scan with shorter summaries and clearer lesson counts.
- Keep graph mode for tablet/desktop; mobile may show a “best on larger screens” hint or a simplified entry point.

**Isolation strategy**

- Preserve `useLearningPathStore`.
- Preserve `computeRecommendedNext`, path grouping, status semantics, and lesson selection IDs.
- Preserve `LearningUnitDrawer` content-fetch logic using existing `learningUnitApi.contentById`.

**Implementation breakdown**

- [ ] Update view-default behavior so mobile lands in timeline confidently and predictably.
- [ ] Rework `PlannerHeader` so the path switcher and actions do not crowd the title area on mobile.
- [ ] Tighten `TimelineBoard` card density and collapsed/expanded interaction for narrow screens.
- [ ] Convert `LearningUnitDrawer` into a responsive component: right drawer on desktop, bottom sheet on mobile.
- [ ] Decide graph-mode mobile handling explicitly: disabled below breakpoint, secondary mode, or simplified layout.
- [ ] Add tests for default mobile view, drawer open/close behavior, and lesson navigation inside the mobile sheet.

**Definition of Done**

- [ ] Planner is usable on phone width without relying on the graph canvas.
- [ ] Lesson details open in a mobile-native sheet, not a desktop-style side panel.
- [ ] Existing planner recommendation and progress logic is unchanged.
- [ ] Planner actions remain reachable without horizontal crowding.
- [ ] Unit-detail selection and start-learning links still work exactly as before.

## Phase 4: Learning Player Mobile Study Flow

**Objective:** Preserve study context on mobile by replacing hidden desktop side rails with explicit mobile tools.

**Files**

- Modify: `frontend/components/learn/LearningPageScreen.tsx`
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
- Create: `frontend/components/learn/MobileStudyToolbar.tsx`
- Create: `frontend/components/learn/MobileLessonSheet.tsx`
- Create: `frontend/components/learn/MobileTutorSheet.tsx`
- Create: `frontend/components/learn/MobileKeyIdeasSheet.tsx`
- Test: `frontend/tests/routes/learning/unit.test.tsx`
- Create: `frontend/tests/routes/learning/mobile-shell.test.tsx`
- Test: `frontend/tests/unit/tutor/in-context-tutor.test.tsx`

**Component changes**

- Add a sticky mobile study toolbar with three explicit actions:
  `Lessons`, `Tutor`, `Key ideas`.
- Convert lesson list into a mobile sheet instead of hiding it below `md`.
- Wrap `InContextTutor` in a mobile sheet instead of relying on right rail visibility.
- Move chapter takeaways and timestamps into a mobile sheet or accordion flow.
- Reposition floating checkpoint/quiz actions so they do not obstruct the video or core reading area.
- Keep desktop 3-column layout behavior intact.

**Isolation strategy**

- Preserve quiz checkpoint thresholds, session progression, answer submission, and completion logic.
- Preserve `InContextTutor` props and existing tutor integration contract.
- Preserve `courseSlug`, `unitSlug`, session storage, and history links.

**Implementation breakdown**

- [ ] Introduce `MobileStudyToolbar` with explicit study tools and safe-area-aware sticky placement.
- [ ] Extract lesson-list rendering into a reusable block that can mount in desktop rail and mobile sheet.
- [ ] Extract tutor mount into a reusable wrapper that can render in desktop rail and mobile sheet.
- [ ] Extract key ideas / timestamps into a mobile-friendly disclosure or sheet flow.
- [ ] Audit all absolute-positioned floating controls and move them away from video overlap on phones.
- [ ] Add tests for mobile toolbar actions, lesson navigation, tutor accessibility, and stable quiz behavior.

**Definition of Done**

- [ ] Mobile users can access lessons, tutor, and key ideas without hidden desktop rails.
- [ ] Video area is not blocked by overlapping CTA bubbles during normal use.
- [ ] Quiz behavior and progression remain unchanged logically.
- [ ] Desktop study layout still works.
- [ ] No backend or session contracts changed.

## Phase 5: Hardening, Regression Pass, and Visual Polish

**Objective:** Close mobile regressions, unify interaction patterns, and verify that the remediation did not break existing routes.

**Files**

- Modify: any touched frontend files from earlier phases only as needed for cleanup
- Test: all touched existing unit/route tests
- Create or update: targeted mobile regression tests only where gaps remain

**Verification matrix**

- Public landing on phone width
- Public auth entry points from header
- Protected header with authenticated user
- Dashboard discover flow
- Course catalog to course detail to start flow
- Planner timeline to lesson detail to start flow
- Learning player toolbar, tutor, key ideas, quiz overlays

**Isolation strategy**

- No new product behavior in this phase.
- Only cleanup, consistency, a11y, and regression fixes.

**Implementation breakdown**

- [ ] Run the targeted frontend unit and route test suite for all touched surfaces.
- [ ] Audit touch target sizes, sheet close affordances, and focus return behavior.
- [ ] Normalize spacing, sticky offsets, and safe-area padding across all mobile sheets/toolbars.
- [ ] Verify no route regressions, no broken deep links, and no desktop visual breakage at common breakpoints.
- [ ] Remove dead code from deprecated mobile header/menu/search implementations once replacements are proven stable.

**Definition of Done**

- [ ] All touched tests pass.
- [ ] Mobile interactions feel consistent across navigation, planner, and player flows.
- [ ] No logic regressions were introduced in auth, planner, search, course-start, or quiz flows.
- [ ] Deprecated duplicate UI paths are removed or clearly isolated.

## Recommended Execution Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5

This order minimizes rework because shared mobile primitives and nav decisions should stabilize before planner/player work.

## Suggested Commit Boundaries

- `feat(ui): add mobile sheet and segmented control primitives`
- `feat(nav): redesign mobile navigation and search flows`
- `feat(discovery): optimize landing dashboard and catalog for mobile`
- `feat(planner): rework learning path mobile experience`
- `feat(learning): add mobile-first study tools and sheets`
- `test(ui): add mobile regression coverage and cleanup`

## Verification Commands

- `npm test -- --run tests/unit/layout/topnav-theme.test.tsx`
- `npm test -- --run tests/routes/dashboard/page.test.tsx`
- `npm test -- --run tests/routes/course/catalog.test.tsx`
- `npm test -- --run tests/unit/learning-path/timeline-board.test.tsx`
- `npm test -- --run tests/routes/learning/unit.test.tsx`
- `npm run type-check`
- `npm run build`

## Risks and Controls

- Risk: Mobile-specific branching in large components increases complexity.
  Control: Extract sheet/toolbars into dedicated files instead of adding more inline conditionals.

- Risk: Planner and learning shell are already large and easy to destabilize.
  Control: Treat business logic and rendering logic separately; extract presentational blocks before restyling.

- Risk: Search/navigation rewrites accidentally change route behavior.
  Control: Reuse existing router targets and add route-state tests around active links and search result navigation.

- Risk: Floating quiz/tutor UI conflicts with mobile viewport and safe areas.
  Control: Standardize all sticky/floating offsets on shared mobile spacing tokens.

## Out of Scope

- Backend API changes
- Store schema changes
- Planner recommendation algorithm changes
- Search algorithm changes
- New product features unrelated to mobile remediation
- Full visual redesign for desktop-only screens
