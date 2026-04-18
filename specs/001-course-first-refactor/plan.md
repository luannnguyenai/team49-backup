# Implementation Plan: Course-First Platform Refactor

**Branch**: `001-course-first-refactor` | **Date**: 2026-04-18 | **Spec**: [spec.md](/mnt/shared/AI-Thuc-Chien/A20-App-049/specs/001-course-first-refactor/spec.md)
**Input**: Feature specification from `/specs/001-course-first-refactor/spec.md`

## Summary

Refactor the product into a course-first platform where the public home page lists all courses, each course has an overview page, `CS231n` is learnable, `CS224n` is visible but coming soon, and AI Tutor becomes part of the lecture experience rather than a standalone page. The implementation will normalize the content domain around server-managed course metadata, keep repository `data/` files as import sources only, and introduce a stable API contract for catalog, overview, learning entry, and lecture context.

## Technical Context

**Language/Version**: Python 3.12 backend, TypeScript 5 frontend  
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, Next.js 14 App Router, React 18, Zustand, Axios  
**Storage**: PostgreSQL for authoritative application data, server-managed object storage for binary course assets, repository `data/` files for bootstrap/import only  
**Testing**: Python unittest/pytest for backend and tooling, frontend route/component tests to be added with Vitest + Testing Library, end-to-end flow coverage to be added with Playwright  
**Target Platform**: Linux-hosted web application with browser clients  
**Project Type**: Full-stack web application with Next.js frontend and FastAPI backend  
**Performance Goals**: Course catalog and overview endpoints return in under 300 ms p95 in local validation; ready-course learning entry does not require more than one redirect after auth gating  
**Constraints**: Preserve existing auth and skill-test behavior, remove standalone tutor as a primary flow, prevent client runtime from depending on repository data files, maintain reversible commit checkpoints  
**Scale/Scope**: Immediate scope covers 2 demo courses, current web app routes, normalized course metadata, learning-entry routing, and a full regression test matrix for catalog-to-lecture flow

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file at `.specify/memory/constitution.md` is still an unfilled template and does not define enforceable project principles. No formal constitution gate blocks planning. For this feature, repository-level instructions remain the effective guardrails:

- Use test-first changes for behavior updates and refactor safety.
- Keep commits small and reversible.
- Do not treat repository `data/` files as production runtime sources.
- Verify user-facing routing and logging behavior before claiming completion.

**Gate Result (pre-design)**: PASS with informational note that the project constitution must be formalized separately.

## Project Structure

### Documentation (this feature)

```text
specs/001-course-first-refactor/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── course-platform-api.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── api/
├── dependencies/
├── models/
├── routers/
├── schemas/
├── services/
└── utils/

frontend/
├── app/
│   ├── (auth)/
│   ├── (protected)/
│   ├── assessment/
│   ├── module-test/
│   ├── onboarding/
│   └── quiz/
├── components/
├── lib/
├── stores/
└── types/

tests/
```

**Structure Decision**: Keep the existing monorepo-style split with FastAPI code under `src/` and Next.js code under `frontend/`, but refactor both sides toward a single course-first domain. Avoid introducing a new top-level backend package. New API contracts, normalized content schemas, frontend route replacements, and regression tests should all be added within the existing structure.

## Complexity Tracking

No constitution violations require justification at planning time.
