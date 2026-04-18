# Quickstart: Course-First Platform Refactor

## Goal

Validate the course-first catalog, overview, auth-gated learning entry, and in-context tutor flow after implementation.

## Prerequisites

- Backend dependencies installed in `.venv`
- Frontend dependencies installed in `frontend/node_modules`
- Database available for backend runtime validation
- Seed/import data available for `CS231n` and `CS224n`

## Validation Steps

### 1. Run backend tests for logging and core API behavior

```bash
.venv/bin/python -m unittest tests.test_log_hook -v
```

```bash
.venv/bin/python -m pytest tests -v
```

### 2. Run frontend static validation

```bash
cd frontend
npm run lint
npm run type-check
```

### 3. Start the backend

```bash
.venv/bin/python -m uvicorn src.api.app:app --reload
```

### 4. Start the frontend

```bash
cd frontend
npm run dev
```

### 5. Validate public catalog behavior

1. Open the home page.
2. Confirm `CS231n` and `CS224n` appear in the catalog.
3. Open each course overview.
4. Confirm `CS231n` exposes a start-learning action.
5. Confirm `CS224n` shows a coming-soon state and blocks learning entry.

### 6. Validate auth and skill-test gating

1. As an unauthenticated visitor, click start learning on `CS231n`.
2. Confirm the flow redirects to authentication without losing course context.
3. Sign in with a learner who has not completed onboarding/skill test.
4. Confirm the flow routes through onboarding and skill test before learning entry.

### 7. Validate recommendation-aware catalog

1. Complete the skill-test flow.
2. Return to the home catalog.
3. Confirm a recommended-courses view is available.
4. Confirm the all-courses view remains available.

### 8. Validate lecture experience

1. Start `CS231n`.
2. Enter a ready lesson or lecture.
3. Confirm AI Tutor appears within the learning page.
4. Confirm the legacy standalone tutor route redirects into the course-first experience.

## Exit Criteria

- Public catalog flow works.
- `CS231n` is startable.
- `CS224n` is visible but blocked as coming soon.
- Auth and skill-test gating preserve course context.
- AI Tutor is accessible within the lecture page rather than via standalone navigation.
