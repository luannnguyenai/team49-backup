# Phase 06: AI Consumers

## Goal

Add optional AI surfaces that consume the backend recommendation engine without replacing it.

## Why This Phase Is Last

Before this phase, the system must already have:

- DB-first KG
- course-aware graph
- unified learner state
- stable deterministic recommendation engine
- evaluation and guardrails

Without those foundations, an AI layer would just mask backend uncertainty with natural language.

## Scope

This phase covers:

- AI-assisted course discovery
- optional natural-language query interpretation
- constrained tool-calling over trusted backend APIs

This phase does not change who makes the recommendation decision.
The backend engine remains the decision core.

## New And Modified Modules

### Add

- `src/services/recommendation_assistant_service.py`
  Thin orchestration layer over trusted search and recommendation APIs.
- `src/schemas/recommendation_assistant.py`
  Structured tool request and response payloads.
- `tests/services/test_recommendation_assistant_service.py`
  Tests that the assistant never escapes backend constraints.

### Optional Frontend Additions

- `frontend/components/course/CourseDiscoveryAssistant.tsx`
  Assistant surface on the catalog page.
- `frontend/tests/routes/course/discovery-assistant.test.tsx`
  Frontend interaction tests.

## Runtime Contract

The AI consumer may:

- interpret user intent
- choose between search and recommendation tools
- ask follow-up clarifying questions
- summarize grounded recommendation results

The AI consumer may not:

- invent courses outside catalog
- bypass availability or gating rules
- directly issue free-form SQL or unrestricted retrieval
- replace the deterministic ranking core

## Suggested Tool Surface

Trusted tools can include:

- `search_courses`
- `recommend_courses`
- `explain_recommendation`
- `similar_courses`

All tools must be catalog-constrained and typed.

## UX Direction

Recommended product direction:

- discovery assistant lives on the catalog page
- result cards still use the same overview and start-learning flow
- assistant is optional, not mandatory

Do not repurpose the existing lecture tutor stack for this.
That stack is scoped to active lecture context, not open-ended recommendation.

## Testing Plan

### Service Tests

- assistant chooses the correct backend tool for representative intents
- assistant returns only grounded courses from backend responses
- assistant preserves recommendation reasons from backend payloads

### Constraint Tests

- assistant cannot return courses not present in backend result set
- assistant cannot override blocked availability states
- assistant does not mutate learner state unintentionally

### Frontend Tests

- catalog assistant renders grounded results
- clicking a result still leads to overview-first flow

## Suggested Commit Slices

1. `feat: add recommendation assistant service`
2. `test: constrain assistant to backend tool outputs`
3. `feat: add catalog discovery assistant ui`
4. `test: cover discovery assistant flow`

## Done When

- AI can help users discover courses
- all outputs remain grounded in backend engine results
- product still behaves recommendation-first, not chatbot-first
