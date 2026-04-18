# Main vs Hybrid Review

## Scope

This document compares:

- `main` at `cc14d53`
- `hybrid/integrate-db-review` at the current working state

The goal is not to pick a "winner" in the abstract. The goal is to decide:

- which branch is the better product baseline
- which parts from `main` are worth porting into `hybrid`
- which parts should not be merged back because they conflict with the current product direction

## Executive Summary

`hybrid/integrate-db-review` is the better branch to continue product development.

Reason:

- it already implements the `course-first` product flow
- it has the public catalog, overview, gated start flow, learning unit route, and in-context AI Tutor
- it has broader automated verification and clearer hybrid backend boundaries

`main` is still valuable, but mainly as a source of infra and persistence improvements.

The highest-value items to consider porting from `main` into `hybrid` are:

- `pgvector` and database/runtime setup improvements
- any `schema v1` changes that strengthen canonical persistence
- startup and environment improvements such as `start.sh` behavior

Do not merge `main` into `hybrid` blindly. Port only the pieces that improve infra without pulling the product direction backward.

## Product Direction

### `main`

Current root flow in `main` is still auth-first:

- [frontend/app/page.tsx](/mnt/shared/AI-Thuc-Chien/A20-App-049/frontend/app/page.tsx:1) redirects users away from `/`
- unauthenticated users are sent to `/login`
- authenticated users are sent toward `/dashboard`

This is still closer to:

- LMS-first
- lecture-first
- authenticated shell first, then content

### `hybrid`

`hybrid` is already course-first:

- [frontend/app/page.tsx](/mnt/shared/AI-Thuc-Chien/A20-App-049/frontend/app/page.tsx:1) renders the public catalog
- [frontend/app/courses/[courseSlug]/page.tsx](/mnt/shared/AI-Thuc-Chien/A20-App-049/frontend/app/courses/[courseSlug]/page.tsx:1) renders course overview
- [frontend/app/courses/[courseSlug]/start/page.tsx](/mnt/shared/AI-Thuc-Chien/A20-App-049/frontend/app/courses/[courseSlug]/start/page.tsx:1) preserves the gated start flow
- [frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx](/mnt/shared/AI-Thuc-Chien/A20-App-049/frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx:1) is the protected learning entry

This matches the current intended product:

- `Home -> Course -> Overview -> Start -> auth/onboarding/assessment -> Learning Unit -> AI Tutor`

Decision:

- keep `hybrid`
- avoid restoring `main` root redirect behavior

## Frontend Architecture

### `main`

Strengths:

- simpler surface area
- fewer new abstractions

Weaknesses:

- no public course-first landing flow
- tutor/learn experience is still shaped around older routes and legacy entry points
- fewer explicit view-model/presenter boundaries

### `hybrid`

Strengths:

- presenter-oriented course platform pieces such as [frontend/features/course-platform/presenters.ts](/mnt/shared/AI-Thuc-Chien/A20-App-049/frontend/features/course-platform/presenters.ts:1)
- dedicated catalog state at [frontend/stores/courseCatalogStore.ts](/mnt/shared/AI-Thuc-Chien/A20-App-049/frontend/stores/courseCatalogStore.ts:1)
- compatibility redirects for legacy routes instead of keeping them as primary product routes
- learning shell and tutor are in-context rather than standalone

Weaknesses:

- bigger surface area to maintain
- some pages still carry transitional logic while the old stack is being isolated

Decision:

- keep `hybrid` frontend structure
- if anything is taken from `main`, it should be visual polish or specific UI details, not route behavior

## Backend API and App Layer

### `main`

At [src/api/app.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/api/app.py:1), `main` still behaves like a unified API plus legacy static UI host:

- serves static HTML at `/`
- centers lecture routes early in the app
- uses permissive CORS defaults

Strengths:

- simpler operational picture
- recent runtime work in `main` likely includes improvements around DB startup and schema rollout

Weaknesses:

- backend root still reflects legacy UI assumptions
- no canonical course API surface comparable to `courses_router`

### `hybrid`

At [src/api/app.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/api/app.py:1), `hybrid` improves the app layer:

- explicit backend landing at `/`
- Redis lifecycle wiring
- `DomainError` handler
- explicit CORS config
- mounted `courses_router`
- lecture stack retained but treated as a compatibility/adapter layer

Decision:

- keep `hybrid` app/API architecture
- port only startup/runtime improvements from `main` that do not revert the route model

## Data Model and Persistence

### `main`

Strengths:

- solid existing LMS learning schema in [src/models/learning.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/models/learning.py:1)
- latest `main` commit explicitly mentions:
  - `pgvector`
  - `fix start.sh`
  - `add schema v1`

These changes matter for production readiness.

### `hybrid`

Strengths:

- canonical course platform ORM at [src/models/course.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/models/course.py:1)
- explicit course-first concepts:
  - `Course`
  - `CourseOverview`
  - `CourseSection`
  - `LearningUnit`
  - `CourseAsset`
  - course recommendation/progress and legacy lecture mapping
- repository rollout into:
  - auth/user
  - recommendations
  - history
  - assessment

Weaknesses:

- some runtime course metadata still comes from bootstrap JSON via [src/services/course_bootstrap_service.py](/mnt/shared/AI-Thuc-Chien/A20-App-049/src/services/course_bootstrap_service.py:1)
- canonical DB-backed serving for all course metadata is not fully complete yet

Decision:

- keep `hybrid` canonical course model
- port persistence/runtime upgrades from `main` if they strengthen DB authority
- specifically review `pgvector` and `schema v1` for selective adoption

## AI Tutor and Learning Flow

### `main`

Strengths:

- established lecture/transcript stack
- fewer moving parts if used only as a lecture Q&A system

Weaknesses:

- product shape remains closer to standalone lecture/tutor behavior

### `hybrid`

Strengths:

- tutor is embedded in learning context
- async tutor route fixes and adapter isolation are already in place
- legacy lecture layer is being treated as a bridge, not the primary product model

Decision:

- keep `hybrid` tutor flow
- only port infra improvements from `main`, not legacy-first interaction patterns

## Auth, Security, and Runtime Hardening

### `main`

Unknown or weaker relative position from the current comparison.

### `hybrid`

Already includes:

- Redis-backed rate limit fallback
- token denylist guards
- logout revoke endpoint
- frontend logout calling backend revoke
- more explicit CORS and startup behavior

Decision:

- keep `hybrid`
- only port operational improvements from `main` if they do not overlap or regress these controls

## Testing and Verification

### `main`

Much lighter verification surface relative to `hybrid`.

### `hybrid`

Has broader coverage across:

- frontend route tests
- frontend unit tests
- Playwright e2e
- backend contract tests
- backend repository tests
- auth/config/runtime regression tests

Decision:

- keep `hybrid` as the verification baseline
- any port from `main` should be validated against this existing suite

## Keep / Port / Avoid Matrix

### Keep from `hybrid`

- `course-first` routes and user journey
- `courses_router` and course API contracts
- canonical course ORM
- in-context tutor flow
- presenter/store/frontend orchestration for catalog and overview
- auth redirect preservation across onboarding and assessment
- Redis rate-limit + denylist + logout revoke
- repository layer already rolled out in hybrid
- test matrix and docs

### Port from `main`

- `pgvector` adoption where it improves tutor retrieval or future recommendation/search
- `schema v1` changes that improve authoritative persistence
- `start.sh` and startup/runtime fixes
- environment or compose fixes that simplify local/prod boot

### Avoid pulling from `main`

- auth-first root redirect behavior
- backend root serving the old static UI as the primary experience
- product flows that make tutor or lecture the entry point again
- anything that reintroduces legacy-first UX over the course-first shell

## Recommended Next Step

Do a focused review of these `main` artifacts and decide whether to port them:

1. `cc14d53` runtime changes:
   - `pgvector`
   - `start.sh`
   - `schema v1`
2. any migration files that strengthen DB authority without conflicting with:
   - `src/models/course.py`
   - `src/routers/courses.py`
   - course-first frontend routes

The recommended integration strategy is:

- keep developing on `hybrid/integrate-db-review`
- port selected infra/database changes from `main`
- do not use `main` as the merge base for product behavior

## Immediate Port Status

The first safe slice has already proven low-risk and high-value:

- `docker-compose.yml`
  - port `pgvector/pgvector:pg16` for the database image
- `start.sh`
  - port cross-platform frontend image timestamp parsing via `python3`
  - port crash-loop detection for the backend container before `docker compose up`

These changes improve local/runtime resilience without changing product behavior.

The `schema v1` migration from `main` is not in the same category.

It should stay under review only, because it directly mutates legacy LMS entities such as:

- `questions`
- `topics`
- `modules`
- `knowledge_components`

That migration may still contain useful ideas, but it should not be ported wholesale into `hybrid`.

For the same audit window, `main` did not add new dependency/runtime package changes in:

- `pyproject.toml`
- `requirements.txt`
- `uv.lock`

So there is no immediate package-level port to perform from `cc14d53`.

## Final Decision

If the question is "which branch should the team continue from?", the answer is:

- `hybrid/integrate-db-review`

If the question is "does `main` still contain valuable work?", the answer is:

- yes, mainly for infra, DB runtime, and startup improvements

If the question is "can we combine them?", the answer is:

- yes, but only by selectively porting infra/persistence improvements from `main` into `hybrid`
- not by merging the product behavior of `main` back over `hybrid`
