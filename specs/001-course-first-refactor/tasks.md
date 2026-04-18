# Tasks: Course-First Platform Refactor

**Input**: Design documents from `/specs/001-course-first-refactor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/course-platform-api.md, quickstart.md

**Tests**: Backend contract tests, frontend route/component tests, and Playwright end-to-end tests are required for this refactor because the spec explicitly requires a complete regression matrix.

**Organization**: Tasks are grouped by user story to keep each delivery slice independently testable and shippable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Every task includes the primary file path(s) that must be changed

## Path Conventions

- Backend runtime code lives in `src/`
- Frontend runtime code lives in `frontend/`
- Backend tests live in `tests/`
- Frontend tests live in `frontend/tests/`
- Database migrations live in `alembic/versions/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the missing test and fixture scaffolding needed before course-platform implementation starts.

- [ ] T001 Update frontend test scripts and dev dependencies in `frontend/package.json`
- [ ] T002 [P] Create Vitest configuration for route and component tests in `frontend/vitest.config.ts`
- [ ] T003 [P] Create frontend test bootstrap and mocks in `frontend/tests/setup.ts`
- [ ] T004 [P] Create Playwright configuration for catalog-to-learning flows in `frontend/playwright.config.ts`
- [ ] T005 [P] Create bootstrap fixture files for demo courses in `data/course_bootstrap/courses.json` and `data/course_bootstrap/overviews.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the canonical course-platform domain, migrations, shared backend services, and frontend API helpers that all user stories depend on.

**⚠️ CRITICAL**: No user story work should start before this phase is complete.

- [ ] T006 Create canonical course-platform ORM models in `src/models/course.py`
- [ ] T007 [P] Register the new course-platform models in `src/models/__init__.py`
- [ ] T008 [P] Create course-platform API schemas in `src/schemas/course.py`
- [ ] T009 Create the course-platform schema migration in `alembic/versions/20260418_course_platform_schema.py`
- [ ] T010 [P] Create bootstrap and import helpers for course-platform data in `src/services/course_bootstrap_service.py`
- [ ] T011 [P] Create shared course catalog query service skeleton in `src/services/course_catalog_service.py`
- [ ] T012 [P] Create start-learning decision service skeleton in `src/services/course_entry_service.py`
- [ ] T013 [P] Create learning-unit service skeleton in `src/services/learning_unit_service.py`
- [ ] T014 Create the shared course router and wire it into the API app in `src/routers/courses.py` and `src/api/app.py`
- [ ] T015 [P] Extend frontend course API clients and domain types in `frontend/lib/api.ts` and `frontend/types/index.ts`
- [ ] T016 [P] Create shared course gating helpers for blocked and gated entry states in `frontend/lib/course-gate.ts`

**Checkpoint**: The repo now has one canonical course-platform domain and shared contracts that all user stories can build on.

---

## Phase 3: User Story 1 - Discover And Enter A Course (Priority: P1) 🎯 MVP

**Goal**: Deliver a public home page that lists both demo courses, lets visitors open overview pages, and correctly differentiates `ready` versus `coming_soon`.

**Independent Test**: Open the public home page, verify `CS231n` and `CS224n` both appear, open both overview pages, and confirm only `CS231n` exposes a learnable CTA.

### Tests for User Story 1

- [ ] T017 [P] [US1] Add backend contract tests for `GET /api/courses` and `GET /api/courses/{course_slug}/overview` in `tests/contract/test_course_catalog_api.py`
- [ ] T018 [P] [US1] Add frontend route tests for the public catalog and course overview states in `frontend/tests/routes/course-catalog.test.tsx`
- [ ] T019 [P] [US1] Add the Playwright public discovery journey in `frontend/tests/e2e/course-discovery.spec.ts`

### Implementation for User Story 1

- [ ] T020 [US1] Implement authoritative catalog and overview read queries in `src/services/course_catalog_service.py`
- [ ] T021 [US1] Implement CS231n and CS224n bootstrap ingestion using server-side records in `src/services/course_bootstrap_service.py` and `src/services/ingestion.py`
- [ ] T022 [US1] Expose public catalog and overview endpoints in `src/routers/courses.py`
- [ ] T023 [P] [US1] Build reusable catalog cards and status badge components in `frontend/components/course/CourseCatalog.tsx` and `frontend/components/course/CourseStatusBadge.tsx`
- [ ] T024 [P] [US1] Build the course overview presentation component in `frontend/components/course/CourseOverview.tsx`
- [ ] T025 [US1] Replace the auth-first root redirect with the public catalog home in `frontend/app/page.tsx`
- [ ] T026 [US1] Create the public course overview route in `frontend/app/courses/[courseSlug]/page.tsx`
- [ ] T027 [US1] Add consistent coming-soon messaging and blocked deep-link handling in `frontend/app/courses/[courseSlug]/page.tsx` and `frontend/lib/course-gate.ts`

**Checkpoint**: The MVP course catalog and overview flow is functional and can be demonstrated without login.

---

## Phase 4: User Story 2 - Personalized Catalog After Skill Test (Priority: P2)

**Goal**: Preserve the existing auth and skill-test gate so learners can start from overview, be routed through required onboarding, then return to a personalized catalog with recommended and all-courses views.

**Independent Test**: As a new learner, click start from `CS231n`, complete auth and the required skill-test flow, then confirm the home page shows both a recommended view and an all-courses view without dead ends.

### Tests for User Story 2

- [ ] T028 [P] [US2] Add backend contract tests for `POST /api/courses/{course_slug}/start` and recommendation-aware catalog responses in `tests/contract/test_course_start_api.py`
- [ ] T029 [P] [US2] Add frontend tests for auth-gated start behavior and recommended versus all-courses tabs in `frontend/tests/routes/personalized-catalog.test.tsx`
- [ ] T030 [P] [US2] Add the Playwright auth-to-skill-test course-entry flow in `frontend/tests/e2e/course-gating.spec.ts`

### Implementation for User Story 2

- [ ] T031 [US2] Implement start-learning decision logic with preserved course context in `src/services/course_entry_service.py`
- [ ] T032 [US2] Extend assessment and recommendation services to return course recommendation payloads in `src/services/assessment_service.py` and `src/services/recommendation_engine.py`
- [ ] T033 [US2] Add the start-learning endpoint and recommendation-aware catalog behavior in `src/routers/courses.py`
- [ ] T034 [P] [US2] Create catalog view state management for recommended and all-courses tabs in `frontend/stores/courseCatalogStore.ts`
- [ ] T035 [US2] Render recommended and all-courses catalog tabs on the public home shell in `frontend/app/page.tsx` and `frontend/components/course/CourseCatalog.tsx`
- [ ] T036 [US2] Route learning entry through auth, onboarding, and skill-test gates in `frontend/stores/authStore.ts` and `frontend/middleware.ts`

**Checkpoint**: Authenticated learners can re-enter the same course context after completing the skill-test gate and can switch between recommended and full catalog views.

---

## Phase 5: User Story 3 - Learn Inside A Unified Lecture Experience (Priority: P3)

**Goal**: Move learning into a canonical course unit route and embed AI Tutor inside that page instead of keeping `/tutor` as a standalone experience.

**Independent Test**: Start `CS231n`, enter a ready learning unit, confirm the lecture page loads with in-context tutor UI, then open `/tutor` and verify it redirects back into the course-first flow.

### Tests for User Story 3

- [ ] T037 [P] [US3] Add backend contract tests for `GET /api/courses/{course_slug}/units/{unit_slug}` and legacy tutor compatibility in `tests/contract/test_learning_unit_api.py`
- [ ] T038 [P] [US3] Add frontend tests for the unified learning page and in-context tutor behavior in `frontend/tests/routes/learning-unit.test.tsx`
- [ ] T039 [P] [US3] Add the Playwright lecture and tutor journey in `frontend/tests/e2e/lecture-tutor.spec.ts`

### Implementation for User Story 3

- [ ] T040 [US3] Add legacy lecture-to-learning-unit mapping and tutor context persistence in `src/models/store.py` and `src/services/learning_unit_service.py`
- [ ] T041 [US3] Implement `GET /api/courses/{course_slug}/units/{unit_slug}` in `src/services/learning_unit_service.py` and `src/routers/courses.py`
- [ ] T042 [US3] Bind tutor question context to active learning units in `src/services/llm_service.py` and `src/services/history_service.py`
- [ ] T043 [P] [US3] Create the protected canonical learning route in `frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx`
- [ ] T044 [P] [US3] Build the unified lecture shell and in-context tutor UI in `frontend/components/learn/LearningUnitShell.tsx` and `frontend/components/learn/InContextTutor.tsx`
- [ ] T045 [US3] Replace the standalone tutor surface with a compatibility redirect in `frontend/app/(protected)/tutor/page.tsx`
- [ ] T046 [US3] Update legacy protected learn entry points to route into canonical course units in `frontend/app/(protected)/learn/page.tsx` and `frontend/app/(protected)/learn/[topicId]/page.tsx`

**Checkpoint**: Ready-course learning is course-first end to end, and the tutor is only accessible inside the active unit experience.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Clean up navigation, lock in architecture notes, add shared fixtures, and run the end-to-end validation matrix.

- [ ] T047 [P] Update navigation to surface the catalog-first flow in `frontend/components/layout/TopNav.tsx` and `frontend/components/layout/Sidebar.tsx`
- [ ] T048 [P] Document server-authoritative data architecture and import boundaries in `docs/course-platform-architecture.md`
- [ ] T049 [P] Add shared backend and frontend course-platform fixtures in `tests/fixtures/course_platform/README.md` and `frontend/tests/fixtures/coursePlatform.ts`
- [ ] T050 Run the full quickstart validation matrix and record any command updates in `specs/001-course-first-refactor/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no dependencies and should start immediately.
- **Phase 2: Foundational** depends on Phase 1 and blocks all user story work.
- **Phase 3: US1** depends on Phase 2 and is the MVP slice.
- **Phase 4: US2** depends on Phase 2 and the public catalog shell from US1.
- **Phase 5: US3** depends on Phase 2 and the canonical course catalog and entry flow established in US1.
- **Phase 6: Polish** depends on the user stories that are in scope for the release.

### User Story Dependencies

- **US1 (P1)**: No dependency on later stories; this is the first deliverable.
- **US2 (P2)**: Reuses the catalog and overview entry points from US1, but remains independently testable once they exist.
- **US3 (P3)**: Reuses the course catalog and learning-entry decisions from US1 and US2 while remaining independently testable as the lecture slice.

### Within Each User Story

- Write the listed tests first and confirm they fail before implementing the story.
- Finish backend contract changes before wiring frontend data fetching.
- Finish route and state integration before polishing navigation.
- Validate the story independently before moving to the next priority.

### Parallel Opportunities

- Phase 1 tasks `T002` to `T005` can run in parallel after `T001`.
- In Phase 2, `T007`, `T008`, `T010`, `T011`, `T012`, `T013`, `T015`, and `T016` can run in parallel once `T006` is established.
- In US1, `T017`, `T018`, and `T019` can run in parallel, and `T023` plus `T024` can run in parallel.
- In US2, `T028`, `T029`, and `T030` can run in parallel, and `T034` can run alongside backend work `T031` to `T033`.
- In US3, `T037`, `T038`, and `T039` can run in parallel, and `T043` plus `T044` can run in parallel.
- In Phase 6, `T047`, `T048`, and `T049` can run in parallel before `T050`.

---

## Parallel Example: User Story 1

```bash
# Test-first work for US1
Task: "Add backend contract tests for GET /api/courses and GET /api/courses/{course_slug}/overview in tests/contract/test_course_catalog_api.py"
Task: "Add frontend route tests for the public catalog and course overview states in frontend/tests/routes/course-catalog.test.tsx"
Task: "Add the Playwright public discovery journey in frontend/tests/e2e/course-discovery.spec.ts"

# UI component work for US1
Task: "Build reusable catalog cards and status badge components in frontend/components/course/CourseCatalog.tsx and frontend/components/course/CourseStatusBadge.tsx"
Task: "Build the course overview presentation component in frontend/components/course/CourseOverview.tsx"
```

---

## Parallel Example: User Story 2

```bash
# Test-first work for US2
Task: "Add backend contract tests for POST /api/courses/{course_slug}/start and recommendation-aware catalog responses in tests/contract/test_course_start_api.py"
Task: "Add frontend tests for auth-gated start behavior and recommended versus all-courses tabs in frontend/tests/routes/personalized-catalog.test.tsx"
Task: "Add the Playwright auth-to-skill-test course-entry flow in frontend/tests/e2e/course-gating.spec.ts"

# Implementation work for US2
Task: "Implement start-learning decision logic with preserved course context in src/services/course_entry_service.py"
Task: "Create catalog view state management for recommended and all-courses tabs in frontend/stores/courseCatalogStore.ts"
```

---

## Parallel Example: User Story 3

```bash
# Test-first work for US3
Task: "Add backend contract tests for GET /api/courses/{course_slug}/units/{unit_slug} and legacy tutor compatibility in tests/contract/test_learning_unit_api.py"
Task: "Add frontend tests for the unified learning page and in-context tutor behavior in frontend/tests/routes/learning-unit.test.tsx"
Task: "Add the Playwright lecture and tutor journey in frontend/tests/e2e/lecture-tutor.spec.ts"

# UI work for US3
Task: "Create the protected canonical learning route in frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx"
Task: "Build the unified lecture shell and in-context tutor UI in frontend/components/learn/LearningUnitShell.tsx and frontend/components/learn/InContextTutor.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 as the first demoable slice.
3. Validate public catalog, overview, `CS231n` readiness, and `CS224n` coming-soon behavior.
4. Commit a reversible checkpoint before starting personalized or lecture work.

### Incremental Delivery

1. Setup plus Foundational creates the shared course platform.
2. US1 delivers public discovery and overview.
3. US2 restores the personalized catalog and auth-gated start behavior.
4. US3 completes the canonical learning route and in-context tutor experience.
5. Polish locks in navigation, docs, fixtures, and end-to-end validation.

### Commit Strategy

1. Commit after Setup and Foundational complete.
2. Commit after each user story checkpoint.
3. Commit after Polish and validation complete.
4. Keep each commit reversible and scoped to one logical slice.

---

## Notes

- `CS231n` must remain the only demo course that is learnable in this phase.
- `CS224n` must remain visible but blocked with a consistent `coming_soon` state across catalog, overview, and deep-link flows.
- Repository `data/` files remain import/bootstrap inputs only; runtime UI must read server-managed data through API contracts.
- The standalone `/tutor` surface is compatibility-only after this refactor and must not remain a primary entry point.
