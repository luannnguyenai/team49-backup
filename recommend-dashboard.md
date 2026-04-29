# Recommendation + Dashboard Consistency Plan

## Goal

Make recommendation behavior consistent across:

- `/learn` personalized planner
- dashboard tab `Dành cho bạn`
- global search in the top navigation

Add a global search dropdown under the navigation search input on every `TopNav`, showing matching course results immediately without redirecting.

This change must stay isolated. Do not modify unrelated behavior in assessment, auth, planner generation core, or learning-unit runtime.

## Problem Summary

Today the product has three different concepts that look similar to the user but are backed by different code paths:

- `/learn` renders the current personalized learning path from planner output
- dashboard `Dành cho bạn` renders from the course catalog and currently falls back to all courses when there are no recommended flags
- search behavior is limited and not available consistently across all navigation shells

This creates a mismatch:

- `/learn` can correctly show only the 2 courses in the selected path
- dashboard `Dành cho bạn` can show the entire catalog
- users interpret both as “recommendations”, even though they are not driven by the same source

## Design Principles

1. Keep concepts separate.
- Planner path is not the same thing as course recommendation.
- Recommendation is not the same thing as search.

2. Make recommendation semantics honest.
- `Dành cho bạn` must only show recommended courses.
- It must not silently degrade into “all courses”.

3. Keep search global but isolated.
- Navigation search should only provide quick course discovery.
- It should not mutate planner state or dashboard recommendation logic.

4. Minimize blast radius.
- Only touch components and services directly responsible for recommendation annotation, dashboard rendering, and top-nav search dropdown.

## Source of Truth

### Personalized Planner

`/learn` remains driven by planner path generation and `plan_history.recommended_path_json`.

This semantic stays unchanged:

- `/learn` = current personalized path

### Recommended Courses

Recommended courses should resolve through one backend path:

1. Primary source: `course_recommendations`
2. Fallback source: `goal_preferences.selected_course_ids`

This ensures the course catalog can still expose coherent recommendations even when explicit `course_recommendations` rows have not been written yet.

### Global Search

Global search should use the course catalog as a search source and remain independent from planner state.

## Scope

### Allowed Changes

- frontend `TopNav` and related search dropdown UI/state
- frontend dashboard filtering/rendering for `Dành cho bạn`
- backend course catalog recommendation resolution
- directly related tests

### Not Allowed

- planner generation algorithm beyond reading existing recommendation scope
- assessment flow
- auth flow semantics
- learning-unit runtime
- unrelated page layouts or unrelated navigation logic
- any broad refactor outside recommendation/search/dashboard consistency

## Phase Plan

### Phase 1: Lock Semantics

Objective:
- Freeze the meaning of planner path, recommended courses, and global search before changing code.

Checklist:
- `/learn` continues to mean current personalized path
- dashboard `Dành cho bạn` means recommended courses only
- global nav search means quick course lookup only
- recommendation must not silently fall back to full catalog
- search dropdown must not change planner or recommendation state

Success criteria:
- clear behavior matrix exists for:
  - user has `course_recommendations`
  - user has no `course_recommendations` but has `goal_preferences.selected_course_ids`
  - user has neither

### Phase 2: Isolate Backend Recommendation Resolution

Objective:
- Make catalog recommendation annotation consistent with planner scope when explicit recommendation rows are absent.

Implementation direction:
- update `src/services/course_catalog_service.py`
- resolve recommended course slugs with precedence:
  - `course_recommendations`
  - fallback from `goal_preferences.selected_course_ids`

Checklist:
- `view="recommended"` returns only recommended courses
- `view="all"` returns the full catalog with correct `is_recommended` flags
- explicit recommendation rows override fallback goal scope
- no planner-generation rewrite

Success criteria:
- backend can produce a coherent recommended subset even without explicit `course_recommendations`

### Phase 3: Isolate Dashboard `Dành cho bạn`

Objective:
- Make dashboard recommendation behavior honest and consistent.

Implementation direction:
- update dashboard presenter/page logic
- remove current fallback from recommended tab to all courses

Checklist:
- `Dành cho bạn` only renders recommended courses
- if recommended set is empty, show an explicit empty state
- `Tất cả`, `Sẵn sàng`, `Sắp ra mắt` keep current behavior
- no hidden fallback to all catalog inside “for-you”

Success criteria:
- dashboard no longer misrepresents the full catalog as personalized recommendations

### Phase 4: Add Global Search Dropdown to Every `TopNav`

Objective:
- Expose the course search input consistently across all top navigation shells.

Implementation direction:
- render search input on every `TopNav`
- show a dropdown directly under the input while typing

Checklist:
- search bar visible on every page using `TopNav`
- dropdown appears directly under the search field
- dropdown supports:
  - loading state
  - matched results
  - empty state
- click outside closes dropdown
- selecting a result navigates to the target course page
- search interaction does not auto-redirect while the user types

Success criteria:
- users can type from any page and immediately see matching course results without leaving the page first

### Phase 5: Isolate Search Data Flow

Objective:
- Reuse course catalog data safely without creating a broad new search subsystem.

Implementation direction:
- prefer existing `courseApi.catalog({ includeUnavailable: true })`
- filter client-side for dropdown results
- keep the first version minimal and focused

Checklist:
- only course fields needed by dropdown are used
- query matches title and short description using existing search helpers where possible
- dropdown limits result count
- optional recommended badge can be shown from `is_recommended`
- planner store is not touched

Success criteria:
- dropdown search remains fast, local, and isolated

### Phase 6: Regression Boundaries

Objective:
- Ensure unrelated product areas are not altered.

Checklist:
- `/learn` still renders planner path as before
- assessment results CTA flow remains unchanged
- auth gating remains unchanged
- tutor and course pages only change insofar as they inherit the updated `TopNav`
- no unrelated navigation regressions

Success criteria:
- all changes remain inside recommendation/search/dashboard boundaries

### Phase 7: Verification

Objective:
- Prove the change set works locally and in Docker.

Checklist:
- targeted backend tests for recommendation resolution
- targeted frontend tests for dashboard and top-nav dropdown
- frontend type-check
- frontend production build
- Docker frontend dev build
- Docker frontend prod build

Success criteria:
- behavior is consistent in both local and Docker execution paths

## Expected UX After Change

### `/learn`

- continues to show the personalized path only
- if the selected path is `computer_vision`, it may still show only `CS230 + CS231n`
- if the selected path is `nlp`, it may still show only `CS230 + CS224n`

### Dashboard `Dành cho bạn`

- shows only recommended courses
- if recommendations are empty, it shows a clear empty state
- it no longer expands into the full catalog under the label “Dành cho bạn”

### Navigation Search

- search bar is available on every `TopNav`
- typing opens a dropdown under the input
- dropdown shows matching course results immediately
- clicking a result opens the corresponding course page

## Test Plan

### Backend Tests

- `view="recommended"` returns recommendation rows when `course_recommendations` exists
- `view="recommended"` falls back to `goal_preferences.selected_course_ids` when recommendation rows are absent
- `view="all"` annotates `is_recommended` correctly
- explicit recommendations override goal-scope fallback

### Frontend Tests

- `TopNav` search input renders on every top-nav shell
- typing opens dropdown results
- no-match query shows empty state
- click outside closes the dropdown
- clicking a dropdown result navigates correctly
- dashboard `Dành cho bạn` only shows recommended courses
- dashboard `Dành cho bạn` shows empty state when there are none

### Build Verification

- `npm --prefix frontend run type-check`
- `npm --prefix frontend run build`
- `docker compose build frontend`
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml build frontend`

## Non-Goals

- Do not redesign the planner
- Do not add a new backend search API unless existing catalog reuse proves insufficient
- Do not implement a broad omnibox for units, sections, tutor history, or other entities
- Do not rewrite onboarding path selection
- Do not expand recommendation scope beyond the existing goal-path model in this change

## Review Questions

Questions for review before implementation:

1. Is it acceptable that dashboard recommendation fallback is based on `goal_preferences.selected_course_ids` when explicit `course_recommendations` are absent?
2. Should the dropdown show unavailable courses as well, or only `ready` courses?
3. Should the dropdown open course overview pages for unavailable courses and start pages for ready courses, or always go to overview first?
4. Is a minimal result list sufficient, or should the dropdown include a “see all results” action later as a follow-up?
