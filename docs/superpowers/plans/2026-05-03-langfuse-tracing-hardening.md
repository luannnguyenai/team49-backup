# LangFuse Tracing Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the repo from basic tutor-only LangFuse callback usage to end-to-end, best-practice tracing across all major LLM flows with trace linkage for user feedback.

**Architecture:** Introduce a thin LangFuse integration layer in `src/core/observability.py` that standardizes SDK-rooted tracing, callback creation, propagated trace attributes, scoring linkage, and trace context persistence. Follow the LangFuse-recommended interoperability pattern: create a LangFuse root span/trace with the Python SDK, run LangChain/LangGraph callbacks inside that context, and use the root trace ID for downstream scoring and correlation.

**Tech Stack:** Python 3.12, FastAPI, LangChain, LangGraph, LangFuse Python SDK 4.x, SQLAlchemy async, pytest

---

## Scope and Assumptions

- The LangFuse agent skill from `github.com/langfuse/skills` is not currently installed in this Codex environment. The implementation should align with LangFuse documented best practices anyway, and the plan includes an explicit installation-status task so the repo/docs reflect that gap honestly.
- This plan deliberately avoids unrelated refactors in tutor, onboarding, or assessment business logic.
- Root `.env` already contains `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`.
- Existing Prometheus tutor metrics remain in place; LangFuse complements them rather than replacing them.

## File Structure / Responsibility Map

**Core tracing layer**
- Modify: `src/core/observability.py`
  Central helper for LangFuse client/callback initialization, normalized metadata, SDK root-span creation, propagated attributes, and scoring helper(s).

**Tutor flow**
- Modify: `src/services/llm_service.py`
  Add standardized root trace metadata, child observation boundaries, and trace ID persistence hooks for tutor runs.
- Modify: `src/models/store.py`
  Add optional fields on `QAHistory` for LangFuse trace linkage.
- Modify: `alembic/versions/<new_revision>_add_langfuse_trace_fields_to_qa_history.py`
  Schema migration for `qa_history.trace_id` and optional `qa_history.observation_id`.
- Modify: `src/api/app.py`
  Resolve authenticated vs anonymous tutor identity consistently and pass trace-scoped identity into the tutor service.

**Assessment flow**
- Modify: `src/services/assessment_service.py`
  Add LangFuse callbacks/metadata to assessment summary generation.

**Onboarding flow**
- Modify: `src/services/onboarding_service.py`
  Add LangFuse tracing to both LangChain-backed and direct OpenAI Responses-backed prior-analysis execution.

**Feedback scoring**
- Modify: `src/api/app.py`
  Change thumbs-up/down scoring to target the correct LangFuse trace/observation instead of issuing an unbound score.

**Tests**
- Create: `tests/test_langfuse_observability.py`
  Unit tests for core helper behavior, metadata normalization, and score routing.
- Modify: `tests/services/test_assessment_ai_summary.py`
  Targeted tests for assessment summary callback wiring.
- Modify: `tests/test_onboarding_endpoints.py`
  Extend prior-analysis tests to cover tracing behavior at the service boundary already exercised here.
- Modify or Create: `tests/services/test_llm_service.py`
  Tutor trace metadata and persistence tests if a dedicated service test file is cleaner than overloading prompt-only tests.
- Modify or Create: `tests/test_tutor_rating_route.py`
  Focused API test for tutor rating persistence and LangFuse score linkage.

**Docs**
- Modify: `.env.example`
- Modify: `deploy/.env.production.example`
- Modify: `admin-dashboard/README.md`
- Modify: `README.md`
  Document tracing behavior, required env vars, and known limitations.

---

## Phase 0: Gap Lock and Integration Contract

**Objective:** Freeze the integration contract before code changes so every later phase uses the same trace metadata vocabulary.

**Files**
- Modify: `docs/superpowers/plans/2026-05-03-langfuse-tracing-hardening.md`
- Modify: `README.md`
- Modify: `admin-dashboard/README.md`

**Work**
- Record the required LangFuse tracing pattern from official docs:
  - create SDK root span/observation first
  - apply `propagate_attributes(...)` for `user_id`, `session_id`, and tags
  - execute LangChain/LangGraph with `CallbackHandler()` inside that context
  - use the root trace ID for later scoring
- Define the normalized metadata contract for all traced LLM calls:
  - `langfuse_user_id`
  - `langfuse_session_id`
  - `langfuse_tags`
  - domain metadata such as `feature`, `route`, `lecture_id`, `context_binding_id`, `assessment_session_id`
- Document that every traced flow must expose one root trace per user-visible AI task.
- Document that tutor feedback scoring depends on persisted `trace_id`.
- Add a short note that LangFuse skill installation was requested conceptually, but the repo currently implements the integration directly in application code unless the skill is later installed in the agent environment.
- Add an installation-status subsection for `github.com/langfuse/skills`:
  - not installed in current environment
  - optional installation path
  - no runtime dependency of the app itself

**Checklist**
- [ ] A single metadata vocabulary is written down in docs.
- [ ] The docs clearly distinguish `LANGFUSE_BASE_URL` from legacy `LANGFUSE_HOST`.
- [ ] The docs explain which current endpoints are expected to create traces.
- [ ] The docs explicitly state the root-span-first pattern recommended by LangFuse.
- [ ] The docs explicitly state that `langfuse/skills` is an agent-environment aid, not an application runtime package.

**Tests**
- No unit test required in this phase.
- Manual review only.

---

## Phase 1: Core Observability Foundation

**Objective:** Turn `src/core/observability.py` into the single supported interface for creating LangFuse SDK root spans, LangChain callbacks, propagated attributes, normalized metadata, and attached scores.

**Files**
- Modify: `src/core/observability.py`
- Create: `tests/test_langfuse_observability.py`

**Work**
- Introduce a small typed helper surface, for example:
  - `build_langfuse_metadata(...)`
  - `llm_callbacks() -> list[Any]`
  - `start_langfuse_root_span(...)`
  - `propagate_langfuse_attributes(...)`
  - `score_trace(...)`
  - optional `get_langfuse_client()`
- Keep backward compatibility with `LANGFUSE_HOST`, but prefer `LANGFUSE_BASE_URL`.
- Normalize optional values so metadata never emits noisy empty strings/lists.
- Ensure the callback helper can be used by both plain `llm.invoke(...)` and LangGraph `compiled_graph.stream(...)`, but only from inside an active LangFuse SDK context when root trace control is required.
- Model the implementation on LangFuse’s documented interoperability pattern:
  - root span/context from SDK
  - `propagate_attributes(...)`
  - `CallbackHandler()` nested within the active context
- Add best-effort behavior:
  - missing keys => tracing disabled without app failure
  - score submission failures => logged, not raised

**Checklist**
- [ ] All LangFuse initialization remains centralized in one module.
- [ ] Metadata helper supports `user/session/tags` plus feature-specific fields.
- [ ] The module exposes a root-span-first API rather than encouraging callback-only tracing as the primary pattern.
- [ ] The module exposes a safe wrapper for `propagate_attributes(...)`.
- [ ] A scoring helper exists so API routes no longer call raw `client.score(...)` directly.
- [ ] Existing tutor metrics in this file still work unchanged.

**Unit Tests**
- `test_get_langfuse_handler_returns_none_without_keys`
- `test_build_langfuse_metadata_omits_empty_values`
- `test_build_langfuse_metadata_preserves_domain_fields`
- `test_score_trace_noops_when_client_unavailable`
- `test_score_trace_targets_trace_when_trace_id_present`

**Suggested Verification**
- Run: `uv run pytest tests/test_langfuse_observability.py -q`

---

## Phase 2: Tutor Root Trace and Trace Persistence

**Objective:** Upgrade the tutor path from “callback exists” to “one rooted trace per tutor exchange, with persisted trace linkage for later scoring”.

**Files**
- Modify: `src/services/llm_service.py`
- Modify: `src/models/store.py`
- Create: `alembic/versions/<new_revision>_add_langfuse_trace_fields_to_qa_history.py`
- Modify: `src/api/app.py`
- Modify or Create: `tests/services/test_llm_service.py`
- Modify or Create: `tests/test_tutor_rating_route.py`

**Work**
- Extend `QAHistory` with:
  - `langfuse_trace_id` nullable string
  - `langfuse_observation_id` nullable string if retrievable cleanly
- Decide and document the tutor identity contract:
  - if tutor is authenticated, pass `current_user.id` into tracing metadata
  - if tutor is intentionally public/anonymous, emit a stable anonymous mode without pretending a user ID exists
- In tutor request handling:
  - start one LangFuse SDK root span per tutor exchange
  - apply propagated attributes for `user_id`, `session_id`, and tags
  - build metadata including `langfuse_user_id` only when truly available, `langfuse_session_id` from tutor thread/session concept if available, `langfuse_tags=["tutor","streaming"]`
  - include domain fields like `lecture_id`, `context_binding_id`, `has_image`, `route_type`
- Thread the chosen identity/metadata from `src/api/app.py` into `src/services/llm_service.py` explicitly rather than having the service guess auth context.
- Make LangChain/LangGraph callback tracing run inside that active LangFuse context as child observations.
- Persist the root trace ID from the SDK context/root span onto `QAHistory`. Treat callback-derived IDs only as fallback diagnostics, not the primary source of truth.
- Preserve current streaming behavior and Prometheus metrics.
- Update feedback rating endpoint to look up `QAHistory.langfuse_trace_id` and send score to that trace.
- Fix the existing persistence gap in the rating endpoint by committing the DB session after `qa.rating` is updated.

**Checklist**
- [ ] Each tutor question produces one identifiable LangFuse trace.
- [ ] `QAHistory` stores enough trace linkage for future score/event correlation.
- [ ] The trace ID source of truth comes from the LangFuse SDK root context, not only `CallbackHandler.last_trace_id`.
- [ ] Tutor thumbs-up/down score attaches to the correct trace instead of an unbound score.
- [ ] Tutor thumbs-up/down ratings persist in PostgreSQL, not only in-memory request state.
- [ ] No change to tutor API contract visible to frontend clients.

**Unit / Integration Tests**
- `test_tutor_stream_config_includes_langfuse_metadata`
- `test_tutor_trace_id_persisted_with_qa_history`
- `test_rate_answer_scores_trace_when_trace_id_exists`
- `test_rate_answer_skips_langfuse_score_when_trace_id_missing`

**Suggested Verification**
- Run: `uv run pytest tests/services/test_llm_service.py -q`
- Run: `uv run pytest tests/test_langfuse_observability.py -q`
- Run: `uv run pytest tests/test_tutor_rating_route.py -q`

---

## Phase 3: Assessment Summary Tracing

**Objective:** Bring assessment AI summary generation under the same tracing contract as tutor.

**Files**
- Modify: `src/services/assessment_service.py`
- Modify: `tests/services/test_assessment_ai_summary.py`

**Work**
- Wrap assessment summary generation in one LangFuse SDK root span.
- Use propagated attributes for `user_id`, `session_id`, and tags before calling the LLM.
- Pass `llm_callbacks()` into assessment summary `llm.invoke(...)` inside that active context.
- Metadata should include:
  - `langfuse_user_id`
  - `langfuse_session_id` using the assessment `session_id`
  - `langfuse_tags=["assessment","summary"]`
  - domain metadata such as `overall_score_percent`, `decision_counts`, or simpler coarse fields if payload sensitivity is a concern
- Keep the current fallback behavior unchanged: LangFuse failure must not block summary generation or fallback response.

**Checklist**
- [ ] Assessment summary traces show up independently in LangFuse.
- [ ] The trace can be filtered by feature/tag without relying on free-text prompts.
- [ ] Summary generation still returns `available=False` on model failure without raising app errors.

**Unit Tests**
- `test_generate_assessment_ai_summary_passes_langfuse_callbacks`
- `test_generate_assessment_ai_summary_includes_assessment_session_metadata`
- `test_generate_assessment_ai_summary_preserves_existing_failure_fallback`

**Suggested Verification**
- Run: `uv run pytest tests/services/test_assessment_ai_summary.py -q`

---

## Phase 4: Onboarding Prior-Analysis Tracing

**Objective:** Trace onboarding prior-analysis consistently across both execution branches: LangChain-backed providers and direct OpenAI Responses API.

**Files**
- Modify: `src/services/onboarding_service.py`
- Modify: `tests/test_onboarding_endpoints.py`

**Work**
- For the LangChain branch:
  - start one LangFuse SDK root span
  - apply propagated attributes
  - add callbacks/metadata using the shared helper
- For the direct OpenAI Responses branch:
  - wrap the request with a LangFuse root span/child observation using the low-level SDK helper from `src/core/observability.py`
  - record input/output metadata at a safe level without logging secrets
- Use consistent tags:
  - `["onboarding","prior-analysis"]`
- Include coarse identifiers:
  - goal id
  - candidate count
  - fallback boolean
- Preserve current retry and fallback semantics.

**Checklist**
- [ ] Both onboarding provider paths emit LangFuse traces.
- [ ] Both onboarding provider paths use the same root-span-first contract.
- [ ] Retries do not create misleading duplicate root traces; either one root trace contains retries as observations, or retries are clearly labeled.
- [ ] Fallback execution remains observable in metadata.

**Unit Tests**
- `test_prior_analysis_langchain_branch_uses_langfuse_callbacks`
- `test_prior_analysis_openai_responses_branch_uses_langfuse_client`
- `test_prior_analysis_trace_metadata_contains_goal_and_candidate_count`
- `test_prior_analysis_fallback_sets_fallback_metadata_or_result_flag`

**Suggested Verification**
- Run: `uv run pytest tests/test_onboarding_endpoints.py -q`

---

## Phase 5: Observation Boundaries for Tutor Internals

**Objective:** Improve trace quality by separating routing, retrieval, tool use, and answer generation instead of relying only on one opaque LLM observation.

**Files**
- Modify: `src/services/llm_service.py`
- Modify: `src/core/observability.py`
- Modify or Create: `tests/services/test_llm_service.py`

**Work**
- Add explicit child observations or span helpers around:
  - lecture/canonical context fetch
  - transcript window retrieval
  - route selection
  - sandbox/tool execution
  - final answer persistence
- Use `propagate_attributes(...)` where appropriate so nested spans inherit stable `user_id`, `session_id`, and tags without manually re-threading them.
- Decide the minimum granularity that yields useful traces without making the code brittle.
- Ensure image-bearing tutor runs include a `has_image` trace attribute but do not store raw base64 in metadata.

**Checklist**
- [ ] Tutor trace shows meaningful internal steps in LangFuse UI.
- [ ] Nested tutor observations inherit consistent attributes through LangFuse propagation, not manual duplication everywhere.
- [ ] No sensitive payloads such as base64 image blobs or full auth tokens are emitted into trace metadata.
- [ ] The instrumentation does not materially change streaming latency or response order.

**Unit / Behavior Tests**
- `test_tutor_internal_spans_do_not_include_image_base64`
- `test_tutor_route_metadata_normalized_for_trace`
- `test_tutor_tool_execution_creates_observable_marker_or_span`

**Suggested Verification**
- Run: `uv run pytest tests/services/test_llm_service.py -q`
- Manual smoke test: ask one simple tutor question and one tool-using tutor question, then inspect LangFuse trace tree.

---

## Phase 6: Docs, Admin Surface, and Operational Verification

**Objective:** Finish the rollout with operator-facing documentation and a reproducible validation checklist.

**Files**
- Modify: `README.md`
- Modify: `admin-dashboard/README.md`
- Modify: `.env.example`
- Modify: `deploy/.env.production.example`
- Optionally Modify: `frontend/app/admin/llm/page.tsx` only if a visible note about score linkage or trace expectations is necessary

**Work**
- Document:
  - required env vars
  - which app flows create traces
  - how user feedback maps to LangFuse scores
  - how to validate traces in local dev
- Add a short operator note on the LangFuse skill:
  - what it is
  - why the app does not depend on it at runtime
  - how an agent operator could install it separately if desired
- Add an operator checklist for “LangFuse healthy vs unhealthy”.
- If useful, add a small admin note that tutor thumbs map to LangFuse score name `user_thumb`.

**Checklist**
- [ ] Docs accurately reflect `LANGFUSE_BASE_URL`.
- [ ] Docs explain trace coverage across tutor, onboarding, and assessment summary.
- [ ] Docs explain the root-span-first tracing pattern and propagated attributes pattern.
- [ ] There is a reproducible smoke-test procedure for local verification.

**Tests**
- No dedicated unit test required.
- Manual smoke checklist:
  - hit tutor endpoint
  - hit onboarding prior-analysis endpoint
  - hit assessment summary endpoint
  - rate a tutor answer
  - confirm traces and score appear in LangFuse

---

## Cross-Phase Completion Checklist

- [ ] `src/core/observability.py` is the only place that knows how to initialize LangFuse primitives.
- [ ] Tutor traces persist a `trace_id` into `QAHistory`.
- [ ] Rating a tutor answer emits a score linked to a real trace.
- [ ] Assessment summary traces are visible in LangFuse.
- [ ] Onboarding prior-analysis traces are visible for both provider paths.
- [ ] All major traced flows follow LangFuse’s documented SDK-root + nested callback pattern.
- [ ] Nested observations use propagated attributes rather than ad hoc attribute duplication.
- [ ] All new tests pass.
- [ ] Docs describe the final behavior accurately.

## Recommended Execution Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6

Rationale: scoring linkage depends on persisted tutor trace IDs, and the shared helper API should stabilize before adding coverage to other flows.

## Verification Matrix

| Phase | Main risk | Verification |
|---|---|---|
| 1 | Helper API brittle or too SDK-specific | `tests/test_langfuse_observability.py` |
| 2 | Tutor trace IDs not persisted or ratings unbound | tutor service tests + route/API test |
| 3 | Assessment summary silently untraced | assessment service test |
| 4 | OpenAI direct branch escapes tracing | onboarding service test |
| 5 | Trace too noisy or leaks sensitive data | tutor service tests + manual LangFuse review |
| 6 | Docs drift from implementation | manual checklist |

## Out of Scope for This Plan

- Full LangFuse eval datasets or prompt management migration
- Replacing Prometheus/Grafana admin metrics with LangFuse dashboards
- Frontend-side tracing in Next.js
- Bulk historical backfill of trace IDs into old `qa_history` rows

## Self-Review

- Spec coverage: every gap identified in the previous assessment is covered by a phase.
- Placeholder scan: the migration filename placeholder intentionally remains schematic because Alembic revision IDs are generated at execution time; the task still defines the file purpose explicitly.
- Type consistency: this plan now explicitly acknowledges that tutor auth context is not currently passed into `get_context_and_stream_langgraph`, so the implementation must either thread identity from `src/api/app.py` or intentionally trace tutor runs as anonymous.
- LangFuse alignment: the plan now treats SDK root spans plus nested callbacks as the default pattern, matching the LangFuse interoperability guidance for LangChain/LangGraph.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-03-langfuse-tracing-hardening.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
