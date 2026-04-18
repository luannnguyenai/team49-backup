# Course-First Platform Refactor — Quickstart Validation

> Run these commands to validate the full course-platform refactor.

## Prerequisites

```bash
# Ensure you're in the project root
cd /mnt/shared/AI-Thuc-Chien/A20-App-049

# Backend virtualenv should be active
source .venv/bin/activate
```

## 1. Backend Validation

### Foundation Tests (Phase 2)

```bash
.venv/bin/python -m unittest tests.test_course_platform_foundation -v
```

**Expected**: 3 tests pass — enums, model tables/relationships, response schema shape.

### Catalog Contract Tests (US1)

```bash
.venv/bin/python -m unittest tests.contract.test_course_catalog_api -v
```

**Expected**: 3 tests pass — both demo courses listed, CS231n ready overview, CS224n blocked overview.

### Start/Recommendation Contract Tests (US2)

```bash
.venv/bin/python -m unittest tests.contract.test_course_start_api -v
```

**Expected**: 6 tests pass — auth gate, course unavailable, 404, response shape, all-courses view, recommendations.

### Learning Unit Contract Tests (US3)

```bash
.venv/bin/python -m unittest tests.contract.test_learning_unit_api -v
```

**Expected**: 6 tests pass — unit payload, 404s, tutor context binding, contract shape, multi-unit access.

### All Backend Tests (Combined)

```bash
.venv/bin/python -m unittest \
  tests.test_course_platform_foundation \
  tests.contract.test_course_catalog_api \
  tests.contract.test_course_start_api \
  tests.contract.test_learning_unit_api \
  -v
```

**Expected**: 18 tests pass, 0 failures.

## 2. Frontend Validation

### TypeScript Type Check

```bash
cd frontend && ./node_modules/.bin/tsc --noEmit
```

**Expected**: Zero type errors.

### Vitest Route Tests

```bash
cd frontend && node ./node_modules/.bin/vitest run
```

**Expected**: 3 test files, 15 tests pass:
- `course-catalog.test.tsx` (3 tests) — US1 public catalog
- `personalized-catalog.test.tsx` (6 tests) — US2 recommended tabs
- `learning-unit.test.tsx` (6 tests) — US3 unified lecture

### Playwright E2E (requires running dev servers)

```bash
cd frontend && npx playwright test tests/e2e/
```

**Expected**: Course discovery, gating, and lecture-tutor journeys pass.

## 3. Validation Matrix

| Phase | Suite | Tests | Command |
|-------|-------|-------|---------|
| Foundation | `test_course_platform_foundation` | 3 | `.venv/bin/python -m unittest tests.test_course_platform_foundation -v` |
| US1 Backend | `test_course_catalog_api` | 3 | `.venv/bin/python -m unittest tests.contract.test_course_catalog_api -v` |
| US1 Frontend | `course-catalog.test.tsx` | 3 | `cd frontend && vitest run tests/routes/course-catalog.test.tsx` |
| US2 Backend | `test_course_start_api` | 6 | `.venv/bin/python -m unittest tests.contract.test_course_start_api -v` |
| US2 Frontend | `personalized-catalog.test.tsx` | 6 | `cd frontend && vitest run tests/routes/personalized-catalog.test.tsx` |
| US3 Backend | `test_learning_unit_api` | 6 | `.venv/bin/python -m unittest tests.contract.test_learning_unit_api -v` |
| US3 Frontend | `learning-unit.test.tsx` | 6 | `cd frontend && vitest run tests/routes/learning-unit.test.tsx` |
| TypeScript | `tsc --noEmit` | — | `cd frontend && tsc --noEmit` |
| **Total** | | **33** | |

## 4. Manual Smoke Tests

### Public Catalog (US1)

1. Navigate to `/` — both CS231n and CS224n should appear
2. CS231n card shows "Available now" badge with "Start learning" CTA
3. CS224n card shows "Coming soon" badge with disabled CTA
4. Click CS231n overview → loads with "Start learning" button enabled
5. Click CS224n overview → loads with "Coming soon" button disabled

### Personalized Catalog (US2)

1. Sign in with test credentials
2. If recommendations exist → tab bar with "Recommended for you" / "All courses"
3. If no recommendations → all-courses view without tabs
4. Welcome message shows user's first name

### Unified Lecture Experience (US3)

1. Navigate to `/courses/cs231n/learn/lecture-1-introduction`
2. Video player loads with lecture content
3. "AI Tutor" toggle button visible in breadcrumb bar
4. Click "AI Tutor" → chat panel opens on the right
5. Ask a question → streaming response from tutor
6. Navigate to `/tutor` → shows compatibility banner with "Go to courses" link
7. Navigate to `/learn` → redirects to `/` (course catalog)

### Navigation (Phase 6)

1. Top nav shows "Courses" link pointing to `/`
2. Sidebar shows "Courses" link pointing to `/`
3. Standalone "AI Tutor" and "Học" links are removed from nav
4. Legacy `/tutor` still works but shows redirect banner
