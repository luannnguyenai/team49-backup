# Replan Production E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/replan` prototype/demo scope with a production end-to-end flow that analyzes the learner's real current path, builds real review scope, starts a real assessment, and returns through existing `/assessment/results` and `/learn`.

**Architecture:** Add focused backend replan routes: `POST /api/replan/analyze` and `POST /api/replan/assessment/start`. The analyze route composes the existing replan keyword planner, unit discovery, prerequisite suggestion, handled filtering, and question scope services against real learner/path/question data. The assessment start route enforces selected units and difficulty filters by creating/returning an assessment session compatible with the existing `/assessment` page rather than adding a custom result flow.

**Tech Stack:** FastAPI, SQLAlchemy async repositories, Pydantic, existing assessment service/session models, Next.js 14 App Router, React 18, TypeScript, Vitest, pytest.

---

## Planned Files

- Create: `src/schemas/replan.py` — request/response models for analyze and start.
- Create: `src/routers/replan.py` — `/api/replan/analyze` and `/api/replan/assessment/start` endpoints.
- Modify: `src/api/app.py` — include replan router.
- Modify: `src/services/replan_unit_discovery.py` — support already handled state and serializable candidates.
- Modify: `src/services/replan_question_scope.py` — expose canonical review scope format.
- Create/modify: `tests/services/test_replan_*` and `tests/test_replan_router.py` — focused unit/router tests.
- Modify: `frontend/lib/replan-api.ts` — typed client for analyze/start.
- Modify: `frontend/app/replan/page.tsx` — remove demo data, call backend.
- Modify: `frontend/lib/replan-assessment-context.ts` — store started assessment/session metadata.
- Modify tests under `frontend/tests/routes/replan` and `frontend/tests/unit/replan`.

---

## Task 1: Backend route contract

- [ ] Write failing tests for `POST /api/replan/analyze` returning real review units, prerequisites, handled notes, question counts.
- [ ] Write failing tests for `POST /api/replan/assessment/start` honoring selected units and difficulty filters.
- [ ] Add `src/schemas/replan.py` models with exact camelCase API aliases.
- [ ] Add `src/routers/replan.py` endpoints and register router in `src/api/app.py`.
- [ ] Verify route tests pass.
- [ ] Commit.

## Task 2: Real analyze composition

- [ ] Load current learner path units from existing recommendation/path repositories or current path response helpers.
- [ ] Build `ReplanUnitCandidate` objects from real path units, canonical ids, titles, summaries/key points, path order, handled state, and question counts.
- [ ] Use keyword planner and unit discovery to select current-path units only.
- [ ] Use prerequisite suggester with real prerequisite graph data where available; filter current-path only, handled, no-question units.
- [ ] Use question scope builder to return KPs and counts by difficulty.
- [ ] Verify service/router tests pass.
- [ ] Commit.

## Task 3: Real assessment start bridge

- [ ] Add backend helper that selects canonical questions for selected canonical unit ids and selected difficulty filters.
- [ ] Create or reuse a canonical assessment session compatible with `/assessment` page.
- [ ] Return `sessionId`, `questions`, `canonicalUnitIds`, `unitNameMap`, and `/assessment?next=/learn` href.
- [ ] Verify submitted assessment still writes `placement_assessment_results`; do not create `/replan/result`.
- [ ] Commit.

## Task 4: Frontend API wiring

- [ ] Replace `/replan` demo scope with `replanApi.analyze({ claim })`.
- [ ] Show loading/error states.
- [ ] Render prerequisite popup only from backend suggestions; never auto-add.
- [ ] On start, call `replanApi.startAssessment({ selectedUnits })`, write started canonical assessment context, write metadata, route to `/assessment?next=/learn`.
- [ ] Update Vitest route tests to mock production API instead of relying on demo data.
- [ ] Commit.

## Task 5: Verification

- [ ] Run focused frontend tests: `npm --prefix frontend test -- tests/routes/replan/page.test.tsx tests/unit/replan`.
- [ ] Run frontend typecheck: `npm --prefix frontend run type-check`.
- [ ] Run focused backend tests with isolated uv env and `--confcutdir=tests/services` where possible.
- [ ] Run router tests from repo root if environment permits; document unrelated env failures.
- [ ] Run `npx gitnexus analyze` if stale, then `npx gitnexus detect-changes`.
- [ ] Confirm `git status --short` is clean.
