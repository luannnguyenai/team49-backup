# RECAI Adoption Plan

## Goal

Build a backend-first recommendation system for `A20-App-049` that:

- reads a materialized Knowledge Graph stored in PostgreSQL
- reads learner state directly from runtime tables
- recommends courses deterministically from graph and user signals
- explains every recommendation from real features and graph paths
- exposes a stable backend engine that future AI/chat surfaces can call

This plan does **not** treat RecAI as a framework to embed into the app.
It treats RecAI as an architectural reference, mainly for:

- query/retrieve/rank/explain decomposition
- evaluation discipline
- optional future AI orchestration over trusted backend tools

## Product Direction

The recommendation engine is the product core.

- Primary system: backend recommendation engine
- Secondary system: optional AI consumers that call the engine
- Non-goal: chatbot-first recommendation
- Non-goal: training-heavy LLM recommender stack in early phases

## Why This Direction

The current repo already has:

- a course-first frontend shell
- a rule-based course recommender
- a PostgreSQL-backed KG subsystem
- persisted recommendation rows and events

The current repo does **not** yet have:

- authoritative course runtime data fully sourced from DB
- real course search
- a course-aware KG that treats courses as first-class graph nodes
- unified learner state across recommendation and KG

That makes the best path:

1. clean up the data plane
2. make the KG course-aware
3. unify learner state
4. build the backend recommendation engine
5. add evaluation and guardrails
6. only then add AI consumers

## Proposed Runtime Workflow

### Automatic Recommendation Workflow

1. A user lands on the catalog or dashboard.
2. The backend loads a `LearnerStateSnapshot`.
3. The backend loads candidate courses from the course-aware KG.
4. The engine filters out ineligible courses.
5. The engine ranks remaining candidates using:
   - prerequisite readiness
   - remediation fit
   - advancement fit
   - transfer potential
   - availability and business constraints
   - learner goals and preferences
6. The engine emits:
   - ranked course list
   - feature payload
   - explanation payload
7. The backend persists recommendation rows and request metadata.
8. The frontend renders course cards and explanation text.
9. User interactions are logged for future evaluation and analytics.

### Optional AI Consumer Workflow

1. A user asks for help discovering a course.
2. The AI layer parses intent.
3. The AI layer calls backend search or recommendation tools.
4. The backend engine returns constrained, grounded results.
5. The AI layer reformats the grounded result into natural language.

The AI layer never invents courses or bypasses the backend engine.

## Phase Overview

- `phase-01-kg-db-foundation.md`
  Build DB-first KG inputs and remove hidden dependence on file bootstrap logic for recommendation-critical graph data.
- `phase-02-course-aware-kg.md`
  Extend the graph model so courses become first-class KG nodes with course-topic, course-KC, and course-course edges.
- `phase-03-user-state-aggregation.md`
  Unify learner readiness, mastery, progress, goals, and preferences into one backend snapshot.
- `phase-04-recommendation-engine.md`
  Implement the backend recommendation engine using `filter -> retrieve -> rank -> explain -> persist`.
- `phase-05-evaluation-and-guardrails.md`
  Add correctness, relevance, regression, and explanation evaluation suites.
- `phase-06-ai-consumers.md`
  Add optional AI consumers that call the backend engine without replacing it.

## Phase Order

The order is mandatory.

- Phase 1 blocks every later phase.
- Phase 2 depends on Phase 1.
- Phase 3 depends on Phase 1 and informs Phase 4.
- Phase 4 depends on Phases 1, 2, and 3.
- Phase 5 starts after Phase 4 has stable contracts.
- Phase 6 starts only after Phase 4 and Phase 5 are in place.

## Commit Strategy

Implementation should be pushed in small slices, not giant dumps.

- One commit per completed submodule slice
- Keep each commit roughly to one testable unit
- Push the current branch after each stable commit
- Never combine schema, runtime, and frontend changes in one unreviewable blob unless the slice is tiny and inseparable

Recommended commit rhythm per phase:

- migration or schema slice
- repository or service slice
- API slice
- test slice
- polish or docs slice

## Phase Exit Criteria

A phase is complete only when all of the following are true:

- runtime behavior works for the phase goal
- unit tests pass
- contract or integration tests pass where applicable
- docs and fixtures are updated
- no hidden fallback is masking missing dependencies

## Known Constraints

- The current course runtime still mixes bootstrap data and DB data.
- The current tutor stack is lecture-scoped and must not become the recommendation core.
- Recommendation logic is currently fragmented across course, topic, and KG paths.
- Graph and learner-state correctness matter more than adding any LLM layer early.

## Source References

- [src/services/course_recommendation_engine.py](/D:/VSCODE/VINAI/A20-App-049/src/services/course_recommendation_engine.py:50)
- [src/services/course_catalog_service.py](/D:/VSCODE/VINAI/A20-App-049/src/services/course_catalog_service.py:67)
- [src/kg/service.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/service.py:30)
- [src/kg/pipeline.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/pipeline.py:17)
- [src/kg/repository.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/repository.py:192)
- [src/kg/providers.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/providers.py:29)
- [alembic/versions/20260419_kg_init.py](/D:/VSCODE/VINAI/A20-App-049/alembic/versions/20260419_kg_init.py:47)
