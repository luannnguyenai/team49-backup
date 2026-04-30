# Path Agent RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a V1 Path Agent/AI Assistant that accepts chat messages from `/agent`, resolves user/path context, retrieves canonical units through unit-centered search or graph-based path requirements, returns cited answers/actions, and uses LangGraph only for the long-running assessment/replan approval workflow.

**Architecture:** Add a separate `/api/agent` router and focused services: schemas, context resolver, query normalizer, policy guard, unit search, runtime navigation resolver, path requirement service, unit context service, optional last-5 Lecture Tutor memory provider, chat orchestrator, frontend `/agent` chat surface, and LangGraph-backed assessment workflow service. Keep retrieval, requirement matching, assessment eligibility, and replan validation deterministic and tool-mediated; do not update mastery/planner state from LLM text. Use non-streaming chat in V1 and return structured citations/actions/traces.

**Tech Stack:** FastAPI, SQLAlchemy AsyncSession, Pydantic v2, LangGraph `StateGraph`/`interrupt`/`Command`, PostgreSQL full-text-compatible query construction, pytest/pytest-asyncio, httpx ASGI contract tests.

---

## Scope And Constraints

This plan implements backend contracts, deterministic retrieval, a narrow LangGraph workflow for assessment proposal/approval/reduction, and a minimal `/agent` chatbot UI. It does not implement streaming, vector embeddings, or free-form LLM answer generation. The chat orchestrator can return template-based grounded answers in V1 while preserving the final response shape for future LLM integration.

LangGraph scope:

- Use LangGraph only for long-running conversational workflow state: self-report → assessment proposal → user approval/reduction → assessment handoff → replan explanation.
- Do not use LangChain/LangGraph as the retrieval layer.
- Do not let an LLM decide mastery, skip, quiz eligibility, or replan mutation.
- V1 uses a backend-owned LangGraph checkpointer for assessment proposal/resume. Before multi-worker production, replace the process-local checkpointer with a DB-backed checkpointer or persist graph state snapshots into `planner_session_state.state_json`.

Important rules:

- `units.unit_id` is canonical and is the primary retrieval key.
- UI actions need runtime navigation fields such as `learning_unit_id`, `course_slug`, `unit_slug`, and `learn_href`.
- Public search requests must not allow `includeHidden`.
- Public requested `courseIds` must be intersected with the user's selected/enrolled/available courses.
- `traceMode="full"` is reviewer/dev/admin only.
- Retrieved content and Tutor memory are data, never instructions. They must not override system/developer/tool policy.
- Questions outside the current path but inside the controlled catalog may be answered with citations, but must be labeled as outside the user's current path.
- Replan requests must not trust client-provided phase/KP/mastery deltas.
- Self-report does not update mastery. Assessment evidence does.

## File Structure

Create:

- `src/schemas/agent.py` — Pydantic request/response contracts for chat, search, path requirements, unit context, actions, trace, citations, and actions.
- `src/routers/agent.py` — FastAPI `/api/agent` endpoints and auth/db wiring.
- `src/services/agent_query_normalizer.py` — deterministic alias/synonym expansion with trace output.
- `src/services/agent_context_service.py` — authenticated user/path/course context resolver.
- `src/services/agent_navigation_service.py` — canonical unit to runtime `learn_href` resolver.
- `src/services/agent_search_service.py` — unit-centered search and ranking.
- `src/services/agent_requirement_service.py` — graph-based path prerequisite/gap service.
- `src/services/agent_unit_context_service.py` — canonical unit context/KP/quiz/timestamp expansion.
- `src/services/agent_tutor_memory_service.py` — last-five current-lecture Lecture AI Tutor Q&A context provider.
- `src/services/agent_conversation_service.py` — authenticated conversation history and same-session memory summary provider.
- `src/models/agent_conversation.py` — persisted agent conversations, messages, and memory summaries.
- `src/repositories/agent_conversation_repo.py` — user-scoped persistence helpers for conversation sidebar/history/memory.
- `alembic/versions/YYYYMMDD_agent_conversations.py` — Alembic migration for conversation persistence tables.
- `src/services/agent_chat_service.py` — orchestration endpoint logic: intent, tool calls, citations, actions, fallback, trace.
- `src/services/agent_assessment_workflow.py` — LangGraph workflow for assessment proposal, user approval/reduction, and assessment handoff state.
- `frontend/app/agent/page.tsx` — ChatGPT-like AI Assistant surface.
- `frontend/components/agent/AgentChatPage.tsx` — chat transcript, citations, and action cards.
- `tests/services/test_agent_query_normalizer.py`
- `tests/services/test_agent_context_service.py`
- `tests/services/test_agent_search_service.py`
- `tests/services/test_agent_requirement_service.py`
- `tests/services/test_agent_unit_context_service.py`
- `tests/services/test_agent_tutor_memory_service.py`
- `tests/services/test_agent_conversation_service.py`
- `tests/repositories/test_agent_conversation_repo.py`
- `tests/services/test_agent_chat_service.py`
- `tests/services/test_agent_assessment_workflow.py`
- `tests/contract/test_agent_routes.py`
- `frontend/tests/routes/agent/page.test.tsx`

Modify:

- `src/api/app.py` — include `agent_router`.
- `src/models/__init__.py` — import agent conversation models so Alembic metadata discovers the new tables.
- `src/repositories/canonical_content_repo.py` — add focused data access helpers for agent search/navigation/requirements.
- `frontend/components/layout/navItems.ts` — label the global entry as `AI Assistant`.
- `frontend/middleware.ts` — redirect or alias legacy `/tutor` to `/agent` once the new UI is enabled.
- `tests/repositories/test_canonical_content_repo.py` — add repository behavior tests for new helpers.

Do not modify:

- Existing Lecture AI Tutor routing/scope.
- Existing assessment scoring/mastery update logic.
- Existing planner generation logic except through future replan action stubs.

---

### Task 1: Agent Schemas

**Files:**
- Create: `src/schemas/agent.py`
- Test: `tests/test_agent_schema_contract.py`

- [ ] **Step 1: Write schema contract tests**

Create `tests/test_agent_schema_contract.py`:

```python
from datetime import datetime, timezone

from pydantic import ValidationError

from src.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentAction,
    AgentAssessmentWorkflowRequest,
    AgentAssessmentWorkflowResponse,
    AgentCitation,
    AgentConversationMessage,
    AgentConversationSummary,
    UnitSearchRequest,
    UnitSearchResponse,
)


def test_chat_request_accepts_minimal_message():
    request = AgentChatRequest(message="Where is receptive field taught?")

    assert request.message == "Where is receptive field taught?"
    assert request.response_mode == "non_streaming"
    assert request.trace_mode == "summary"


def test_chat_response_supports_citations_and_disabled_assessment_action():
    response = AgentChatResponse(
        conversation_id="conv-1",
        message_id="msg-1",
        answer={"markdown": "Found it in CS231n Lecture 5.", "confidence": "grounded"},
        citations=[
            AgentCitation(
                canonical_unit_id="local::lecture_5::seg6",
                course_id="CS231n",
                lecture_id="lecture-05",
                lecture_title="Lecture 5: Image Classification with CNNs",
                unit_name="Receptive fields, stride, and convolution formulas",
                learn_href="/courses/cs231n/learn/lecture-05-seg6#t=3220",
                timestamp_s=3220,
                source="key_point",
            )
        ],
        actions=[
            AgentAction(
                type="start_assessment",
                label="Verify with a short quiz",
                canonical_unit_ids=["local::lecture_5::seg6"],
                default_phase="skip_verification",
                eligible=False,
                disabled_reason="no_eligible_questions",
            )
        ],
    )

    assert response.actions[0].eligible is False
    assert response.actions[0].disabled_reason == "no_eligible_questions"


def test_conversation_replay_accepts_datetime_and_raw_response_json():
    summary = AgentConversationSummary(
        conversationId="conv-1",
        title="CNN review",
        preview="Review CNN basics.",
        updatedAt=datetime(2026, 4, 30, 9, 4, tzinfo=timezone.utc),
        messageCount=1,
    )
    message = AgentConversationMessage(
        messageId="msg-1",
        role="assistant",
        markdown="Review CNN basics.",
        createdAt=datetime(2026, 4, 30, 9, 6, tzinfo=timezone.utc),
        citations=[{"canonicalUnitId": "unit-cnn", "title": "CNN basics"}],
        actions=[{"type": "open_unit", "label": "Open unit"}],
    )

    assert summary.updated_at.year == 2026
    assert message.citations[0]["canonicalUnitId"] == "unit-cnn"
    assert message.actions[0]["type"] == "open_unit"


def test_unit_search_request_does_not_accept_include_hidden():
    try:
        UnitSearchRequest.model_validate(
            {
                "query": "course logistics",
                "includeHidden": True,
            }
        )
    except ValidationError as exc:
        assert "includeHidden" in str(exc)
    else:
        raise AssertionError("includeHidden must not be accepted on public request")


def test_unit_search_response_trace_uses_per_result_navigation_resolution():
    response = UnitSearchResponse(
        results=[],
        trace={
            "trace_id": "trace-1",
            "resolved_scope": "current_path",
            "normalized_query": "receptive field",
            "query_expansions": [],
            "applied_filters": ["course_scope:CS231n"],
            "ranking_version": "unit_search_v1",
            "runtime_navigation_resolution": [
                {
                    "canonical_unit_id": "local::lecture_5::seg6",
                    "source": "product_learning_unit",
                    "learn_href": "/courses/cs231n/learn/lecture-05-seg6",
                }
            ],
        },
    )

    assert response.trace.runtime_navigation_resolution[0].source == "product_learning_unit"


def test_assessment_workflow_response_exposes_interrupt_payload():
    response = AgentAssessmentWorkflowResponse(
        workflow_id="workflow-1",
        status="waiting_user_approval",
        interrupt={
            "type": "assessment_proposal",
            "title": "CNN skip verification",
            "purpose": "Verify whether selected CNN units can be skipped.",
            "estimatedQuestions": 58,
            "estimatedTimeMinutes": 45,
            "difficultyMix": {"easy": 10, "medium": 24, "hard": 18, "application": 6},
            "canonicalUnitIds": ["unit-a"],
            "scope": [
                {"label": "CNN image classification", "unitCount": 7, "reason": "Core CV foundation."}
            ],
            "reductionOptions": [
                {
                    "id": "core-only",
                    "label": "Focus only on core topics",
                    "effect": "Removes advanced/application-heavy questions.",
                    "estimatedQuestionsAfterReduction": 38,
                }
            ],
        },
        actions=[],
    )

    assert response.status == "waiting_user_approval"
    assert response.interrupt["type"] == "assessment_proposal"
    assert response.interrupt["estimatedQuestions"] == 58


def test_assessment_workflow_request_supports_resume_decision():
    request = AgentAssessmentWorkflowRequest(
        workflowId="workflow-1",
        event="resume",
        decision={"action": "reduce", "questionBudget": 15},
    )

    assert request.workflow_id == "workflow-1"
    assert request.decision.question_budget == 15


def test_assessment_workflow_request_rejects_invalid_reduce_budget():
    try:
        AgentAssessmentWorkflowRequest.model_validate(
            {
                "event": "resume",
                "workflowId": "workflow-1",
                "decision": {"action": "reduce", "questionBudget": "abc"},
            }
        )
    except ValidationError as exc:
        assert "questionBudget" in str(exc)
    else:
        raise AssertionError("invalid reduce budget must fail request validation")
```

- [ ] **Step 2: Run schema tests and verify failure**

Run:

```bash
pytest tests/test_agent_schema_contract.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.schemas.agent'`.

- [ ] **Step 3: Implement schemas**

Create `src/schemas/agent.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AgentScope = Literal[
    "current_unit",
    "current_lecture",
    "current_course",
    "current_path",
    "global_catalog",
]

AgentIntent = Literal[
    "explain_concept",
    "find_content",
    "navigate_to_unit",
    "ask_what_next",
    "assess_knowledge",
    "request_replan",
    "explain_planner_decision",
    "summarize_progress",
    "general_course_question",
]

AssessmentPhase = Literal[
    "placement",
    "mini_quiz",
    "skip_verification",
    "bridge_check",
    "final_quiz",
    "review",
]


class RouteContext(BaseModel):
    route: str
    course_slug: str | None = Field(default=None, alias="courseSlug")
    unit_slug: str | None = Field(default=None, alias="unitSlug")
    canonical_unit_id: str | None = Field(default=None, alias="canonicalUnitId")
    player_timestamp_sec: int | None = Field(default=None, alias="playerTimestampSec")

    model_config = ConfigDict(populate_by_name=True)


class QueryExpansion(BaseModel):
    from_term: str = Field(alias="from")
    to: list[str]
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class RuntimeNavigationTrace(BaseModel):
    canonical_unit_id: str
    source: Literal["path_item", "product_learning_unit", "missing"]
    learn_href: str | None = None


class RetrievalTrace(BaseModel):
    trace_id: str
    intent: AgentIntent | None = None
    raw_query: str | None = None
    normalized_query: str
    query_expansions: list[QueryExpansion] = Field(default_factory=list)
    resolved_scope: AgentScope
    selected_path: str | None = None
    candidate_courses: list[str] = Field(default_factory=list)
    applied_filters: list[str] = Field(default_factory=list)
    ranking_version: str
    runtime_navigation_resolution: list[RuntimeNavigationTrace] = Field(default_factory=list)
    selected_unit_ids: list[str] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = Field(default=None, alias="conversationId")
    route_context: RouteContext | None = Field(default=None, alias="routeContext")
    intent: AgentIntent | None = None
    response_mode: Literal["non_streaming", "streaming"] = Field(
        default="non_streaming", alias="responseMode"
    )
    trace_mode: Literal["none", "summary", "full"] = Field(default="summary", alias="traceMode")

    model_config = ConfigDict(populate_by_name=True)


class AgentAnswer(BaseModel):
    markdown: str
    confidence: Literal["grounded", "partial", "no_source"]


class AgentCitation(BaseModel):
    canonical_unit_id: str
    course_id: str
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_name: str
    learn_href: str | None = None
    timestamp_s: int | None = None
    quote: str | None = None
    source: Literal["summary", "key_point", "transcript", "planner", "mastery"]


class AssessmentProposalScopeItem(BaseModel):
    label: str
    unit_count: int = Field(alias="unitCount")
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class AssessmentDifficultyMix(BaseModel):
    easy: int = 0
    medium: int = 0
    hard: int = 0
    application: int = 0


class AssessmentReductionOption(BaseModel):
    id: str
    label: str
    effect: str
    estimated_questions_after_reduction: int = Field(alias="estimatedQuestionsAfterReduction")

    model_config = ConfigDict(populate_by_name=True)


class AssessmentProposal(BaseModel):
    title: str
    purpose: str
    estimated_questions: int = Field(alias="estimatedQuestions", ge=1, le=70)
    estimated_time_minutes: int = Field(alias="estimatedTimeMinutes", ge=1)
    scope: list[AssessmentProposalScopeItem] = Field(default_factory=list)
    difficulty_mix: AssessmentDifficultyMix = Field(alias="difficultyMix")
    reduction_options: list[AssessmentReductionOption] = Field(default_factory=list, alias="reductionOptions")

    model_config = ConfigDict(populate_by_name=True)


class AgentAction(BaseModel):
    type: Literal[
        "open_unit",
        "start_assessment_workflow",
        "start_assessment",
        "request_replan_dry_run",
        "continue_assessment_workflow",
    ]
    label: str
    learn_href: str | None = None
    workflow_id: str | None = Field(default=None, alias="workflowId")
    canonical_unit_id: str | None = None
    canonical_unit_ids: list[str] = Field(default_factory=list)
    default_phase: AssessmentPhase | None = None
    eligible: bool | None = None
    disabled_reason: Literal[
        "no_eligible_questions",
        "unsupported_phase",
        "out_of_scope",
        "requires_login",
        "not_implemented",
    ] | None = Field(default=None, alias="disabledReason")
    current_plan_id: str | None = Field(default=None, alias="currentPlanId")
    planner_session_id: str | None = Field(default=None, alias="plannerSessionId")
    assessment_session_id: str | None = Field(default=None, alias="assessmentSessionId")
    source_canonical_unit_ids: list[str] = Field(
        default_factory=list, alias="sourceCanonicalUnitIds"
    )
    proposal: AssessmentProposal | None = None

    model_config = ConfigDict(populate_by_name=True)


class AgentFallback(BaseModel):
    reason: Literal["no_retrieval_result", "out_of_scope", "unsafe_action", "tool_error"]
    message: str


class StartAssessmentActionRequest(BaseModel):
    canonical_unit_ids: list[str] = Field(alias="canonicalUnitIds", min_length=1)
    phase: AssessmentPhase
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class RequestReplanActionRequest(BaseModel):
    assessment_session_id: str | None = Field(default=None, alias="assessmentSessionId")
    source_canonical_unit_ids: list[str] = Field(default_factory=list, alias="sourceCanonicalUnitIds")
    reason: str
    dry_run: bool = Field(default=True, alias="dryRun")

    model_config = ConfigDict(populate_by_name=True)


class AgentActionResponse(BaseModel):
    accepted: bool
    rejected_reason: str | None = Field(default=None, alias="rejectedReason")
    dry_run: bool = Field(default=True, alias="dryRun")
    impact: dict | None = None

    model_config = ConfigDict(populate_by_name=True)


class AssessmentWorkflowDecision(BaseModel):
    action: Literal["approve", "reduce", "reject"]
    question_budget: int | None = Field(default=None, ge=1, le=70, alias="questionBudget")

    model_config = ConfigDict(populate_by_name=True)


class AgentAssessmentWorkflowRequest(BaseModel):
    workflow_id: str | None = Field(default=None, alias="workflowId")
    event: Literal["start", "resume"] = "start"
    message: str | None = None
    candidate_canonical_unit_ids: list[str] = Field(
        default_factory=list, alias="candidateCanonicalUnitIds"
    )
    question_budget: int = Field(default=30, ge=1, le=70, alias="questionBudget")
    phase: AssessmentPhase = "skip_verification"
    decision: AssessmentWorkflowDecision | None = None
    assessment_session_id: str | None = Field(default=None, alias="assessmentSessionId")

    model_config = ConfigDict(populate_by_name=True)


class AgentAssessmentWorkflowResponse(BaseModel):
    workflow_id: str = Field(alias="workflowId")
    status: Literal[
        "collecting_self_report",
        "waiting_user_approval",
        "assessment_ready",
        "waiting_assessment_result",
        "completed",
        "rejected",
    ]
    interrupt: dict | None = None
    actions: list[AgentAction] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class AgentChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: AgentAnswer
    citations: list[AgentCitation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    fallback: AgentFallback | None = None
    trace: RetrievalTrace | None = None


class AgentConversationSummary(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    title: str
    preview: str
    updated_at: datetime = Field(alias="updatedAt")
    message_count: int = Field(alias="messageCount")

    model_config = ConfigDict(populate_by_name=True)


class AgentConversationMemory(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    summary_status: Literal["empty", "fresh", "stale", "updating"] = Field(alias="summaryStatus")
    recent_message_window: int = Field(alias="recentMessageWindow")
    last_updated_at: datetime | None = Field(default=None, alias="lastUpdatedAt")
    summary: dict = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class AgentConversationMessage(BaseModel):
    message_id: str = Field(alias="messageId")
    role: Literal["user", "assistant"]
    markdown: str
    created_at: datetime = Field(alias="createdAt")
    citations: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class UnitSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: AgentScope | None = None
    course_ids: list[str] | None = Field(default=None, alias="courseIds")
    limit: int = Field(default=5, ge=1, le=20)
    intent: AgentIntent | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class UnitSearchResult(BaseModel):
    canonical_unit_id: str
    learning_unit_id: str | None = None
    course_id: str
    course_slug: str | None = None
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_slug: str | None = None
    learn_href: str | None = None
    start_sec: int | None = None
    end_sec: int | None = None
    unit_name: str
    summary: str | None = None
    score: float
    reasons: list[str] = Field(default_factory=list)
    has_quiz_items: bool = False
    content_type: str | None = None
    salience_score: str | None = None
    actionable: bool
    navigation_resolution: Literal["path_item", "product_learning_unit", "missing"]


class UnitSearchResponse(BaseModel):
    results: list[UnitSearchResult]
    trace: RetrievalTrace


class TranscriptSnippet(BaseModel):
    start_sec: int
    end_sec: int
    text: str
    source: Literal["transcript", "summary", "key_point"]


class UnitContextResponse(BaseModel):
    canonical_unit_id: str
    course_id: str
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_name: str
    summary: str | None = None
    key_points: list[dict | str] = Field(default_factory=list)
    kp_ids: list[str] = Field(default_factory=list)
    learn_href: str | None = None
    start_sec: int | None = None
    end_sec: int | None = None
    snippets: list[TranscriptSnippet] = Field(default_factory=list)
    trace: RetrievalTrace


class PathRequirementsRequest(BaseModel):
    target_path_key: Literal["computer_vision", "nlp"] = Field(alias="targetPathKey")
    target_course_ids: list[str] | None = Field(default=None, alias="targetCourseIds")
    source_course_ids: list[str] | None = Field(default=None, alias="sourceCourseIds")
    include_mastery: bool = Field(default=True, alias="includeMastery")
    prerequisite_depth: Literal[1, 2] = Field(default=2, alias="prerequisiteDepth")

    model_config = ConfigDict(populate_by_name=True)


class PathRequirementUnit(BaseModel):
    canonical_unit_id: str
    learning_unit_id: str | None = None
    course_id: str
    course_slug: str | None = None
    unit_slug: str | None = None
    learn_href: str | None = None
    unit_name: str
    required_kp_ids: list[str]
    prerequisite_for: list[str]
    mastery_lcb: float | None = None
    status: Literal["required", "already_mastered", "needs_review", "unassessed"]
    reasons: list[str]


class PathRequirementTrace(BaseModel):
    trace_id: str
    target_path: str
    selected_path: str
    selected_course_ids: list[str]
    prerequisite_depth: int
    graph_edges_considered: int
    applied_filters: list[str]
    ranking_version: str
    runtime_navigation_resolution: list[RuntimeNavigationTrace] = Field(default_factory=list)


class PathRequirementsResponse(BaseModel):
    required_units: list[PathRequirementUnit] = Field(alias="requiredUnits")
    auth: dict[str, bool] = Field(default_factory=lambda: {"userScoped": True})
    trace: PathRequirementTrace

    model_config = ConfigDict(populate_by_name=True)
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
pytest tests/test_agent_schema_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/schemas/agent.py tests/test_agent_schema_contract.py
git commit -m "feat: add path agent schemas"
```

---

### Task 2: Query Normalizer

**Files:**
- Create: `src/services/agent_query_normalizer.py`
- Test: `tests/services/test_agent_query_normalizer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_query_normalizer.py`:

```python
from src.services.agent_query_normalizer import normalize_agent_query


def test_expands_rf_in_cv_context():
    result = normalize_agent_query("Where is RF covered?", course_ids=["CS231n"])

    assert "receptive field" in result.normalized_query
    assert result.expansions[0].from_term == "RF"
    assert result.expansions[0].to == ["receptive field"]


def test_expands_cnn_aliases():
    result = normalize_agent_query("Test me on CNNs")

    assert "convolutional neural network" in result.normalized_query
    assert any(exp.from_term.lower() == "cnn" for exp in result.expansions)


def test_expands_word_vectors():
    result = normalize_agent_query("word vectors in NLP")

    assert "word embeddings" in result.normalized_query
    assert "dense vectors" in result.normalized_query
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_query_normalizer.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement normalizer**

Create `src/services/agent_query_normalizer.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.schemas.agent import QueryExpansion


@dataclass(slots=True)
class NormalizedQuery:
    raw_query: str
    normalized_query: str
    expansions: list[QueryExpansion] = field(default_factory=list)


ALIASES: tuple[tuple[str, list[str], str], ...] = (
    (r"\bViT\b", ["vision transformer", "image transformer"], "vision_domain_alias"),
    (r"\bCNNs?\b", ["convnet", "convolutional neural network", "convolution"], "cv_domain_alias"),
    (r"\bRF\b", ["receptive field"], "cv_domain_alias"),
    (r"\bword vectors?\b", ["embeddings", "word embeddings", "dense vectors"], "nlp_domain_alias"),
    (r"\bRAG\b", ["retrieval augmented generation", "retrieval", "augmentation"], "rag_alias"),
    (r"\bbackprop\b", ["backpropagation", "gradient", "chain rule"], "dl_domain_alias"),
)


def normalize_agent_query(query: str, course_ids: list[str] | None = None) -> NormalizedQuery:
    normalized = query.strip()
    expansions: list[QueryExpansion] = []
    for pattern, replacements, reason in ALIASES:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            matched = re.search(pattern, normalized, flags=re.IGNORECASE)
            from_term = matched.group(0) if matched else pattern
            for replacement in replacements:
                if replacement.lower() not in normalized.lower():
                    normalized = f"{normalized} {replacement}"
            expansions.append(
                QueryExpansion.model_validate(
                    {"from": from_term, "to": replacements, "reason": reason}
                )
            )

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return NormalizedQuery(raw_query=query, normalized_query=normalized, expansions=expansions)
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_query_normalizer.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_query_normalizer.py tests/services/test_agent_query_normalizer.py
git commit -m "feat: add agent query normalizer"
```

---

### Task 3: Agent Context Resolver

**Files:**
- Create: `src/services/agent_context_service.py`
- Test: `tests/services/test_agent_context_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_context_service.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.agent_context_service import AgentContextService


@pytest.mark.asyncio
async def test_context_resolver_reads_goal_preference_courses():
    user_id = uuid4()
    goal_repo = SimpleNamespace()

    async def get_by_user_id(input_user_id):
        assert input_user_id == user_id
        return SimpleNamespace(selected_course_ids=["CS230", "CS231n"])

    goal_repo.get_by_user_id = get_by_user_id

    context = await AgentContextService(goal_repo).resolve(SimpleNamespace(id=user_id))

    assert context.allowed_course_ids == ["CS230", "CS231n"]
    assert context.scope == "current_path"


@pytest.mark.asyncio
async def test_context_resolver_does_not_fallback_to_all_courses():
    goal_repo = SimpleNamespace()

    async def get_by_user_id(user_id):
        return None

    goal_repo.get_by_user_id = get_by_user_id

    context = await AgentContextService(goal_repo).resolve(SimpleNamespace(id=uuid4()))

    assert context.allowed_course_ids == []


def test_context_checks_canonical_unit_course_scope():
    context = SimpleNamespace(allowed_course_ids=["CS230", "CS231n"])

    assert AgentContextService.unit_in_scope(SimpleNamespace(course_id="cs231n"), context) is True
    assert AgentContextService.unit_in_scope(SimpleNamespace(course_id="CS224n"), context) is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_context_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement context service**

Create `src/services/agent_context_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentContext:
    user_id: str
    allowed_course_ids: list[str]
    scope: str = "current_path"


class AgentContextService:
    def __init__(self, goal_preference_repo):
        self.goal_preference_repo = goal_preference_repo

    async def resolve(self, user) -> AgentContext:
        goal = await self.goal_preference_repo.get_by_user_id(user.id)
        selected = list(getattr(goal, "selected_course_ids", None) or [])
        return AgentContext(
            user_id=str(user.id),
            allowed_course_ids=[str(course_id) for course_id in selected],
        )

    @staticmethod
    def unit_in_scope(unit, context: AgentContext) -> bool:
        allowed = {course_id.lower() for course_id in context.allowed_course_ids}
        return str(getattr(unit, "course_id", "")).lower() in allowed
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_context_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_context_service.py tests/services/test_agent_context_service.py
git commit -m "feat: add path agent context resolver"
```

---

### Task 4: Repository Helpers For Agent Data

**Files:**
- Modify: `src/repositories/canonical_content_repo.py`
- Test: `tests/repositories/test_canonical_content_repo.py`

- [ ] **Step 1: Add repository tests**

Append to `tests/repositories/test_canonical_content_repo.py`:

```python
@pytest.mark.asyncio
async def test_search_units_skips_empty_query():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.search_agent_units("", ["CS231n"]) == []
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_runtime_navigation_for_canonical_units_skips_empty_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_runtime_navigation_for_canonical_units([]) == {}
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_unit_kp_concepts_skips_empty_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_unit_kp_concepts([]) == []
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_canonical_units_by_ids_skips_empty_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_canonical_units_by_ids([]) == {}
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_agent_unit_context_skips_empty_id():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_agent_unit_context("") is None
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_mastery_lcb_by_kp_ids_skips_empty_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_mastery_lcb_by_kp_ids(user_id="user-1", kp_ids=[]) == {}
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_transcript_snippets_for_unit_skips_empty_id():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_transcript_snippets_for_unit("", max_snippets=3) == []
    assert session.execute.await_count == 0
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/repositories/test_canonical_content_repo.py -q
```

Expected: FAIL with missing methods.

- [ ] **Step 3: Implement repository helpers**

Modify `src/repositories/canonical_content_repo.py`.

Add imports:

```python
from dataclasses import dataclass
from sqlalchemy import String, and_, cast, not_
from src.models.learning import LearnerMasteryKP
from src.services.canonical_mastery_service import estimate_mastery_lcb_on_read
```

Add dataclasses after imports:

```python
@dataclass(slots=True)
class AgentUnitSearchRow:
    unit: CanonicalUnit
    quiz_count: int
    score: float


@dataclass(slots=True)
class RuntimeNavigationRow:
    canonical_unit_id: str
    learning_unit_id: UUID
    course_id: UUID
    course_slug: str | None
    unit_slug: str | None
    learn_href: str | None


@dataclass(slots=True)
class AgentUnitContextRow:
    unit: CanonicalUnit
    kp_rows: list[tuple[UnitKPMap, ConceptKP]]
    navigation: RuntimeNavigationRow | None


@dataclass(slots=True)
class AgentTranscriptSnippetRow:
    start_sec: int
    end_sec: int
    text: str
    source: str
```

Add methods inside `CanonicalContentRepository`:

```python
    async def search_agent_units(
        self,
        query: str,
        course_ids: list[str],
        limit: int = 5,
    ) -> list[AgentUnitSearchRow]:
        clean_query = query.strip()
        if not clean_query or not course_ids:
            return []

        selected_lower = [course_id.lower() for course_id in course_ids]
        hidden_filter = and_(
            or_(
                CanonicalUnit.section_flags.is_(None),
                and_(
                    not_(CanonicalUnit.section_flags.contains(["logistics"])),
                    not_(CanonicalUnit.section_flags.contains(["admin"])),
                    not_(CanonicalUnit.section_flags.contains(["administrative"])),
                    not_(CanonicalUnit.section_flags.contains(["reference"])),
                ),
            ),
            or_(
                CanonicalUnit.content_type.is_(None),
                CanonicalUnit.content_type.not_in(("logistics", "admin", "administrative", "reference")),
            ),
            CanonicalUnit.is_worth_learning.is_not(False),
        )
        like_terms = [term for term in clean_query.lower().split() if len(term) >= 2][:8]
        like_filter = None
        for term in like_terms:
            pattern = f"%{term}%"
            term_filter = or_(
                func.lower(CanonicalUnit.unit_name).like(pattern),
                func.lower(CanonicalUnit.lecture_title).like(pattern),
                func.lower(CanonicalUnit.summary).like(pattern),
                func.lower(cast(CanonicalUnit.key_points, String)).like(pattern),
            )
            like_filter = term_filter if like_filter is None else or_(like_filter, term_filter)

        if like_filter is None:
            return []

        quiz_count = (
            select(
                QuestionBankItem.unit_id.label("unit_id"),
                func.count(func.distinct(QuestionBankItem.item_id)).label("quiz_count"),
            )
            .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
            .where(
                ItemPhaseMap.phase.in_(
                    (
                        "placement",
                        "mini_quiz",
                        "skip_verification",
                        "bridge_check",
                        "final_quiz",
                        "review",
                    )
                ),
                QuestionBankItem.qa_gate_passed.is_not(False),
            )
            .group_by(QuestionBankItem.unit_id)
            .subquery()
        )

        candidate_limit = max(limit * 4, limit)
        result = await self.session.execute(
            select(
                CanonicalUnit,
                func.coalesce(quiz_count.c.quiz_count, 0).label("quiz_count"),
            )
            .outerjoin(quiz_count, quiz_count.c.unit_id == CanonicalUnit.unit_id)
            .where(
                func.lower(CanonicalUnit.course_id).in_(selected_lower),
                CanonicalUnit.active.is_(True),
                hidden_filter,
                like_filter,
            )
            # Candidate-window ordering is deterministic only; final response ranking
            # is by computed relevance score below.
            .order_by(CanonicalUnit.course_id, CanonicalUnit.lecture_order, CanonicalUnit.ordering_index)
            .limit(candidate_limit)
        )

        rows: list[AgentUnitSearchRow] = []
        for unit, count in result.all():
            score = 1.0
            if clean_query.lower() in (unit.unit_name or "").lower():
                score += 2.0
            if getattr(unit, "content_type", None) in {"core_theory", "prerequisite", "foundation"}:
                score += 0.5
            if getattr(unit, "salience_score", None) in {"critical", "high"}:
                score += 0.5
            if int(count or 0) > 0:
                score += 0.25
            rows.append(AgentUnitSearchRow(unit=unit, quiz_count=int(count or 0), score=score))
        rows.sort(
            key=lambda row: (
                -row.score,
                row.unit.course_id,
                row.unit.lecture_order,
                row.unit.ordering_index,
            )
        )
        return rows[:limit]

    async def get_runtime_navigation_for_canonical_units(
        self,
        canonical_unit_ids: list[str],
    ) -> dict[str, RuntimeNavigationRow]:
        if not canonical_unit_ids:
            return {}

        result = await self.session.execute(
            select(LearningUnit, Course)
            .join(Course, LearningUnit.course_id == Course.id)
            .where(LearningUnit.canonical_unit_id.in_(canonical_unit_ids))
        )
        rows: dict[str, RuntimeNavigationRow] = {}
        for learning_unit, course in result.all():
            canonical_id = str(learning_unit.canonical_unit_id)
            course_slug = getattr(course, "slug", None)
            unit_slug = getattr(learning_unit, "slug", None)
            rows[canonical_id] = RuntimeNavigationRow(
                canonical_unit_id=canonical_id,
                learning_unit_id=learning_unit.id,
                course_id=course.id,
                course_slug=course_slug,
                unit_slug=unit_slug,
                learn_href=f"/courses/{course_slug}/learn/{unit_slug}"
                if course_slug and unit_slug
                else None,
            )
        return rows

    async def get_unit_kp_concepts(self, canonical_unit_ids: list[str]) -> list[tuple[UnitKPMap, ConceptKP]]:
        if not canonical_unit_ids:
            return []
        result = await self.session.execute(
            select(UnitKPMap, ConceptKP)
            .join(ConceptKP, ConceptKP.kp_id == UnitKPMap.kp_id)
            .where(UnitKPMap.unit_id.in_(canonical_unit_ids))
        )
        return list(result.all())

    async def get_canonical_units_by_ids(self, canonical_unit_ids: list[str]) -> dict[str, CanonicalUnit]:
        if not canonical_unit_ids:
            return {}
        result = await self.session.execute(
            select(CanonicalUnit).where(CanonicalUnit.unit_id.in_(canonical_unit_ids))
        )
        return {str(unit.unit_id): unit for unit in result.scalars().all()}

    async def get_mastery_lcb_by_kp_ids(
        self,
        *,
        user_id: str,
        kp_ids: list[str],
    ) -> dict[str, float]:
        if not kp_ids:
            return {}
        result = await self.session.execute(
            select(LearnerMasteryKP)
            .where(
                LearnerMasteryKP.user_id == user_id,
                LearnerMasteryKP.kp_id.in_(kp_ids),
            )
        )
        return {
            row.kp_id: estimate_mastery_lcb_on_read(row)
            for row in result.scalars().all()
        }

    async def get_agent_unit_context(self, canonical_unit_id: str) -> AgentUnitContextRow | None:
        if not canonical_unit_id:
            return None
        unit = await self.session.get(CanonicalUnit, canonical_unit_id)
        if unit is None:
            return None
        kp_rows = await self.get_unit_kp_concepts([canonical_unit_id])
        navigation = (await self.get_runtime_navigation_for_canonical_units([canonical_unit_id])).get(
            canonical_unit_id
        )
        return AgentUnitContextRow(unit=unit, kp_rows=kp_rows, navigation=navigation)

    async def get_transcript_snippets_for_unit(
        self,
        canonical_unit_id: str,
        max_snippets: int = 3,
    ) -> list[AgentTranscriptSnippetRow]:
        if not canonical_unit_id:
            return []
        unit = await self.session.get(CanonicalUnit, canonical_unit_id)
        if unit is None:
            return []
        clip = unit.video_clip_ref or {}
        content_ref = unit.content_ref or {}
        start_sec = int(clip.get("start_sec") or content_ref.get("start_sec") or 0)
        end_sec = int(clip.get("end_sec") or content_ref.get("end_sec") or start_sec)
        text_value = unit.summary or unit.description or unit.unit_name
        return [
            AgentTranscriptSnippetRow(
                start_sec=start_sec,
                end_sec=end_sec,
                text=text_value,
                source="summary",
            )
        ][:max_snippets]
```

- [ ] **Step 4: Run repository tests**

Run:

```bash
pytest tests/repositories/test_canonical_content_repo.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/repositories/canonical_content_repo.py tests/repositories/test_canonical_content_repo.py
git commit -m "feat: add agent content repository helpers"
```

---

### Task 5: Runtime Navigation Resolver

**Files:**
- Create: `src/services/agent_navigation_service.py`
- Test: `tests/services/test_agent_navigation_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_navigation_service.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.agent_navigation_service import RuntimeNavigationResolver


@pytest.mark.asyncio
async def test_resolves_navigation_from_repository():
    repo = SimpleNamespace()
    learning_unit_id = uuid4()
    course_id = uuid4()

    async def get_runtime_navigation_for_canonical_units(ids):
        return {
            "unit-a": SimpleNamespace(
                canonical_unit_id="unit-a",
                learning_unit_id=learning_unit_id,
                course_id=course_id,
                course_slug="cs231n",
                unit_slug="lecture-05-seg6",
                learn_href="/courses/cs231n/learn/lecture-05-seg6",
            )
        }

    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    resolver = RuntimeNavigationResolver(repo)
    result = await resolver.resolve(["unit-a"])

    assert result["unit-a"].learn_href == "/courses/cs231n/learn/lecture-05-seg6"
    assert result["unit-a"].source == "product_learning_unit"


@pytest.mark.asyncio
async def test_missing_navigation_is_non_actionable():
    repo = SimpleNamespace()

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    resolver = RuntimeNavigationResolver(repo)
    result = await resolver.resolve(["unit-a"])

    assert result["unit-a"].learn_href is None
    assert result["unit-a"].source == "missing"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_navigation_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_navigation_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class RuntimeNavigationTarget:
    canonical_unit_id: str
    learning_unit_id: str | None
    course_id: str | None
    course_slug: str | None
    unit_slug: str | None
    learn_href: str | None
    source: str


class RuntimeNavigationResolver:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    async def resolve(self, canonical_unit_ids: list[str]) -> dict[str, RuntimeNavigationTarget]:
        if not canonical_unit_ids:
            return {}

        rows = await self.content_repo.get_runtime_navigation_for_canonical_units(canonical_unit_ids)
        resolved: dict[str, RuntimeNavigationTarget] = {}
        for unit_id in canonical_unit_ids:
            row = rows.get(unit_id)
            if row is None:
                resolved[unit_id] = RuntimeNavigationTarget(
                    canonical_unit_id=unit_id,
                    learning_unit_id=None,
                    course_id=None,
                    course_slug=None,
                    unit_slug=None,
                    learn_href=None,
                    source="missing",
                )
                continue
            resolved[unit_id] = RuntimeNavigationTarget(
                canonical_unit_id=unit_id,
                learning_unit_id=str(row.learning_unit_id),
                course_id=str(row.course_id),
                course_slug=row.course_slug,
                unit_slug=row.unit_slug,
                learn_href=row.learn_href,
                source="product_learning_unit",
            )
        return resolved
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_navigation_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_navigation_service.py tests/services/test_agent_navigation_service.py
git commit -m "feat: add agent runtime navigation resolver"
```

---

### Task 6: Unit Search Service

**Files:**
- Create: `src/services/agent_search_service.py`
- Test: `tests/services/test_agent_search_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_search_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.schemas.agent import UnitSearchRequest
from src.services.agent_search_service import UnitSearchService


@pytest.mark.asyncio
async def test_search_intersects_requested_courses_with_allowed_courses():
    repo = SimpleNamespace()
    captured = {}

    async def search_agent_units(query, course_ids, limit):
        captured["course_ids"] = course_ids
        return []

    repo.search_agent_units = search_agent_units

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    service = UnitSearchService(repo)
    response = await service.search(
        UnitSearchRequest(query="CNN", courseIds=["CS231n", "CS999"]),
        allowed_course_ids=["CS231n"],
    )

    assert captured["course_ids"] == ["CS231n"]
    assert response.trace.applied_filters == [
        "course_scope:CS231n",
        "content_policy:exclude_hidden_reference_logistics",
    ]


@pytest.mark.asyncio
async def test_search_returns_navigation_and_quiz_metadata():
    unit = SimpleNamespace(
        unit_id="unit-a",
        course_id="CS231n",
        lecture_id="lecture-05",
        lecture_title="Lecture 5",
        unit_name="Receptive fields",
        summary="Effective receptive field.",
        content_type="core_theory",
        salience_score="medium",
    )
    repo = SimpleNamespace()

    async def search_agent_units(query, course_ids, limit):
        return [SimpleNamespace(unit=unit, quiz_count=3, score=4.2)]

    async def get_runtime_navigation_for_canonical_units(ids):
        return {
            "unit-a": SimpleNamespace(
                learning_unit_id="lu-a",
                course_id="course-a",
                course_slug="cs231n",
                unit_slug="lecture-05-seg6",
                learn_href="/courses/cs231n/learn/lecture-05-seg6",
            )
        }

    repo.search_agent_units = search_agent_units
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    service = UnitSearchService(repo)
    response = await service.search(UnitSearchRequest(query="RF in CNNs"), ["CS231n"])

    assert response.results[0].canonical_unit_id == "unit-a"
    assert response.results[0].has_quiz_items is True
    assert response.results[0].learn_href == "/courses/cs231n/learn/lecture-05-seg6"
    assert response.results[0].navigation_resolution == "product_learning_unit"


@pytest.mark.asyncio
async def test_search_trace_records_content_policy_filter():
    repo = SimpleNamespace()

    async def search_agent_units(query, course_ids, limit):
        return []

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    repo.search_agent_units = search_agent_units
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    response = await UnitSearchService(repo).search(UnitSearchRequest(query="course intro"), ["CS230"])

    assert "content_policy:exclude_hidden_reference_logistics" in response.trace.applied_filters


@pytest.mark.asyncio
async def test_search_orders_results_by_score_before_response():
    low_unit = SimpleNamespace(
        unit_id="unit-low",
        course_id="CS231n",
        lecture_id="lecture-01",
        lecture_title="Lecture 1",
        unit_name="Low score",
        summary="",
        content_type="core_theory",
        salience_score="low",
    )
    high_unit = SimpleNamespace(
        unit_id="unit-high",
        course_id="CS231n",
        lecture_id="lecture-05",
        lecture_title="Lecture 5",
        unit_name="High score",
        summary="",
        content_type="core_theory",
        salience_score="critical",
    )
    repo = SimpleNamespace()

    async def search_agent_units(query, course_ids, limit):
        return [
            SimpleNamespace(unit=low_unit, quiz_count=0, score=1.0),
            SimpleNamespace(unit=high_unit, quiz_count=2, score=5.0),
        ]

    async def get_runtime_navigation_for_canonical_units(ids):
        return {
            unit_id: SimpleNamespace(
                learning_unit_id=None,
                course_id="course-a",
                course_slug="cs231n",
                unit_slug=unit_id,
                learn_href=f"/courses/cs231n/learn/{unit_id}",
                source="product_learning_unit",
            )
            for unit_id in ids
        }

    repo.search_agent_units = search_agent_units
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    response = await UnitSearchService(repo).search(UnitSearchRequest(query="cnn"), ["CS231n"])

    assert [result.canonical_unit_id for result in response.results] == ["unit-high", "unit-low"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_search_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_search_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.schemas.agent import (
    QueryExpansion,
    RetrievalTrace,
    RuntimeNavigationTrace,
    UnitSearchRequest,
    UnitSearchResponse,
    UnitSearchResult,
)
from src.services.agent_navigation_service import RuntimeNavigationResolver
from src.services.agent_query_normalizer import normalize_agent_query


class UnitSearchService:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    async def search(
        self,
        request: UnitSearchRequest,
        allowed_course_ids: list[str],
    ) -> UnitSearchResponse:
        requested = request.course_ids or allowed_course_ids
        allowed_lower = {course_id.lower(): course_id for course_id in allowed_course_ids}
        scoped_course_ids = [
            allowed_lower[course_id.lower()]
            for course_id in requested
            if course_id.lower() in allowed_lower
        ]
        if not scoped_course_ids and request.scope == "global_catalog":
            scoped_course_ids = allowed_course_ids

        normalized = normalize_agent_query(request.query, course_ids=scoped_course_ids)
        rows = await self.content_repo.search_agent_units(
            normalized.normalized_query,
            scoped_course_ids,
            request.limit,
        )
        rows = sorted(rows, key=lambda row: row.score, reverse=True)
        canonical_ids = [row.unit.unit_id for row in rows]
        navigation = await RuntimeNavigationResolver(self.content_repo).resolve(canonical_ids)

        results: list[UnitSearchResult] = []
        nav_trace: list[RuntimeNavigationTrace] = []
        for row in rows:
            unit = row.unit
            nav = navigation[unit.unit_id]
            nav_trace.append(
                RuntimeNavigationTrace(
                    canonical_unit_id=unit.unit_id,
                    source=nav.source,  # type: ignore[arg-type]
                    learn_href=nav.learn_href,
                )
            )
            reasons = ["text_match"]
            if row.quiz_count > 0:
                reasons.append("quiz_available")
            if nav.learn_href:
                reasons.append("runtime_navigation_available")
            results.append(
                UnitSearchResult(
                    canonical_unit_id=unit.unit_id,
                    learning_unit_id=nav.learning_unit_id,
                    course_id=unit.course_id,
                    course_slug=nav.course_slug,
                    lecture_id=unit.lecture_id,
                    lecture_title=unit.lecture_title,
                    unit_slug=nav.unit_slug,
                    learn_href=nav.learn_href,
                    unit_name=unit.unit_name,
                    summary=unit.summary,
                    score=float(row.score),
                    reasons=reasons,
                    has_quiz_items=row.quiz_count > 0,
                    content_type=unit.content_type,
                    salience_score=unit.salience_score,
                    actionable=bool(nav.learn_href),
                    navigation_resolution=nav.source,  # type: ignore[arg-type]
                )
            )

        return UnitSearchResponse(
            results=results,
            trace=RetrievalTrace(
                trace_id=str(uuid4()),
                intent=request.intent,
                raw_query=request.query,
                normalized_query=normalized.normalized_query,
                query_expansions=normalized.expansions,
                resolved_scope=request.scope or "current_path",
                candidate_courses=scoped_course_ids,
                applied_filters=(
                    [f"course_scope:{','.join(scoped_course_ids)}"] if scoped_course_ids else []
                )
                + ["content_policy:exclude_hidden_reference_logistics"],
                ranking_version="unit_search_v1",
                runtime_navigation_resolution=nav_trace,
                selected_unit_ids=canonical_ids,
            ),
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_search_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_search_service.py tests/services/test_agent_search_service.py
git commit -m "feat: add path agent unit search service"
```

---

### Task 7: Path Requirement Service

**Files:**
- Create: `src/services/agent_requirement_service.py`
- Test: `tests/services/test_agent_requirement_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_requirement_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.schemas.agent import PathRequirementsRequest
from src.services.agent_requirement_service import PathRequirementService


@pytest.mark.asyncio
async def test_requirement_service_filters_target_courses_to_allowed_scope():
    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return []

    async def get_canonical_units_by_ids(ids):
        return {}

    async def get_unit_kp_rows(ids):
        return []

    async def get_prerequisite_edges_for_kps(ids):
        return []

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return []

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_canonical_units_by_ids = get_canonical_units_by_ids
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids

    service = PathRequirementService(repo)
    response = await service.get_requirements(
        PathRequirementsRequest(
            targetPathKey="nlp",
            targetCourseIds=["CS224n", "CS999"],
            sourceCourseIds=["CS230", "CS999"],
        ),
        allowed_course_ids=["CS224n", "CS230"],
    )

    assert response.trace.selected_course_ids == ["CS224n"]
    assert "target_course_scope:CS224n" in response.trace.applied_filters


@pytest.mark.asyncio
async def test_requirement_service_maps_prerequisite_kp_back_to_source_unit():
    target_runtime_unit = SimpleNamespace(canonical_unit_id="target-unit")
    target_unit = SimpleNamespace(unit_id="target-unit", unit_name="NLP target")
    source_unit = SimpleNamespace(
        unit_id="source-unit",
        course_id="CS230",
        unit_name="Backpropagation",
    )
    target_kp = SimpleNamespace(unit_id="target-unit", kp_id="kp-target", planner_role="main")
    source_kp = SimpleNamespace(
        unit_id="source-unit",
        kp_id="kp-source",
        planner_role="main",
        coverage_weight=1.0,
    )
    edge = SimpleNamespace(source_kp_id="kp-source", target_kp_id="kp-target")

    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return [target_runtime_unit] if course_ids == ["CS224n"] else [SimpleNamespace(canonical_unit_id="source-unit")]

    async def get_canonical_units_by_ids(ids):
        if ids == ["target-unit"]:
            return {"target-unit": target_unit}
        return {"source-unit": source_unit}

    async def get_unit_kp_rows(ids):
        return [target_kp] if ids == ["target-unit"] else [source_kp]

    async def get_prerequisite_edges_for_kps(ids):
        return [edge]

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return [SimpleNamespace(kp_id="kp-target", importance_level="high", structural_role="gateway")]

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_canonical_units_by_ids = get_canonical_units_by_ids
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids

    service = PathRequirementService(repo)
    response = await service.get_requirements(
        PathRequirementsRequest(targetPathKey="nlp", targetCourseIds=["CS224n"], sourceCourseIds=["CS230"]),
        allowed_course_ids=["CS224n", "CS230"],
    )

    assert response.required_units[0].canonical_unit_id == "source-unit"
    assert response.required_units[0].course_id == "CS230"
    assert response.required_units[0].required_kp_ids == ["kp-source"]


@pytest.mark.asyncio
async def test_requirement_service_applies_mastery_overlay_from_repo():
    target_runtime_unit = SimpleNamespace(canonical_unit_id="target-unit")
    target_unit = SimpleNamespace(unit_id="target-unit", unit_name="NLP target")
    source_unit = SimpleNamespace(unit_id="source-unit", unit_name="Backpropagation")
    target_kp = SimpleNamespace(unit_id="target-unit", kp_id="kp-target", planner_role="main")
    source_kp = SimpleNamespace(unit_id="source-unit", kp_id="kp-source", planner_role="main")
    edge = SimpleNamespace(source_kp_id="kp-source", target_kp_id="kp-target")
    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return [target_runtime_unit] if course_ids == ["CS224n"] else [SimpleNamespace(canonical_unit_id="source-unit")]

    async def get_canonical_units_by_ids(ids):
        if ids == ["target-unit"]:
            return {"target-unit": target_unit}
        return {"source-unit": source_unit}

    async def get_unit_kp_rows(ids):
        return [target_kp] if ids == ["target-unit"] else [source_kp]

    async def get_prerequisite_edges_for_kps(ids):
        return [edge]

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return [SimpleNamespace(kp_id="kp-target", importance_level="high", structural_role="gateway")]

    async def get_mastery_lcb_by_kp_ids(*, user_id, kp_ids):
        assert user_id == "user-1"
        assert kp_ids == ["kp-source"]
        return {"kp-source": 0.86}

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_canonical_units_by_ids = get_canonical_units_by_ids
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids
    repo.get_mastery_lcb_by_kp_ids = get_mastery_lcb_by_kp_ids

    response = await PathRequirementService(repo).get_requirements(
        PathRequirementsRequest(targetPathKey="nlp", targetCourseIds=["CS224n"], sourceCourseIds=["CS230"]),
        allowed_course_ids=["CS224n", "CS230"],
        user_id="user-1",
    )

    assert response.required_units[0].mastery_lcb == 0.86
    assert response.required_units[0].status == "already_mastered"


@pytest.mark.asyncio
async def test_requirement_service_accepts_concept_lookup_dict_from_repo():
    target_runtime_unit = SimpleNamespace(canonical_unit_id="target-unit")
    target_unit = SimpleNamespace(unit_id="target-unit", unit_name="NLP target")
    source_unit = SimpleNamespace(unit_id="source-unit", unit_name="Embeddings")
    target_kp = SimpleNamespace(unit_id="target-unit", kp_id="kp-target", planner_role="main")
    source_kp = SimpleNamespace(unit_id="source-unit", kp_id="kp-source", planner_role="main")
    edge = SimpleNamespace(source_kp_id="kp-source", target_kp_id="kp-target")
    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return [target_runtime_unit] if course_ids == ["CS224n"] else [SimpleNamespace(canonical_unit_id="source-unit")]

    async def get_canonical_units_by_ids(ids):
        if ids == ["target-unit"]:
            return {"target-unit": target_unit}
        return {"source-unit": source_unit}

    async def get_unit_kp_rows(ids):
        return [target_kp] if ids == ["target-unit"] else [source_kp]

    async def get_prerequisite_edges_for_kps(ids):
        return [edge]

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return {
            "kp-target": SimpleNamespace(
                kp_id="kp-target",
                importance_level="critical",
                structural_role="gateway",
            )
        }

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_canonical_units_by_ids = get_canonical_units_by_ids
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids

    response = await PathRequirementService(repo).get_requirements(
        PathRequirementsRequest(targetPathKey="nlp", targetCourseIds=["CS224n"], sourceCourseIds=["CS230"]),
        allowed_course_ids=["CS224n", "CS230"],
    )

    assert response.required_units[0].canonical_unit_id == "source-unit"


@pytest.mark.asyncio
async def test_requirement_service_ignores_reference_and_mention_only_targets():
    target_runtime_unit = SimpleNamespace(canonical_unit_id="target-unit")
    target_unit = SimpleNamespace(unit_id="target-unit", content_type="reference")
    target_kp = SimpleNamespace(
        unit_id="target-unit",
        kp_id="kp-target",
        planner_role="support",
        coverage_level="mention",
    )
    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return [target_runtime_unit]

    async def get_canonical_units_by_ids(ids):
        return {"target-unit": target_unit}

    async def get_unit_kp_rows(ids):
        return [target_kp]

    async def get_prerequisite_edges_for_kps(ids):
        raise AssertionError("mention-only reference targets must not query prerequisite edges")

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return [SimpleNamespace(kp_id="kp-target", importance_level="low", structural_role="support")]

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_canonical_units_by_ids = get_canonical_units_by_ids
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids

    response = await PathRequirementService(repo).get_requirements(
        PathRequirementsRequest(targetPathKey="nlp", targetCourseIds=["CS224n"], sourceCourseIds=["CS230"]),
        allowed_course_ids=["CS224n", "CS230"],
    )

    assert response.required_units == []
    assert "target_content_policy:core_only" in response.trace.applied_filters
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_requirement_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_requirement_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.config.goal_course_map import GOAL_COURSE_MAP
from src.schemas.agent import (
    PathRequirementTrace,
    PathRequirementUnit,
    PathRequirementsRequest,
    PathRequirementsResponse,
    RuntimeNavigationTrace,
)
from src.services.agent_navigation_service import RuntimeNavigationResolver


class PathRequirementService:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    def _eligible_unit(self, unit) -> bool:
        if unit is None:
            return False
        flags = set(getattr(unit, "section_flags", None) or [])
        content_type = str(getattr(unit, "content_type", "") or "").lower()
        if flags.intersection({"logistics", "admin", "administrative", "reference"}):
            return False
        if content_type in {"logistics", "admin", "administrative", "reference"}:
            return False
        return getattr(unit, "is_worth_learning", True) is not False

    def _target_kp_row(self, row) -> bool:
        planner_role = str(getattr(row, "planner_role", "") or "").lower()
        coverage_level = str(getattr(row, "coverage_level", "") or "").lower()
        if coverage_level == "mention":
            return False
        return planner_role in {"main", "prereq", ""}

    def _target_concept(self, concept) -> bool:
        if concept is None:
            return True
        importance = str(getattr(concept, "importance_level", "") or "").lower()
        structural_role = str(getattr(concept, "structural_role", "") or "").lower()
        if structural_role == "gateway":
            return True
        return importance in {"critical", "high", "medium", ""}

    async def get_requirements(
        self,
        request: PathRequirementsRequest,
        allowed_course_ids: list[str],
        user_id: str | None = None,
    ) -> PathRequirementsResponse:
        allowed_lower = {course_id.lower(): course_id for course_id in allowed_course_ids}
        default_targets = GOAL_COURSE_MAP.get(request.target_path_key, [])
        requested_targets = request.target_course_ids or default_targets
        requested_sources = request.source_course_ids or allowed_course_ids
        target_courses = [
            allowed_lower[c.lower()] for c in requested_targets if c.lower() in allowed_lower
        ]
        source_courses = [
            allowed_lower[c.lower()] for c in requested_sources if c.lower() in allowed_lower
        ]

        target_learning_units = await self.content_repo.get_linked_learning_units(target_courses)
        target_candidate_ids = [
            str(unit.canonical_unit_id)
            for unit in target_learning_units
            if getattr(unit, "canonical_unit_id", None)
        ]
        target_canonical_units = await self.content_repo.get_canonical_units_by_ids(target_candidate_ids)
        target_units = [
            unit for unit in target_canonical_units.values() if self._eligible_unit(unit)
        ]
        target_canonical_ids = [
            str(unit.unit_id)
            for unit in target_units
            if getattr(unit, "unit_id", None)
        ]
        target_kp_rows = await self.content_repo.get_unit_kp_rows(target_canonical_ids)
        target_concepts = await self.content_repo.get_concepts_by_ids(
            sorted({row.kp_id for row in target_kp_rows})
        )
        target_concept_values = (
            target_concepts.values() if isinstance(target_concepts, dict) else target_concepts
        )
        target_concept_by_id = {concept.kp_id: concept for concept in target_concept_values}
        target_kp_ids = sorted(
            {
                row.kp_id
                for row in target_kp_rows
                if self._target_kp_row(row)
                and self._target_concept(target_concept_by_id.get(row.kp_id))
            }
        )

        all_edges = []
        prereq_kp_ids: set[str] = set()
        frontier = target_kp_ids
        for _ in range(request.prerequisite_depth):
            if not frontier:
                break
            edges = await self.content_repo.get_prerequisite_edges_for_kps(frontier)
            all_edges.extend(edges)
            next_frontier = {
                edge.source_kp_id
                for edge in edges
                if edge.target_kp_id in frontier and edge.source_kp_id not in prereq_kp_ids
            }
            prereq_kp_ids.update(next_frontier)
            frontier = sorted(next_frontier)

        source_learning_units = await self.content_repo.get_linked_learning_units(source_courses)
        source_candidate_ids = [
            str(unit.canonical_unit_id)
            for unit in source_learning_units
            if getattr(unit, "canonical_unit_id", None)
        ]
        source_canonical_units = await self.content_repo.get_canonical_units_by_ids(source_candidate_ids)
        source_units = [
            unit for unit in source_canonical_units.values() if self._eligible_unit(unit)
        ]
        source_canonical_ids = [
            str(unit.unit_id)
            for unit in source_units
            if getattr(unit, "unit_id", None)
        ]
        source_kp_rows = await self.content_repo.get_unit_kp_rows(source_canonical_ids)
        unit_to_kps: dict[str, set[str]] = {}
        for row in source_kp_rows:
            if row.kp_id in prereq_kp_ids and self._target_kp_row(row):
                unit_to_kps.setdefault(row.unit_id, set()).add(row.kp_id)

        mastery_by_kp = {}
        if request.include_mastery and user_id:
            mastery_by_kp = await self.content_repo.get_mastery_lcb_by_kp_ids(
                user_id=user_id,
                kp_ids=sorted(prereq_kp_ids),
            )

        navigation = await RuntimeNavigationResolver(self.content_repo).resolve(list(unit_to_kps))
        units_by_canonical = {str(unit.unit_id): unit for unit in source_units}
        required_units: list[PathRequirementUnit] = []
        nav_trace: list[RuntimeNavigationTrace] = []
        for canonical_id in sorted(unit_to_kps):
            nav = navigation[canonical_id]
            nav_trace.append(
                RuntimeNavigationTrace(
                    canonical_unit_id=canonical_id,
                    source=nav.source,  # type: ignore[arg-type]
                    learn_href=nav.learn_href,
                )
            )
            unit = units_by_canonical.get(canonical_id)
            mastery_values = [
                mastery_by_kp[kp_id]
                for kp_id in unit_to_kps[canonical_id]
                if kp_id in mastery_by_kp
            ]
            min_mastery = min(mastery_values) if mastery_values else None
            status = (
                "already_mastered"
                if min_mastery is not None and min_mastery >= 0.8
                else "needs_review"
                if min_mastery is not None and min_mastery >= 0.5
                else "unassessed"
            )
            required_units.append(
                PathRequirementUnit(
                    canonical_unit_id=canonical_id,
                    learning_unit_id=nav.learning_unit_id,
                    course_id=getattr(unit, "course_id", ""),
                    course_slug=nav.course_slug,
                    unit_slug=nav.unit_slug,
                    learn_href=nav.learn_href,
                    unit_name=getattr(unit, "unit_name", canonical_id),
                    required_kp_ids=sorted(unit_to_kps[canonical_id]),
                    prerequisite_for=target_kp_ids,
                    mastery_lcb=min_mastery,
                    status=status,
                    reasons=["required_prerequisite", "prerequisite_kp_match"],
                )
            )

        return PathRequirementsResponse(
            requiredUnits=required_units,
            trace=PathRequirementTrace(
                trace_id=str(uuid4()),
                target_path=request.target_path_key,
                selected_path=request.target_path_key,
                selected_course_ids=target_courses,
                prerequisite_depth=request.prerequisite_depth,
                graph_edges_considered=len(all_edges),
                applied_filters=[
                    f"target_course_scope:{','.join(target_courses)}",
                    "target_content_policy:core_only",
                    "kp_policy:main_prereq_not_mention",
                ],
                ranking_version="path_requirements_v1",
                runtime_navigation_resolution=nav_trace,
            ),
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_requirement_service.py -q
```

Expected: PASS.

Note: action route tests are intentionally not part of Task 11. They append to
`tests/contract/test_agent_routes.py` in Task 12 after action schemas and
`agent_action_service.py` exist.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_requirement_service.py tests/services/test_agent_requirement_service.py
git commit -m "feat: add path requirement service"
```

---

### Task 8: Unit Context Service

**Files:**
- Create: `src/services/agent_unit_context_service.py`
- Test: `tests/services/test_agent_unit_context_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_unit_context_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.services.agent_unit_context_service import AgentUnitContextService


@pytest.mark.asyncio
async def test_unit_context_returns_kps_navigation_and_snippets():
    unit = SimpleNamespace(
        unit_id="unit-a",
        course_id="CS231n",
        lecture_id="lecture-05",
        lecture_title="Lecture 5",
        unit_name="Receptive fields",
        summary="How convolution kernels see local image regions.",
        key_points=["local receptive field"],
        video_clip_ref={"start_sec": 3200, "end_sec": 3340},
    )
    kp = SimpleNamespace(kp_id="kp-rf", name="Receptive field")
    context_row = SimpleNamespace(
        unit=unit,
        kp_rows=[(SimpleNamespace(kp_id="kp-rf"), kp)],
        navigation=SimpleNamespace(learn_href="/courses/cs231n/learn/lecture-05-seg6"),
    )
    repo = SimpleNamespace()

    async def get_agent_unit_context(canonical_unit_id):
        return context_row

    async def get_transcript_snippets_for_unit(canonical_unit_id, max_snippets=3):
        return [
            SimpleNamespace(
                start_sec=3200,
                end_sec=3340,
                text="Convolutional layers use local receptive fields.",
                source="summary",
            )
        ]

    repo.get_agent_unit_context = get_agent_unit_context
    repo.get_transcript_snippets_for_unit = get_transcript_snippets_for_unit

    response = await AgentUnitContextService(repo).get_context(
        "unit-a",
        allowed_course_ids=["CS231n"],
    )

    assert response.canonical_unit_id == "unit-a"
    assert response.kp_ids == ["kp-rf"]
    assert response.learn_href == "/courses/cs231n/learn/lecture-05-seg6"
    assert response.snippets[0].start_sec == 3200


@pytest.mark.asyncio
async def test_unit_context_rejects_out_of_scope_unit():
    repo = SimpleNamespace()

    async def get_agent_unit_context(canonical_unit_id):
        return SimpleNamespace(unit=SimpleNamespace(course_id="CS224n"))

    repo.get_agent_unit_context = get_agent_unit_context
    repo.get_transcript_snippets_for_unit = get_agent_unit_context

    with pytest.raises(PermissionError, match="canonical_unit_out_of_scope"):
        await AgentUnitContextService(repo).get_context("unit-a", allowed_course_ids=["CS231n"])


@pytest.mark.asyncio
async def test_unit_context_raises_for_missing_unit():
    repo = SimpleNamespace()

    async def get_agent_unit_context(canonical_unit_id):
        return None

    repo.get_agent_unit_context = get_agent_unit_context
    repo.get_transcript_snippets_for_unit = get_agent_unit_context

    with pytest.raises(ValueError, match="canonical_unit_not_found"):
        await AgentUnitContextService(repo).get_context("missing-unit", allowed_course_ids=["CS231n"])
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_unit_context_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_unit_context_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.schemas.agent import RetrievalTrace, TranscriptSnippet, UnitContextResponse


class AgentUnitContextService:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    async def get_context(
        self,
        canonical_unit_id: str,
        allowed_course_ids: list[str],
        max_snippets: int = 3,
    ) -> UnitContextResponse:
        context = await self.content_repo.get_agent_unit_context(canonical_unit_id)
        if context is None:
            raise ValueError("canonical_unit_not_found")

        unit = context.unit
        allowed = {course_id.lower() for course_id in allowed_course_ids}
        if str(unit.course_id).lower() not in allowed:
            raise PermissionError("canonical_unit_out_of_scope")
        snippets = await self.content_repo.get_transcript_snippets_for_unit(
            canonical_unit_id,
            max_snippets=max_snippets,
        )
        kp_ids = [kp.kp_id for _, kp in context.kp_rows]
        key_points = list(unit.key_points or [])
        navigation = context.navigation

        return UnitContextResponse(
            canonical_unit_id=unit.unit_id,
            course_id=unit.course_id,
            lecture_id=unit.lecture_id,
            lecture_title=unit.lecture_title,
            unit_name=unit.unit_name,
            summary=unit.summary,
            key_points=key_points,
            kp_ids=kp_ids,
            learn_href=getattr(navigation, "learn_href", None),
            start_sec=(unit.video_clip_ref or {}).get("start_sec"),
            end_sec=(unit.video_clip_ref or {}).get("end_sec"),
            snippets=[
                TranscriptSnippet(
                    start_sec=snippet.start_sec,
                    end_sec=snippet.end_sec,
                    text=snippet.text,
                    source=snippet.source,
                )
                for snippet in snippets
            ],
            trace=RetrievalTrace(
                trace_id=str(uuid4()),
                normalized_query=canonical_unit_id,
                resolved_scope="current_path",
                ranking_version="unit_context_v1",
                selected_unit_ids=[canonical_unit_id],
            ),
        )

    async def get_transcript_snippets(
        self,
        canonical_unit_id: str,
        allowed_course_ids: list[str],
        max_snippets: int = 5,
    ) -> list[TranscriptSnippet]:
        context = await self.content_repo.get_agent_unit_context(canonical_unit_id)
        if context is None:
            raise ValueError("canonical_unit_not_found")
        allowed = {course_id.lower() for course_id in allowed_course_ids}
        if str(context.unit.course_id).lower() not in allowed:
            raise PermissionError("canonical_unit_out_of_scope")
        snippets = await self.content_repo.get_transcript_snippets_for_unit(
            canonical_unit_id,
            max_snippets=max_snippets,
        )
        return [
            TranscriptSnippet(
                start_sec=snippet.start_sec,
                end_sec=snippet.end_sec,
                text=snippet.text,
                source=snippet.source,
            )
            for snippet in snippets
        ]
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_unit_context_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_unit_context_service.py tests/services/test_agent_unit_context_service.py
git commit -m "feat: add agent unit context service"
```

---

### Task 8.5: Tutor Memory Context Provider

**Files:**
- Create: `src/services/agent_tutor_memory_service.py`
- Test: `tests/services/test_agent_tutor_memory_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_tutor_memory_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.services.agent_tutor_memory_service import TutorMemoryContextProvider


@pytest.mark.asyncio
async def test_tutor_memory_returns_only_last_five_current_lecture_turns():
    repo = SimpleNamespace()

    async def get_recent_tutor_turns(user_id, lecture_id, limit):
        assert user_id == "user-1"
        assert lecture_id == "lecture-02"
        assert limit == 5
        return [
            SimpleNamespace(question=f"q{i}", answer=f"a{i}", lecture_id="lecture-02")
            for i in range(7)
        ][-5:]

    repo.get_recent_tutor_turns = get_recent_tutor_turns

    turns = await TutorMemoryContextProvider(repo).get_recent_turns(
        user_id="user-1",
        current_lecture_id="lecture-02",
    )

    assert len(turns) == 5
    assert turns[0].question == "q2"


@pytest.mark.asyncio
async def test_tutor_memory_ignores_missing_or_cross_lecture_context():
    repo = SimpleNamespace()
    repo.get_recent_tutor_turns = None

    turns = await TutorMemoryContextProvider(repo).get_recent_turns(
        user_id="user-1",
        current_lecture_id=None,
    )

    assert turns == []
```

- [ ] **Step 2: Implement provider**

Create `src/services/agent_tutor_memory_service.py`:

```python
from __future__ import annotations

from pydantic import BaseModel


class TutorMemoryTurn(BaseModel):
    question: str
    answer: str
    lecture_id: str


class TutorMemoryContextProvider:
    def __init__(self, repo):
        self.repo = repo

    async def get_recent_turns(
        self,
        *,
        user_id: str,
        current_lecture_id: str | None,
    ) -> list[TutorMemoryTurn]:
        if not current_lecture_id:
            return []
        rows = await self.repo.get_recent_tutor_turns(
            user_id=user_id,
            lecture_id=current_lecture_id,
            limit=5,
        )
        return [
            TutorMemoryTurn(
                question=row.question,
                answer=row.answer,
                lecture_id=row.lecture_id,
            )
            for row in rows[-5:]
            if row.lecture_id == current_lecture_id
        ]
```

- [ ] **Step 3: Commit**

```bash
git add src/services/agent_tutor_memory_service.py tests/services/test_agent_tutor_memory_service.py
git commit -m "feat: add agent tutor memory context provider"
```

---

### Task 8.75: Agent Conversation Sessions And Memory

**Files:**
- Create: `src/models/agent_conversation.py`
- Create: `alembic/versions/YYYYMMDD_agent_conversations.py`
- Create: `src/repositories/agent_conversation_repo.py`
- Create: `src/services/agent_conversation_service.py`
- Test: `tests/repositories/test_agent_conversation_repo.py`
- Test: `tests/services/test_agent_conversation_service.py`
- Modify: `src/models/__init__.py`
- Modify: `src/schemas/agent.py`
- Modify: `src/routers/agent.py`
- Test: `tests/contract/test_agent_routes.py`

This task backs the `/agent` chat-history sidebar and same-session memory UI. It
does not feed old sessions into new chats. The source of truth is backend
persistence through repository helpers; frontend local state is only an
optimistic/rendering cache.

- [ ] **Step 1: Add persistence model and migration**

Create `src/models/agent_conversation.py`:

```python
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    conversation_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, default="New chat")
    preview: Mapped[str] = mapped_column(String, nullable=False, default="")
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[list["AgentConversationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    memory: Mapped["AgentConversationMemory | None"] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        uselist=False,
    )


class AgentConversationMessage(Base):
    __tablename__ = "agent_conversation_messages"

    message_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("agent_conversations.conversation_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    citations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    actions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[AgentConversation] = relationship(back_populates="messages")


class AgentConversationMemory(Base):
    __tablename__ = "agent_conversation_memories"

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("agent_conversations.conversation_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    summary_status: Mapped[str] = mapped_column(String, nullable=False, default="empty")
    recent_message_window: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_updated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[AgentConversation] = relationship(back_populates="memory")
```

Register the models in `src/models/__init__.py`. This repo's `alembic/env.py`
imports `src.models`, so missing this import means tests and migrations will not
discover the new tables:

```python
from src.models.agent_conversation import (  # noqa: F401
    AgentConversation,
    AgentConversationMemory,
    AgentConversationMessage,
)

__all__ = [
    # ...
    "AgentConversation",
    "AgentConversationMessage",
    "AgentConversationMemory",
]
```

Create `alembic/versions/YYYYMMDD_agent_conversations.py`. Use the same Alembic
style as the existing files in `alembic/versions/`:

```python
from alembic import op
import sqlalchemy as sa


revision = "YYYYMMDD_agent_conversations"
down_revision = "<current_head_revision>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("conversation_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default="New chat"),
        sa.Column("preview", sa.String(), nullable=False, server_default=""),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_conversations_user_id", "agent_conversations", ["user_id"])
    op.create_index("ix_agent_conversations_updated_at", "agent_conversations", ["updated_at"])

    op.create_table(
        "agent_conversation_messages",
        sa.Column("message_id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("agent_conversations.conversation_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("citations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("actions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_conversation_messages_conversation_id", "agent_conversation_messages", ["conversation_id"])
    op.create_index("ix_agent_conversation_messages_user_id", "agent_conversation_messages", ["user_id"])
    op.create_index("ix_agent_conversation_messages_created_at", "agent_conversation_messages", ["created_at"])

    op.create_table(
        "agent_conversation_memories",
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("agent_conversations.conversation_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("summary_status", sa.String(), nullable=False, server_default="empty"),
        sa.Column("recent_message_window", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_conversation_memories_user_id", "agent_conversation_memories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_conversation_memories_user_id", table_name="agent_conversation_memories")
    op.drop_table("agent_conversation_memories")
    op.drop_index("ix_agent_conversation_messages_created_at", table_name="agent_conversation_messages")
    op.drop_index("ix_agent_conversation_messages_user_id", table_name="agent_conversation_messages")
    op.drop_index("ix_agent_conversation_messages_conversation_id", table_name="agent_conversation_messages")
    op.drop_table("agent_conversation_messages")
    op.drop_index("ix_agent_conversations_updated_at", table_name="agent_conversations")
    op.drop_index("ix_agent_conversations_user_id", table_name="agent_conversations")
    op.drop_table("agent_conversations")
```

Verification for this step:

```bash
uv run alembic upgrade head
pytest tests/repositories/test_agent_conversation_repo.py -q
```

- [ ] **Step 2: Write repository tests**

Create `tests/repositories/test_agent_conversation_repo.py`:

```python
import pytest

from src.models.agent_conversation import (
    AgentConversation,
    AgentConversationMemory,
    AgentConversationMessage,
)
from src.repositories.agent_conversation_repo import AgentConversationRepository


@pytest.mark.asyncio
async def test_repo_lists_only_user_conversations(db_session):
    repo = AgentConversationRepository(db_session)
    db_session.add_all(
        [
            AgentConversation(conversation_id="conv-user", user_id="user-1", title="CNN review"),
            AgentConversation(conversation_id="conv-other", user_id="user-2", title="Other"),
        ]
    )
    await db_session.commit()

    rows = await repo.list_agent_conversations("user-1")

    assert [row.conversation_id for row in rows] == ["conv-user"]


@pytest.mark.asyncio
async def test_repo_rejects_wrong_user_message_access(db_session):
    repo = AgentConversationRepository(db_session)
    db_session.add(AgentConversation(conversation_id="conv-1", user_id="user-1", title="Owned"))
    await db_session.commit()

    with pytest.raises(ValueError, match="conversation_not_found"):
        await repo.get_agent_conversation_messages("user-2", "conv-1")


@pytest.mark.asyncio
async def test_repo_returns_messages_and_memory_for_owner(db_session):
    repo = AgentConversationRepository(db_session)
    db_session.add(AgentConversation(conversation_id="conv-1", user_id="user-1", title="Owned"))
    db_session.add(
        AgentConversationMessage(
            message_id="msg-1",
            conversation_id="conv-1",
            user_id="user-1",
            role="assistant",
            markdown="Review CNN basics here.",
            citations_json=[{"canonicalUnitId": "unit-cnn"}],
            actions_json=[{"type": "open_unit", "label": "Open"}],
        )
    )
    db_session.add(
        AgentConversationMemory(
            conversation_id="conv-1",
            user_id="user-1",
            summary_status="fresh",
            summary_json={"selfReportedKnowledge": ["CNN"]},
        )
    )
    await db_session.commit()

    messages = await repo.get_agent_conversation_messages("user-1", "conv-1")
    memory = await repo.get_agent_conversation_memory("user-1", "conv-1")

    assert messages[0].message_id == "msg-1"
    assert memory.summary_json["selfReportedKnowledge"] == ["CNN"]
```

- [ ] **Step 3: Implement repository**

Create `src/repositories/agent_conversation_repo.py`:

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_conversation import (
    AgentConversation,
    AgentConversationMemory,
    AgentConversationMessage,
)


class AgentConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_owned_conversation(self, user_id: str, conversation_id: str) -> AgentConversation:
        conversation = await self.session.scalar(
            select(AgentConversation).where(
                AgentConversation.conversation_id == conversation_id,
                AgentConversation.user_id == user_id,
            )
        )
        if conversation is None:
            raise ValueError("conversation_not_found")
        return conversation

    async def list_agent_conversations(self, user_id: str) -> list[AgentConversation]:
        result = await self.session.scalars(
            select(AgentConversation)
            .where(AgentConversation.user_id == user_id)
            .order_by(AgentConversation.updated_at.desc())
            .limit(50)
        )
        return list(result)

    async def create_agent_conversation(self, user_id: str) -> AgentConversation:
        conversation = AgentConversation(user_id=user_id, title="New chat", preview="", message_count=0)
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def get_agent_conversation_messages(
        self,
        user_id: str,
        conversation_id: str,
    ) -> list[AgentConversationMessage]:
        await self._get_owned_conversation(user_id, conversation_id)
        result = await self.session.scalars(
            select(AgentConversationMessage)
            .where(
                AgentConversationMessage.conversation_id == conversation_id,
                AgentConversationMessage.user_id == user_id,
            )
            .order_by(AgentConversationMessage.created_at.asc())
        )
        return list(result)

    async def get_agent_conversation_memory(
        self,
        user_id: str,
        conversation_id: str,
    ) -> AgentConversationMemory | None:
        await self._get_owned_conversation(user_id, conversation_id)
        return await self.session.scalar(
            select(AgentConversationMemory).where(
                AgentConversationMemory.conversation_id == conversation_id,
                AgentConversationMemory.user_id == user_id,
            )
        )
```

- [ ] **Step 4: Write service tests**

Create `tests/services/test_agent_conversation_service.py`:

```python
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.services.agent_conversation_service import AgentConversationService


@pytest.mark.asyncio
async def test_conversation_service_lists_user_scoped_summaries_without_categories():
    repo = SimpleNamespace()

    async def list_conversations(user_id):
        assert user_id == "user-1"
        return [
            SimpleNamespace(
                conversation_id="conv-1",
                title="CNN skip assessment",
                preview="You asked whether CNN fundamentals can be skipped...",
                updated_at=datetime(2026, 4, 30, 9, 4, tzinfo=timezone.utc),
                message_count=12,
            )
        ]

    repo.list_agent_conversations = list_conversations

    conversations = await AgentConversationService(repo).list_conversations(user_id="user-1")

    assert conversations[0].conversation_id == "conv-1"
    assert not hasattr(conversations[0], "category")


@pytest.mark.asyncio
async def test_new_conversation_starts_with_empty_memory():
    repo = SimpleNamespace()

    async def create_conversation(user_id):
        return SimpleNamespace(
            conversation_id="conv-new",
            title="New chat",
            preview="",
            updated_at=datetime(2026, 4, 30, 9, 10, tzinfo=timezone.utc),
            message_count=0,
        )

    repo.create_agent_conversation = create_conversation

    async def get_memory(user_id, conversation_id):
        return None

    repo.get_agent_conversation_memory = get_memory
    service = AgentConversationService(repo)

    conversation = await service.create_conversation(user_id="user-1")
    memory = await service.get_memory(user_id="user-1", conversation_id=conversation.conversation_id)

    assert conversation.conversation_id == "conv-new"
    assert memory.summary_status == "empty"
    assert memory.summary == {}


@pytest.mark.asyncio
async def test_memory_is_loaded_only_for_same_conversation():
    repo = SimpleNamespace()

    async def get_memory(user_id, conversation_id):
        assert user_id == "user-1"
        assert conversation_id == "conv-1"
        return SimpleNamespace(
            conversation_id="conv-1",
            summary_status="fresh",
            recent_message_window=10,
            last_updated_at=datetime(2026, 4, 30, 9, 5, tzinfo=timezone.utc),
            summary_json={"selfReportedKnowledge": ["CNN basics"]},
        )

    repo.get_agent_conversation_memory = get_memory

    memory = await AgentConversationService(repo).get_memory(
        user_id="user-1",
        conversation_id="conv-1",
    )

    assert memory.summary["selfReportedKnowledge"] == ["CNN basics"]


@pytest.mark.asyncio
async def test_messages_are_replayed_with_citations_and_actions():
    repo = SimpleNamespace()

    async def get_messages(user_id, conversation_id):
        assert user_id == "user-1"
        assert conversation_id == "conv-1"
        return [
            SimpleNamespace(
                message_id="msg-1",
                role="assistant",
                markdown="Review CNN basics.",
                created_at=datetime(2026, 4, 30, 9, 6, tzinfo=timezone.utc),
                citations_json=[{"canonicalUnitId": "unit-cnn", "title": "CNN basics"}],
                actions_json=[{"type": "open_unit", "label": "Open unit"}],
            )
        ]

    repo.get_agent_conversation_messages = get_messages

    messages = await AgentConversationService(repo).get_messages(
        user_id="user-1",
        conversation_id="conv-1",
    )

    assert messages[0].message_id == "msg-1"
    assert messages[0].citations[0]["canonicalUnitId"] == "unit-cnn"
    assert messages[0].actions[0]["type"] == "open_unit"
```

- [ ] **Step 5: Implement service contract**

Create `src/services/agent_conversation_service.py`:

```python
from __future__ import annotations

from src.schemas.agent import (
    AgentConversationMemory,
    AgentConversationMessage,
    AgentConversationSummary,
)


class AgentConversationService:
    def __init__(self, repo):
        self.repo = repo

    async def list_conversations(self, *, user_id: str) -> list[AgentConversationSummary]:
        rows = await self.repo.list_agent_conversations(user_id)
        return [
            AgentConversationSummary(
                conversationId=row.conversation_id,
                title=row.title,
                preview=row.preview,
                updatedAt=row.updated_at,
                messageCount=row.message_count,
            )
            for row in rows
        ]

    async def create_conversation(self, *, user_id: str) -> AgentConversationSummary:
        row = await self.repo.create_agent_conversation(user_id)
        return AgentConversationSummary(
            conversationId=row.conversation_id,
            title=row.title,
            preview=row.preview,
            updatedAt=row.updated_at,
            messageCount=row.message_count,
        )

    async def get_memory(self, *, user_id: str, conversation_id: str) -> AgentConversationMemory:
        row = await self.repo.get_agent_conversation_memory(user_id, conversation_id)
        if row is None:
            return AgentConversationMemory(
                conversationId=conversation_id,
                summaryStatus="empty",
                recentMessageWindow=10,
                lastUpdatedAt=None,
                summary={},
            )
        return AgentConversationMemory(
            conversationId=row.conversation_id,
            summaryStatus=row.summary_status,
            recentMessageWindow=row.recent_message_window,
            lastUpdatedAt=row.last_updated_at,
            summary=row.summary_json or {},
        )

    async def get_messages(self, *, user_id: str, conversation_id: str) -> list[AgentConversationMessage]:
        rows = await self.repo.get_agent_conversation_messages(user_id, conversation_id)
        return [
            AgentConversationMessage(
                messageId=row.message_id,
                role=row.role,
                markdown=row.markdown,
                createdAt=row.created_at,
                citations=row.citations_json or [],
                actions=row.actions_json or [],
            )
            for row in rows
        ]
```

- [ ] **Step 6: Add route contract tests**

Append to `tests/contract/test_agent_routes.py`:

```python
from types import SimpleNamespace

import pytest

from src.api.app import app
from src.dependencies.auth import get_current_user


@pytest.fixture
def agent_auth_user():
    async def override_user():
        return SimpleNamespace(id="user-1")

    app.dependency_overrides[get_current_user] = override_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_agent_conversations_list_is_authenticated_and_user_scoped(db_client, agent_auth_user):
    response = await db_client.get("/api/agent/conversations")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert all("category" not in item for item in body)


@pytest.mark.asyncio
async def test_agent_conversations_create_returns_empty_new_session(db_client, agent_auth_user):
    response = await db_client.post("/api/agent/conversations")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New chat"
    assert body["messageCount"] == 0


@pytest.mark.asyncio
async def test_agent_conversation_messages_404_for_missing_or_wrong_user(db_client, agent_auth_user):
    created = await db_client.post("/api/agent/conversations")
    conversation_id = created.json()["conversationId"]

    async def override_other_user():
        return SimpleNamespace(id="user-2")

    app.dependency_overrides[get_current_user] = override_other_user
    response = await db_client.get(f"/api/agent/conversations/{conversation_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_agent_conversation_memory_returns_empty_for_new_session(db_client, agent_auth_user):
    created = await db_client.post("/api/agent/conversations")
    conversation_id = created.json()["conversationId"]
    response = await db_client.get(f"/api/agent/conversations/{conversation_id}/memory")

    assert response.status_code == 200
    assert response.json()["summaryStatus"] == "empty"
```

These tests use the existing `db_client` fixture from `tests/conftest.py`. That
fixture already builds an `ASGITransport(app=app)` client and overrides
`get_async_db` with the test transaction. If the fixture is renamed during
implementation, keep the same behavior instead of adding an unauthenticated
client fixture.

- [ ] **Step 7: Add router contracts**

Add endpoints to `src/routers/agent.py`:

```python
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.repositories.agent_conversation_repo import AgentConversationRepository
from src.schemas.agent import (
    AgentConversationMemory,
    AgentConversationMessage,
    AgentConversationSummary,
)
from src.services.agent_conversation_service import AgentConversationService


def _agent_conversation_service(db: AsyncSession) -> AgentConversationService:
    return AgentConversationService(AgentConversationRepository(db))


def _conversation_not_found(exc: ValueError) -> HTTPException:
    if str(exc) == "conversation_not_found":
        return HTTPException(status_code=404, detail="conversation_not_found")
    return HTTPException(status_code=400, detail=str(exc))


@agent_router.get("/conversations", response_model=list[AgentConversationSummary])
async def agent_list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = _agent_conversation_service(db)
    return await service.list_conversations(user_id=str(current_user.id))


@agent_router.post("/conversations", response_model=AgentConversationSummary)
async def agent_create_conversation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = _agent_conversation_service(db)
    return await service.create_conversation(user_id=str(current_user.id))


@agent_router.get("/conversations/{conversation_id}", response_model=list[AgentConversationMessage])
async def agent_get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = _agent_conversation_service(db)
    try:
        return await service.get_messages(
            user_id=str(current_user.id),
            conversation_id=conversation_id,
        )
    except ValueError as exc:
        raise _conversation_not_found(exc)


@agent_router.get("/conversations/{conversation_id}/memory", response_model=AgentConversationMemory)
async def agent_get_conversation_memory(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = _agent_conversation_service(db)
    try:
        return await service.get_memory(
            user_id=str(current_user.id),
            conversation_id=conversation_id,
        )
    except ValueError as exc:
        raise _conversation_not_found(exc)
```

Rules:

- All endpoints are authenticated and user-scoped.
- The list response has no category labels.
- New conversations return empty memory until same-session turns are summarized.
- Conversation messages persist structured citations/actions for replay.
- Conversation replay stores `citations_json`/`actions_json` as raw response JSON so old messages can render even if the live action/citation schema evolves.
- Do not implement persistent history as frontend-only `localStorage`; that would break multi-device sessions and reviewer API tests.

- [ ] **Step 8: Commit**

```bash
git add alembic/versions/YYYYMMDD_agent_conversations.py src/models/__init__.py src/models/agent_conversation.py src/repositories/agent_conversation_repo.py src/schemas/agent.py src/services/agent_conversation_service.py src/routers/agent.py tests/repositories/test_agent_conversation_repo.py tests/services/test_agent_conversation_service.py tests/contract/test_agent_routes.py
git commit -m "feat: add agent conversation session contracts"
```

---

### Task 9: Agent Chat Orchestrator

**Files:**
- Create: `src/services/agent_chat_service.py`
- Test: `tests/services/test_agent_chat_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_chat_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.schemas.agent import AgentChatRequest, RetrievalTrace, UnitSearchResponse
from src.services.agent_chat_service import (
    AgentChatService,
    classify_agent_intent,
    extract_requirement_target_path,
)


def test_classify_agent_intent_uses_intent_table_not_single_phrase_match():
    assert classify_agent_intent("Can you verify my CNN knowledge?") == "assess_knowledge"
    assert classify_agent_intent("What should I learn before transformers?") == "ask_what_next"
    assert classify_agent_intent("Where is receptive field covered?") == "find_content"
    assert classify_agent_intent("Which DL prerequisites do I need for NLP?") == "explain_planner_decision"


def test_extract_requirement_target_path_from_message():
    assert extract_requirement_target_path("Which DL prerequisites do I need for NLP?") == "nlp"
    assert extract_requirement_target_path("Which DL parts are required for computer vision?") == "computer_vision"
    assert extract_requirement_target_path("What should I learn before Vision Transformers?") == "computer_vision"
    assert extract_requirement_target_path("What should I learn before ViT?") == "computer_vision"
    assert extract_requirement_target_path("Which prerequisites do I need for CV?") == "computer_vision"
    assert extract_requirement_target_path("Does activity recognition require DL?") is None
    assert extract_requirement_target_path("Which prerequisites do I still need?") is None


@pytest.mark.asyncio
async def test_chat_uses_path_requirements_for_required_parts_question():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()

    async def get_requirements(request, allowed_course_ids, user_id=None):
        assert user_id == "user-1"
        return SimpleNamespace(
            required_units=[
                SimpleNamespace(
                    canonical_unit_id="unit-a",
                    course_id="CS230",
                    unit_name="Backpropagation",
                    learn_href="/courses/cs230/learn/lecture-02-seg4",
                    required_kp_ids=["kp-backprop"],
                )
            ],
            trace=SimpleNamespace(
                trace_id="trace-req",
                selected_course_ids=["CS224n"],
                runtime_navigation_resolution=[],
            ),
        )

    requirement_service.get_requirements = get_requirements
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Which DL parts are required for NLP?"),
        allowed_course_ids=["CS230", "CS224n"],
        user_id="user-1",
        is_reviewer=False,
    )

    assert response.answer.confidence == "grounded"
    assert response.citations[0].canonical_unit_id == "unit-a"
    assert response.actions[0].type == "open_unit"
    assert response.trace is not None


@pytest.mark.asyncio
async def test_chat_uses_cv_target_for_computer_vision_requirement_question():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()
    seen = {}

    async def get_requirements(request, allowed_course_ids, user_id=None):
        seen["target"] = request.target_path_key
        return SimpleNamespace(required_units=[], trace=SimpleNamespace(trace_id="trace-req"))

    requirement_service.get_requirements = get_requirements
    service = AgentChatService(search_service, requirement_service)

    await service.chat(
        AgentChatRequest(message="Which DL parts are required for computer vision?"),
        allowed_course_ids=["CS230", "CS231n"],
        user_id="user-1",
        is_reviewer=False,
    )

    assert seen["target"] == "computer_vision"


@pytest.mark.asyncio
async def test_chat_asks_for_target_when_requirement_question_is_ambiguous():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()

    async def get_requirements(request, allowed_course_ids, user_id=None):
        raise AssertionError("ambiguous target should not query path requirements")

    requirement_service.get_requirements = get_requirements
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Which prerequisites should I learn first?"),
        allowed_course_ids=["CS230", "CS231n", "CS224n"],
        is_reviewer=False,
    )

    assert response.answer.confidence == "partial"
    assert "which target path" in response.answer.markdown.lower()


@pytest.mark.asyncio
async def test_chat_hides_requirement_trace_when_requested():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()

    async def get_requirements(request, allowed_course_ids, user_id=None):
        return SimpleNamespace(required_units=[], trace=SimpleNamespace(trace_id="trace-req"))

    requirement_service.get_requirements = get_requirements
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Which DL parts are required for NLP?", traceMode="none"),
        allowed_course_ids=["CS230", "CS224n"],
        is_reviewer=False,
    )

    assert response.trace is None


@pytest.mark.asyncio
async def test_chat_downgrades_full_trace_for_normal_user():
    trace = RetrievalTrace(
        trace_id="trace-1",
        normalized_query="receptive field",
        resolved_scope="current_path",
        candidate_courses=["CS231n"],
        ranking_version="unit_search_v1",
    )
    search_service = SimpleNamespace()

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(results=[], trace=trace)

    search_service.search = search
    requirement_service = SimpleNamespace()
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Where is receptive field taught?", traceMode="full"),
        allowed_course_ids=["CS231n"],
        is_reviewer=False,
    )

    assert response.trace is not None
    assert response.trace.candidate_courses == []


@pytest.mark.asyncio
async def test_chat_marks_controlled_catalog_answer_outside_current_path():
    search_service = SimpleNamespace()

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                SimpleNamespace(
                    canonical_unit_id="cs224n-wordvec",
                    course_id="CS224n",
                    lecture_id="lecture-01",
                    lecture_title="Lecture 1",
                    unit_name="Word vectors and embeddings",
                    learn_href="/courses/cs224n/learn/lecture-01-seg3",
                    outside_current_path=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-1", ranking_version="unit_search_v1"),
        )

    search_service.search = search
    service = AgentChatService(search_service, SimpleNamespace())

    response = await service.chat(
        AgentChatRequest(message="What are word vectors?", traceMode="summary"),
        allowed_course_ids=["CS230", "CS231n", "CS224n"],
        current_path_course_ids=["CS230", "CS231n"],
        is_reviewer=False,
    )

    assert "outside your current path" in response.answer.markdown.lower()
    assert response.citations[0].course_id == "CS224n"


@pytest.mark.asyncio
async def test_chat_returns_assessment_workflow_action_card_for_skip_request():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                SimpleNamespace(canonical_unit_id="cnn-unit-a"),
                SimpleNamespace(canonical_unit_id="cnn-unit-b"),
            ],
            trace=RetrievalTrace(trace_id="trace-1", ranking_version="unit_search_v1"),
        )

    search_service.search = search
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="I know CNN. Test me so I can skip it."),
        allowed_course_ids=["CS230", "CS231n"],
        is_reviewer=False,
    )

    assert response.actions[0].type == "start_assessment_workflow"
    assert response.actions[0].eligible is True
    assert response.actions[0].canonical_unit_ids == ["cnn-unit-a", "cnn-unit-b"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_chat_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement orchestrator**

Create `src/services/agent_chat_service.py`:

```python
from __future__ import annotations

import re
from uuid import uuid4

from src.schemas.agent import (
    AgentAction,
    AgentAnswer,
    AgentIntent,
    AgentChatRequest,
    AgentChatResponse,
    AgentFallback,
    PathRequirementsRequest,
    RetrievalTrace,
    UnitSearchRequest,
)


INTENT_RULES: list[tuple[AgentIntent, tuple[str, ...]]] = [
    (
        "assess_knowledge",
        (
            "test me",
            "quiz me",
            "verify",
            "assessment",
            "can i skip",
            "skip",
            "already know",
            "i know",
        ),
    ),
    (
        "explain_planner_decision",
        (
            "required for",
            "prerequisite",
            "prerequisites",
            "which dl parts",
            "need for nlp",
            "need before",
        ),
    ),
    (
        "ask_what_next",
        (
            "what should i learn",
            "what next",
            "learn next",
            "study next",
            "before",
        ),
    ),
    (
        "find_content",
        (
            "where is",
            "where can i review",
            "covered",
            "find",
            "open",
            "review",
        ),
    ),
]


def classify_agent_intent(message: str, explicit_intent: AgentIntent | None = None) -> AgentIntent:
    if explicit_intent:
        return explicit_intent
    normalized = message.lower()
    for intent, phrases in INTENT_RULES:
        if any(phrase in normalized for phrase in phrases):
            return intent
    return "general_course_question"


def _has_any_phrase(normalized: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in normalized for phrase in phrases)


def _has_any_token(normalized: str, tokens: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(token)}\b", normalized) for token in tokens)


def extract_requirement_target_path(message: str, route_context=None) -> str | None:
    normalized = message.lower()
    if _has_any_phrase(
        normalized,
        ("vision transformer", "computer vision", "cs231n", "cnn", "image"),
    ) or _has_any_token(normalized, ("vit", "cv")):
        return "computer_vision"
    if _has_any_phrase(
        normalized,
        ("natural language", "cs224n", "word vector", "transformer"),
    ) or _has_any_token(normalized, ("nlp",)):
        return "nlp"
    if route_context and getattr(route_context, "course_slug", None):
        course_slug = str(route_context.course_slug).lower()
        if course_slug == "cs224n":
            return "nlp"
        if course_slug == "cs231n":
            return "computer_vision"
    return None


class AgentChatService:
    def __init__(self, search_service, requirement_service):
        self.search_service = search_service
        self.requirement_service = requirement_service

    def _filter_trace(
        self,
        trace: RetrievalTrace,
        request: AgentChatRequest,
        is_reviewer: bool,
    ) -> RetrievalTrace | None:
        if request.trace_mode == "none":
            return None
        if request.trace_mode == "full" and not is_reviewer:
            return RetrievalTrace(
                trace_id=trace.trace_id,
                intent=trace.intent,
                raw_query=trace.raw_query,
                normalized_query=trace.normalized_query,
                resolved_scope=trace.resolved_scope,
                applied_filters=trace.applied_filters,
                ranking_version=trace.ranking_version,
                selected_unit_ids=trace.selected_unit_ids,
            )
        return trace

    async def chat(
        self,
        request: AgentChatRequest,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
        user_id: str | None = None,
        is_reviewer: bool = False,
    ) -> AgentChatResponse:
        intent = classify_agent_intent(request.message, request.intent)
        if intent == "assess_knowledge":
            search = await self.search_service.search(
                UnitSearchRequest(query=request.message, scope="current_path", intent=intent),
                allowed_course_ids=allowed_course_ids,
            )
            candidate_ids = [result.canonical_unit_id for result in search.results[:12]]
            return AgentChatResponse(
                conversation_id=request.conversation_id or str(uuid4()),
                message_id=str(uuid4()),
                answer=AgentAnswer(
                    markdown=(
                        "Self-report is not enough to update mastery. "
                        "If you are ready, start an assessment so the planner can use evidence."
                    ),
                    confidence="grounded",
                ),
                citations=[],
                actions=[
                    AgentAction(
                        type="start_assessment_workflow",
                        label="Prepare assessment proposal",
                        canonical_unit_ids=candidate_ids,
                        default_phase="skip_verification",
                        eligible=bool(candidate_ids),
                        disabledReason=None if candidate_ids else "no_eligible_questions",
                    )
                ],
                trace=self._filter_trace(search.trace, request, is_reviewer),
            )

        if intent == "explain_planner_decision":
            target_path = extract_requirement_target_path(request.message, request.route_context)
            if target_path is None:
                return AgentChatResponse(
                    conversation_id=request.conversation_id or str(uuid4()),
                    message_id=str(uuid4()),
                    answer=AgentAnswer(
                        markdown=(
                            "Which target path should I check prerequisites for: "
                            "Computer Vision or NLP?"
                        ),
                        confidence="partial",
                    ),
                    citations=[],
                    actions=[],
                )
            requirements = await self.requirement_service.get_requirements(
                PathRequirementsRequest(targetPathKey=target_path),
                allowed_course_ids=allowed_course_ids,
                user_id=user_id,
            )
            answer = f"I checked the path requirement graph for {target_path.replace('_', ' ')} prerequisites."
            if not requirements.required_units:
                answer = "I could not find required prerequisite units in the current scoped path."
            citations = [
                {
                    "canonical_unit_id": unit.canonical_unit_id,
                    "course_id": unit.course_id,
                    "unit_name": unit.unit_name,
                    "learn_href": unit.learn_href,
                    "source": "planner",
                }
                for unit in requirements.required_units[:5]
            ]
            actions = [
                {
                    "type": "open_unit",
                    "label": f"Open {unit.unit_name}",
                    "learn_href": unit.learn_href,
                    "canonical_unit_id": unit.canonical_unit_id,
                }
                for unit in requirements.required_units[:3]
                if unit.learn_href
            ]
            trace = RetrievalTrace(
                trace_id=requirements.trace.trace_id,
                intent=intent,
                raw_query=request.message,
                normalized_query=request.message,
                resolved_scope="current_path",
                selected_path=target_path,
                candidate_courses=getattr(requirements.trace, "selected_course_ids", []),
                applied_filters=getattr(requirements.trace, "applied_filters", []),
                ranking_version="path_requirements_v1",
                runtime_navigation_resolution=getattr(
                    requirements.trace,
                    "runtime_navigation_resolution",
                    [],
                ),
                selected_unit_ids=[
                    unit.canonical_unit_id for unit in requirements.required_units[:5]
                ],
            )
            return AgentChatResponse(
                conversation_id=request.conversation_id or str(uuid4()),
                message_id=str(uuid4()),
                answer=AgentAnswer(
                    markdown=answer,
                    confidence="grounded" if requirements.required_units else "no_source",
                ),
                citations=citations,
                actions=actions,
                trace=self._filter_trace(trace, request, is_reviewer),
            )

        search = await self.search_service.search(
            UnitSearchRequest(query=request.message, scope="current_path", intent=intent),
            allowed_course_ids=allowed_course_ids,
        )
        citations = []
        actions = []
        outside_current_path = False
        current_path = {course_id.lower() for course_id in (current_path_course_ids or allowed_course_ids)}
        for result in search.results[:3]:
            result_outside_path = result.course_id.lower() not in current_path
            outside_current_path = outside_current_path or result_outside_path
            citations.append(
                {
                    "canonical_unit_id": result.canonical_unit_id,
                    "course_id": result.course_id,
                    "lecture_id": result.lecture_id,
                    "lecture_title": result.lecture_title,
                    "unit_name": result.unit_name,
                    "learn_href": result.learn_href,
                    "source": "summary",
                }
            )
            if result.learn_href:
                actions.append(
                    {
                        "type": "open_unit",
                        "label": f"Open {result.unit_name}",
                        "learn_href": result.learn_href,
                        "canonical_unit_id": result.canonical_unit_id,
                    }
                )

        answer_markdown = "I found relevant learning units." if citations else "I could not find a grounded source."
        if outside_current_path:
            answer_markdown += " Note: at least one cited unit is outside your current path."

        return AgentChatResponse(
            conversation_id=request.conversation_id or str(uuid4()),
            message_id=str(uuid4()),
            answer=AgentAnswer(
                markdown=answer_markdown,
                confidence="grounded" if citations else "no_source",
            ),
            citations=citations,
            actions=actions,
            fallback=None if citations else AgentFallback(
                reason="no_retrieval_result",
                message="No grounded unit matched the query in your current scope.",
            ),
            trace=self._filter_trace(search.trace, request, is_reviewer),
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_chat_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_chat_service.py tests/services/test_agent_chat_service.py
git commit -m "feat: add path agent chat orchestrator"
```

---

### Task 10: LangGraph Assessment Workflow

**Files:**
- Create: `src/services/agent_assessment_workflow.py`
- Test: `tests/services/test_agent_assessment_workflow.py`

This workflow is intentionally narrow. It coordinates the conversational
assessment/replan handoff, but it does not score mastery, create quiz sessions,
or mutate planner state. Those remain backend services/actions outside the graph.

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_assessment_workflow.py`:

```python
from langgraph.checkpoint.memory import InMemorySaver

from src.services.agent_assessment_workflow import AgentAssessmentWorkflowService


def test_workflow_starts_with_assessment_proposal_interrupt():
    service = AgentAssessmentWorkflowService(checkpointer=InMemorySaver())

    response = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a", "unit-b"],
        question_budget=30,
        phase="skip_verification",
    )

    assert response.status == "waiting_user_approval"
    assert response.interrupt["type"] == "assessment_proposal"
    assert response.interrupt["estimatedQuestions"] == 30
    assert response.interrupt["canonicalUnitIds"] == ["unit-a", "unit-b"]
    assert response.interrupt["reductionOptions"][0]["estimatedQuestionsAfterReduction"] < 30


def test_workflow_resume_reduce_reissues_smaller_proposal():
    service = AgentAssessmentWorkflowService(checkpointer=InMemorySaver())
    started = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a", "unit-b"],
        question_budget=30,
        phase="skip_verification",
    )

    response = service.resume(
        workflow_id=started.workflow_id,
        user_id="user-1",
        decision={"action": "reduce", "questionBudget": 15},
    )

    assert response.status == "waiting_user_approval"
    assert response.interrupt["estimatedQuestions"] == 15


def test_workflow_resume_invalid_reduce_budget_rejects_cleanly():
    service = AgentAssessmentWorkflowService(checkpointer=InMemorySaver())
    started = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a"],
        question_budget=10,
        phase="skip_verification",
    )

    response = service.resume(
        workflow_id=started.workflow_id,
        user_id="user-1",
        decision={"action": "reduce", "questionBudget": "abc"},
    )

    assert response.status == "rejected"
    assert response.actions == []


def test_workflow_resume_approve_returns_disabled_start_assessment_action_until_wired():
    service = AgentAssessmentWorkflowService(checkpointer=InMemorySaver())
    started = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a"],
        question_budget=10,
        phase="skip_verification",
    )

    response = service.resume(
        workflow_id=started.workflow_id,
        user_id="user-1",
        decision={"action": "approve"},
    )

    assert response.status == "assessment_ready"
    assert response.actions[0].type == "start_assessment"
    assert response.actions[0].canonical_unit_ids == ["unit-a"]
    assert response.actions[0].eligible is False
    assert response.actions[0].disabled_reason == "not_implemented"


def test_workflow_resume_rejects_wrong_user():
    service = AgentAssessmentWorkflowService(checkpointer=InMemorySaver())
    started = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a"],
        question_budget=10,
        phase="skip_verification",
    )

    try:
        service.resume(
            workflow_id=started.workflow_id,
            user_id="user-2",
            decision={"action": "approve"},
        )
    except PermissionError as exc:
        assert str(exc) == "workflow_out_of_scope"
    else:
        raise AssertionError("resume must enforce workflow ownership")


def test_workflow_resume_rejects_unknown_workflow():
    service = AgentAssessmentWorkflowService(checkpointer=InMemorySaver())

    try:
        service.resume(
            workflow_id="missing-workflow",
            user_id="user-1",
            decision={"action": "approve"},
        )
    except ValueError as exc:
        assert str(exc) == "workflow_not_found"
    else:
        raise AssertionError("resume must reject unknown workflow ids")
```

- [ ] **Step 2: Verify LangGraph dependency is installed**

Run:

```bash
python -c "from langgraph.graph import StateGraph; from langgraph.types import Command, interrupt; print('langgraph ok')"
```

Expected: prints `langgraph ok`. If this fails with `ModuleNotFoundError`, sync project dependencies before continuing:

```bash
uv sync
```

Then rerun the import check.

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_assessment_workflow.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement LangGraph workflow service**

Create `src/services/agent_assessment_workflow.py`:

```python
from __future__ import annotations

from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import ValidationError

from src.schemas.agent import (
    AgentAction,
    AgentAssessmentWorkflowResponse,
    AssessmentPhase,
    AssessmentWorkflowDecision,
)


class AssessmentWorkflowState(TypedDict, total=False):
    workflow_id: str
    user_id: str
    candidate_canonical_unit_ids: list[str]
    question_budget: int
    phase: AssessmentPhase
    status: str


class AgentAssessmentWorkflowService:
    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or InMemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AssessmentWorkflowState)
        builder.add_node("proposal", self._proposal_node)
        builder.add_node("assessment_ready", self._assessment_ready_node)
        builder.add_node("rejected", self._rejected_node)
        builder.add_edge(START, "proposal")
        builder.add_edge("assessment_ready", END)
        builder.add_edge("rejected", END)
        return builder.compile(checkpointer=self.checkpointer)

    def _proposal_node(
        self,
        state: AssessmentWorkflowState,
    ) -> Command[Literal["proposal", "assessment_ready", "rejected"]]:
        decision = interrupt(
            {
                "type": "assessment_proposal",
                "canonicalUnitIds": state["candidate_canonical_unit_ids"],
                "title": "Skip verification assessment",
                "purpose": "Verify whether selected units can be skipped with evidence.",
                "estimatedQuestions": state["question_budget"],
                "estimatedTimeMinutes": max(10, int(state["question_budget"] * 1.5)),
                "scope": [
                    {
                        "label": "Selected candidate units",
                        "unitCount": len(state["candidate_canonical_unit_ids"]),
                        "reason": "These units match the learner's self-reported prior knowledge.",
                    }
                ],
                "difficultyMix": {
                    "easy": max(1, state["question_budget"] // 5),
                    "medium": max(1, state["question_budget"] // 2),
                    "hard": max(0, state["question_budget"] // 4),
                    "application": max(0, state["question_budget"] // 10),
                },
                "reductionOptions": [
                    {
                        "id": "minimum-evidence",
                        "label": "Minimum evidence check",
                        "effect": "Keeps only high-signal questions. Evidence is weaker for borderline skips.",
                        "estimatedQuestionsAfterReduction": max(10, state["question_budget"] // 2),
                    }
                ],
                "phase": state["phase"],
                "message": "Approve or reduce the assessment before starting.",
            }
        )
        parsed_decision = self._parse_decision(decision)
        if parsed_decision is None:
            return Command(update={"status": "rejected"}, goto="rejected")

        if parsed_decision.action == "reduce":
            next_budget = parsed_decision.question_budget or state["question_budget"]
            next_budget = max(1, min(next_budget, state["question_budget"]))
            return Command(update={"question_budget": next_budget}, goto="proposal")
        if parsed_decision.action == "approve":
            return Command(update={"status": "assessment_ready"}, goto="assessment_ready")
        return Command(update={"status": "rejected"}, goto="rejected")

    def _assessment_ready_node(self, state: AssessmentWorkflowState) -> AssessmentWorkflowState:
        return {"status": "assessment_ready"}

    def _rejected_node(self, state: AssessmentWorkflowState) -> AssessmentWorkflowState:
        return {"status": "rejected"}

    def _config(self, workflow_id: str) -> dict:
        return {"configurable": {"thread_id": workflow_id}}

    def _parse_decision(
        self,
        decision: dict | AssessmentWorkflowDecision,
    ) -> AssessmentWorkflowDecision | None:
        if isinstance(decision, AssessmentWorkflowDecision):
            return decision
        try:
            return AssessmentWorkflowDecision.model_validate(decision)
        except ValidationError:
            return None

    def _response_from_result(
        self,
        workflow_id: str,
        result: dict,
        *,
        fallback_state: AssessmentWorkflowState | None = None,
    ) -> AgentAssessmentWorkflowResponse:
        interrupts = result.get("__interrupt__") or []
        if interrupts:
            return AgentAssessmentWorkflowResponse(
                workflowId=workflow_id,
                status="waiting_user_approval",
                interrupt=interrupts[0].value,
                actions=[],
                trace={"orchestrator": "langgraph", "node": "proposal"},
            )

        state = fallback_state or result
        if state.get("status") == "assessment_ready":
            return AgentAssessmentWorkflowResponse(
                workflowId=workflow_id,
                status="assessment_ready",
                actions=[
                    AgentAction(
                        type="start_assessment",
                        label="Start assessment",
                        canonical_unit_ids=state["candidate_canonical_unit_ids"],
                        default_phase=state["phase"],
                        eligible=False,
                        disabled_reason="not_implemented",
                    )
                ],
                trace={"orchestrator": "langgraph", "node": "assessment_ready"},
            )

        return AgentAssessmentWorkflowResponse(
            workflowId=workflow_id,
            status="rejected",
            actions=[],
            trace={"orchestrator": "langgraph", "node": "rejected"},
        )

    def start(
        self,
        *,
        user_id: str,
        candidate_canonical_unit_ids: list[str],
        question_budget: int,
        phase: AssessmentPhase,
    ) -> AgentAssessmentWorkflowResponse:
        workflow_id = str(uuid4())
        state: AssessmentWorkflowState = {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "candidate_canonical_unit_ids": candidate_canonical_unit_ids,
            "question_budget": question_budget,
            "phase": phase,
            "status": "waiting_user_approval",
        }
        result = self.graph.invoke(state, config=self._config(workflow_id))
        return self._response_from_result(workflow_id, result, fallback_state=state)

    def _state_for_workflow(self, workflow_id: str) -> AssessmentWorkflowState:
        state_snapshot = self.graph.get_state(self._config(workflow_id))
        state = dict(state_snapshot.values or {})
        if not state:
            raise ValueError("workflow_not_found")
        return state

    def resume(
        self,
        workflow_id: str,
        *,
        user_id: str,
        decision: dict | AssessmentWorkflowDecision,
    ) -> AgentAssessmentWorkflowResponse:
        state = self._state_for_workflow(workflow_id)
        if state.get("user_id") != user_id:
            raise PermissionError("workflow_out_of_scope")
        result = self.graph.invoke(Command(resume=decision), config=self._config(workflow_id))
        state_snapshot = self.graph.get_state(self._config(workflow_id))
        state = dict(state_snapshot.values or {})
        return self._response_from_result(workflow_id, result, fallback_state=state)
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/services/test_agent_assessment_workflow.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/services/agent_assessment_workflow.py tests/services/test_agent_assessment_workflow.py
git commit -m "feat: add langgraph assessment workflow"
```

---

### Task 11: Agent Router And App Wiring

**Files:**
- Create: `src/routers/agent.py`
- Modify: `src/api/app.py`
- Test: `tests/contract/test_agent_routes.py`

- [ ] **Step 1: Write route contract tests**

Create `tests/contract/test_agent_routes.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database import get_async_db
from src.dependencies.auth import get_current_user


pytestmark = pytest.mark.anyio


async def override_db():
    yield object()


@pytest.fixture(autouse=True)
def agent_route_overrides():
    user = SimpleNamespace(id=uuid4(), is_onboarded=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_async_db] = override_db
    try:
        yield user
    finally:
        app.dependency_overrides.clear()


async def test_agent_chat_endpoint_returns_structured_response():
    expected = {
        "conversation_id": "conv-1",
        "message_id": "msg-1",
        "answer": {"markdown": "Found it.", "confidence": "grounded"},
        "citations": [],
        "actions": [],
        "fallback": None,
        "trace": None,
    }

    with (
        patch("src.routers.agent.AgentChatService.chat", new=AsyncMock(return_value=expected)),
        patch(
            "src.routers.agent._agent_context_for_user",
            new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS230", "CS231n"])),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/agent/chat", json={"message": "Where is CNN taught?"})

    assert response.status_code == 200
    assert response.json()["answer"]["confidence"] == "grounded"


async def test_agent_search_rejects_include_hidden_contract():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/search-units",
            json={"query": "logistics", "includeHidden": True},
        )

    assert response.status_code == 422


async def test_agent_unit_context_endpoint_returns_context():
    expected = {
        "canonical_unit_id": "unit-a",
        "course_id": "CS231n",
        "lecture_id": "lecture-05",
        "lecture_title": "Lecture 5",
        "unit_name": "Receptive fields",
        "summary": "Convolution receptive fields.",
        "key_points": ["local receptive field"],
        "kp_ids": ["kp-rf"],
        "learn_href": "/courses/cs231n/learn/lecture-05-seg6",
        "start_sec": 3200,
        "end_sec": 3340,
        "snippets": [],
        "trace": {
            "trace_id": "trace-context",
            "normalized_query": "unit-a",
            "resolved_scope": "current_path",
            "ranking_version": "unit_context_v1",
        },
    }
    with patch(
        "src.routers.agent.AgentUnitContextService.get_context",
        new=AsyncMock(return_value=expected),
    ), patch(
        "src.routers.agent._agent_context_for_user",
        new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/agent/unit-context/unit-a")

    assert response.status_code == 200
    assert response.json()["canonical_unit_id"] == "unit-a"


async def test_agent_unit_context_scope_error_maps_to_403():
    with patch(
        "src.routers.agent.AgentUnitContextService.get_context",
        new=AsyncMock(side_effect=PermissionError("canonical_unit_out_of_scope")),
    ), patch(
        "src.routers.agent._agent_context_for_user",
        new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/agent/unit-context/unit-outside-scope")

    assert response.status_code == 403


async def test_agent_transcript_missing_unit_maps_to_404():
    with patch(
        "src.routers.agent.AgentUnitContextService.get_transcript_snippets",
        new=AsyncMock(side_effect=ValueError("canonical_unit_not_found")),
    ), patch(
        "src.routers.agent._agent_context_for_user",
        new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/agent/transcript-snippets/missing-unit")

    assert response.status_code == 404


```

- [ ] **Step 2: Run route tests and verify failure**

Run:

```bash
pytest tests/contract/test_agent_routes.py -q
```

Expected: FAIL with 404 for `/api/agent/*`.

- [ ] **Step 3: Implement router**

Create `src/routers/agent.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    PathRequirementsRequest,
    PathRequirementsResponse,
    UnitContextResponse,
    UnitSearchRequest,
    UnitSearchResponse,
    TranscriptSnippet,
)
from src.services.agent_context_service import AgentContext, AgentContextService
from src.services.agent_chat_service import AgentChatService
from src.services.agent_requirement_service import PathRequirementService
from src.services.agent_search_service import UnitSearchService
from src.services.agent_unit_context_service import AgentUnitContextService


agent_router = APIRouter(prefix="/api/agent", tags=["Path Agent"])


async def _agent_context_for_user(user: User, db: AsyncSession) -> AgentContext:
    return await AgentContextService(GoalPreferenceRepository(db)).resolve(user)


@agent_router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    body: AgentChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentChatResponse:
    repo = CanonicalContentRepository(db)
    context = await _agent_context_for_user(user, db)
    search = UnitSearchService(repo)
    requirements = PathRequirementService(repo)
    service = AgentChatService(search, requirements)
    return await service.chat(
        body,
        allowed_course_ids=context.allowed_course_ids,
        current_path_course_ids=context.allowed_course_ids,
        user_id=str(user.id),
        is_reviewer=False,
    )


@agent_router.post("/search-units", response_model=UnitSearchResponse)
async def agent_search_units(
    body: UnitSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UnitSearchResponse:
    context = await _agent_context_for_user(user, db)
    return await UnitSearchService(CanonicalContentRepository(db)).search(
        body,
        allowed_course_ids=context.allowed_course_ids,
    )


@agent_router.post("/path-requirements", response_model=PathRequirementsResponse)
async def agent_path_requirements(
    body: PathRequirementsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> PathRequirementsResponse:
    context = await _agent_context_for_user(user, db)
    return await PathRequirementService(CanonicalContentRepository(db)).get_requirements(
        body,
        allowed_course_ids=context.allowed_course_ids,
        user_id=str(user.id),
    )


@agent_router.get("/unit-context/{canonical_unit_id}", response_model=UnitContextResponse)
async def agent_unit_context(
    canonical_unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UnitContextResponse:
    context = await _agent_context_for_user(user, db)
    try:
        return await AgentUnitContextService(CanonicalContentRepository(db)).get_context(
            canonical_unit_id,
            allowed_course_ids=context.allowed_course_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@agent_router.get(
    "/transcript-snippets/{canonical_unit_id}",
    response_model=list[TranscriptSnippet],
)
async def agent_transcript_snippets(
    canonical_unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[TranscriptSnippet]:
    context = await _agent_context_for_user(user, db)
    try:
        return await AgentUnitContextService(CanonicalContentRepository(db)).get_transcript_snippets(
            canonical_unit_id,
            allowed_course_ids=context.allowed_course_ids,
            max_snippets=5,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


```

Modify `src/api/app.py` imports:

```python
from src.routers.agent import agent_router
```

Add router include near other routers:

```python
app.include_router(agent_router)
```

- [ ] **Step 4: Run route tests**

Run:

```bash
pytest tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 5: Run focused suite**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/repositories/test_agent_conversation_repo.py tests/services/test_agent_query_normalizer.py tests/services/test_agent_context_service.py tests/services/test_agent_navigation_service.py tests/services/test_agent_search_service.py tests/services/test_agent_requirement_service.py tests/services/test_agent_unit_context_service.py tests/services/test_agent_conversation_service.py tests/services/test_agent_chat_service.py tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/routers/agent.py src/api/app.py tests/contract/test_agent_routes.py
git commit -m "feat: expose path agent api routes"
```

---

### Task 12: Replan And Assessment Action Endpoints

**Files:**
- Modify: `src/schemas/agent.py`
- Create: `src/services/agent_action_service.py`
- Modify: `src/routers/agent.py`
- Test: `tests/services/test_agent_action_service.py`
- Test: `tests/contract/test_agent_routes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_action_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.services.agent_action_service import (
    default_phase_for_intent,
    start_assessment_not_implemented,
    validate_replan_request,
)


def test_default_phase_for_self_report_skip():
    assert default_phase_for_intent("assess_knowledge", "self_report_skip") == "skip_verification"


def test_default_phase_for_review():
    assert default_phase_for_intent("summarize_progress", "stale_mastery") == "review"


@pytest.mark.asyncio
async def test_replan_validation_rejects_missing_evidence():
    result = await validate_replan_request(
        SimpleNamespace(assessment_session_id=None, source_canonical_unit_ids=[]),
        user_id="user-1",
    )

    assert result.accepted is False
    assert result.rejected_reason == "missing_evidence"


def test_start_assessment_stub_is_not_accepted_until_wired():
    result = start_assessment_not_implemented()

    assert result.accepted is False
    assert result.rejected_reason == "not_implemented"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_action_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement action service**

Create `src/services/agent_action_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


def default_phase_for_intent(intent: str, reason: str | None = None) -> str:
    if reason == "self_report_skip":
        return "skip_verification"
    if reason == "stale_mastery":
        return "review"
    if reason == "bridge_gap":
        return "bridge_check"
    if reason == "end_of_unit":
        return "final_quiz"
    if intent == "assess_knowledge":
        return "placement"
    return "review"


@dataclass(slots=True)
class ReplanValidationResult:
    accepted: bool
    rejected_reason: str | None = None


def start_assessment_not_implemented() -> ReplanValidationResult:
    return ReplanValidationResult(accepted=False, rejected_reason="not_implemented")


async def validate_replan_request(request, user_id: str) -> ReplanValidationResult:
    """V1 stub: no DB-backed evidence validation or mutation is wired yet."""
    assessment_session_id = getattr(request, "assessment_session_id", None)
    source_unit_ids = getattr(request, "source_canonical_unit_ids", [])
    if not assessment_session_id and not source_unit_ids:
        return ReplanValidationResult(accepted=False, rejected_reason="missing_evidence")
    return ReplanValidationResult(accepted=False, rejected_reason="not_implemented")
```

- [ ] **Step 4: Wire action endpoints**

Modify `src/routers/agent.py` imports:

```python
from src.schemas.agent import (
    AgentActionResponse,
    AgentAssessmentWorkflowRequest,
    AgentAssessmentWorkflowResponse,
    RequestReplanActionRequest,
    StartAssessmentActionRequest,
)
from src.services.agent_assessment_workflow import AgentAssessmentWorkflowService
from src.services.agent_action_service import start_assessment_not_implemented, validate_replan_request
```

Add module-level workflow service and endpoints:

```python
assessment_workflow_service = AgentAssessmentWorkflowService()


async def _validate_workflow_candidates_in_scope(
    canonical_unit_ids: list[str],
    *,
    allowed_course_ids: list[str],
    db: AsyncSession,
) -> None:
    if not canonical_unit_ids:
        raise HTTPException(status_code=422, detail="candidateCanonicalUnitIds_required")

    repo = CanonicalContentRepository(db)
    units_by_id = await repo.get_canonical_units_by_ids(canonical_unit_ids)
    missing_ids = [unit_id for unit_id in canonical_unit_ids if unit_id not in units_by_id]
    if missing_ids:
        raise HTTPException(status_code=404, detail="canonical_unit_not_found")

    allowed = {course_id.lower() for course_id in allowed_course_ids}
    out_of_scope = [
        unit_id
        for unit_id, unit in units_by_id.items()
        if str(getattr(unit, "course_id", "")).lower() not in allowed
    ]
    if out_of_scope:
        raise HTTPException(status_code=403, detail="canonical_unit_out_of_scope")


@agent_router.post("/assessment-workflows", response_model=AgentAssessmentWorkflowResponse)
async def agent_start_assessment_workflow(
    body: AgentAssessmentWorkflowRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentAssessmentWorkflowResponse:
    if body.event != "start":
        raise HTTPException(status_code=422, detail="event_must_be_start")
    context = await _agent_context_for_user(user, db)
    await _validate_workflow_candidates_in_scope(
        body.candidate_canonical_unit_ids,
        allowed_course_ids=context.allowed_course_ids,
        db=db,
    )
    return assessment_workflow_service.start(
        user_id=str(user.id),
        candidate_canonical_unit_ids=body.candidate_canonical_unit_ids,
        question_budget=body.question_budget,
        phase=body.phase,
    )


@agent_router.post(
    "/assessment-workflows/{workflow_id}/resume",
    response_model=AgentAssessmentWorkflowResponse,
)
async def agent_resume_assessment_workflow(
    workflow_id: str,
    body: AgentAssessmentWorkflowRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentAssessmentWorkflowResponse:
    if body.event != "resume":
        raise HTTPException(status_code=422, detail="event_must_be_resume")
    try:
        return assessment_workflow_service.resume(
            workflow_id=workflow_id,
            user_id=str(user.id),
            decision=body.decision or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
```

Add action endpoints:

```python
@agent_router.post("/actions/start-assessment", response_model=AgentActionResponse)
async def agent_start_assessment(
    body: StartAssessmentActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentActionResponse:
    result = start_assessment_not_implemented()
    return AgentActionResponse(
        accepted=result.accepted,
        rejectedReason=result.rejected_reason,
        dryRun=True,
        impact=None,
    )


@agent_router.post("/actions/request-replan", response_model=AgentActionResponse)
async def agent_request_replan(
    body: RequestReplanActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentActionResponse:
    validation = await validate_replan_request(body, user_id=str(user.id))
    return AgentActionResponse(
        accepted=validation.accepted,
        rejectedReason=validation.rejected_reason,
        dryRun=body.dry_run,
        impact={"mode": "dry_run_only"} if validation.accepted and body.dry_run else None,
    )
```

Append to `tests/contract/test_agent_routes.py`:

```python
async def test_assessment_workflow_endpoint_returns_proposal_interrupt():
    expected = {
        "workflowId": "workflow-1",
        "status": "waiting_user_approval",
        "interrupt": {
            "type": "assessment_proposal",
            "estimatedQuestions": 15,
            "estimatedTimeMinutes": 23,
            "canonicalUnitIds": ["unit-a"],
            "scope": [],
            "difficultyMix": {"easy": 3, "medium": 8, "hard": 4, "application": 0},
            "reductionOptions": [],
        },
        "actions": [],
        "trace": {"orchestrator": "langgraph"},
    }

    with patch(
        "src.routers.agent.assessment_workflow_service.start",
        return_value=expected,
    ), patch(
        "src.routers.agent._validate_workflow_candidates_in_scope",
        new=AsyncMock(return_value=None),
    ), patch(
        "src.routers.agent._agent_context_for_user",
        new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/agent/assessment-workflows",
                json={
                    "event": "start",
                    "candidateCanonicalUnitIds": ["unit-a"],
                    "questionBudget": 15,
                    "phase": "skip_verification",
                },
            )

    assert response.status_code == 200
    assert response.json()["status"] == "waiting_user_approval"
    assert response.json()["interrupt"]["type"] == "assessment_proposal"


async def test_assessment_workflow_start_rejects_out_of_scope_candidates():
    with patch(
        "src.routers.agent.CanonicalContentRepository.get_canonical_units_by_ids",
        new=AsyncMock(
            return_value={
                "unit-outside-scope": SimpleNamespace(
                    unit_id="unit-outside-scope",
                    course_id="CS999",
                )
            }
        ),
    ), patch(
        "src.routers.agent._agent_context_for_user",
        new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/agent/assessment-workflows",
                json={
                    "event": "start",
                    "candidateCanonicalUnitIds": ["unit-outside-scope"],
                    "questionBudget": 15,
                    "phase": "skip_verification",
                },
            )

    assert response.status_code == 403


async def test_assessment_workflow_start_rejects_resume_event():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/assessment-workflows",
            json={
                "event": "resume",
                "candidateCanonicalUnitIds": ["unit-a"],
                "questionBudget": 15,
                "phase": "skip_verification",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "event_must_be_start"


async def test_assessment_workflow_resume_maps_reduce_response():
    expected = {
        "workflowId": "workflow-1",
        "status": "waiting_user_approval",
        "interrupt": {
            "type": "assessment_proposal",
            "estimatedQuestions": 15,
            "estimatedTimeMinutes": 23,
            "canonicalUnitIds": ["unit-a"],
            "scope": [],
            "difficultyMix": {"easy": 3, "medium": 8, "hard": 4, "application": 0},
            "reductionOptions": [],
        },
        "actions": [],
        "trace": {"orchestrator": "langgraph"},
    }

    with patch(
        "src.routers.agent.assessment_workflow_service.resume",
        return_value=expected,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/agent/assessment-workflows/workflow-1/resume",
                json={
                    "event": "resume",
                    "decision": {"action": "reduce", "questionBudget": 15},
                },
            )

    assert response.status_code == 200
    assert response.json()["interrupt"]["estimatedQuestions"] == 15


async def test_assessment_workflow_resume_rejects_start_event():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/assessment-workflows/workflow-1/resume",
            json={"event": "start", "decision": {"action": "approve"}},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "event_must_be_resume"


async def test_assessment_workflow_resume_maps_approve_response():
    expected = {
        "workflowId": "workflow-1",
        "status": "assessment_ready",
        "interrupt": None,
        "actions": [
            {
                "type": "start_assessment",
                "label": "Start assessment",
                "canonical_unit_ids": ["unit-a"],
                "default_phase": "skip_verification",
                "eligible": False,
                "disabledReason": "not_implemented",
            }
        ],
        "trace": {"orchestrator": "langgraph"},
    }

    with patch(
        "src.routers.agent.assessment_workflow_service.resume",
        return_value=expected,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/agent/assessment-workflows/workflow-1/resume",
                json={"event": "resume", "decision": {"action": "approve"}},
            )

    assert response.status_code == 200
    assert response.json()["status"] == "assessment_ready"
    assert response.json()["actions"][0]["eligible"] is False
    assert response.json()["actions"][0]["disabledReason"] == "not_implemented"


async def test_assessment_workflow_resume_maps_ownership_error_to_403():
    with patch(
        "src.routers.agent.assessment_workflow_service.resume",
        side_effect=PermissionError("workflow_out_of_scope"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/agent/assessment-workflows/workflow-1/resume",
                json={"event": "resume", "decision": {"action": "approve"}},
            )

    assert response.status_code == 403


async def test_assessment_workflow_resume_maps_unknown_workflow_to_404():
    with patch(
        "src.routers.agent.assessment_workflow_service.resume",
        side_effect=ValueError("workflow_not_found"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/agent/assessment-workflows/missing-workflow/resume",
                json={"event": "resume", "decision": {"action": "approve"}},
            )

    assert response.status_code == 404


async def test_replan_action_is_disabled_until_db_validation_is_wired():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/actions/request-replan",
            json={
                "assessmentSessionId": "session-a",
                "sourceCanonicalUnitIds": ["unit-a"],
                "reason": "assessment_completed",
                "dryRun": True,
            },
        )

    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert response.json()["rejectedReason"] == "not_implemented"


async def test_start_assessment_action_is_disabled_until_wired():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/actions/start-assessment",
            json={
                "canonicalUnitIds": ["unit-a"],
                "phase": "skip_verification",
                "reason": "self_report_skip",
            },
        )

    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert response.json()["rejectedReason"] == "not_implemented"
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/services/test_agent_action_service.py tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/schemas/agent.py src/services/agent_action_service.py src/routers/agent.py tests/services/test_agent_action_service.py tests/contract/test_agent_routes.py
git commit -m "feat: add agent action validation stubs"
```

---

### Task 12.5: Frontend AI Assistant Route

**Files:**
- Create: `frontend/app/agent/page.tsx`
- Create: `frontend/components/agent/AgentChatPage.tsx`
- Modify: `frontend/components/layout/navItems.ts`
- Modify: `frontend/middleware.ts`
- Test: `frontend/tests/routes/agent/page.test.tsx`
- Modify: adjacent nav/middleware tests as needed.

- [ ] **Step 1: Add route and navigation tests**

Tests should assert:

- The global authenticated nav label is `AI Assistant`, not `AI Tutor`.
- `/agent` renders a normal chatbot-like page with an input and message transcript.
- `/agent` renders a left chat-history sidebar on desktop with `New chat`, search/filter, active session highlight, and sessions grouped by `Today`, `Previous 7 days`, and `Older`.
- Chat-history items show title, preview, and updated time only. Do not render category labels such as `Assessment`, `Path`, `Course`, or `General`.
- Starting a new chat creates a new conversation UI state and does not hydrate messages or memory summary from previous chat sessions.
- Agent responses render citations/direct links to `learn_href`.
- Agent responses render action cards/buttons, including `start_assessment_workflow`, `continue_assessment_workflow`, and disabled `start_assessment` states.
- Assessment workflow cards render a proposal/negotiation state with exact question count, scope, difficulty mix, rationale, reduction options, and approval action. They must not render fixed onboarding-style `Quick` / `Balanced` / `Thorough` modes.
- The right context panel renders session-scoped assistant memory status: recent message window, last summary update, and read-only memory summary. New chats show empty memory.
- Legacy `/tutor` redirects or aliases to `/agent` according to the migration decision.
- The Lecture AI Tutor panel inside `/courses/:course/learn/:unit` still says `AI Tutor` and remains lecture-scoped.

- [ ] **Step 2: Implement minimal UI**

Implement a focused chat shell:

- POST messages to `/api/agent/chat`.
- Load chat history from `GET /api/agent/conversations`.
- Create a new session with `POST /api/agent/conversations`.
- Load selected conversation messages from `GET /api/agent/conversations/{conversationId}`.
- Load selected conversation memory from `GET /api/agent/conversations/{conversationId}/memory`.
- Render `answer.markdown`.
- Render `citations` as direct course/lecture/unit links.
- Render `actions` as buttons/cards below the assistant message.
- Render chat history from session data:
  - `New chat` creates a new empty conversation.
  - Existing sessions remain available in the sidebar.
  - No session category badges in V1 because one conversation can mix path, assessment, and course questions.
- Render session memory as same-session context only:
  - Keep latest 8-12 messages as short-term context.
  - Show summary status (`empty`, `fresh`, `stale`, `updating`) for older turns in the current session.
  - Do not use previous chat-session memory in a new chat.
  - Use latest five current-lecture AI Tutor Q&A turns only when route context points to the current player/lecture.
- Render assessment proposal cards:
  - `start_assessment_workflow` calls `POST /api/agent/assessment-workflows` with candidate canonical unit IDs,
  - `continue_assessment_workflow` renders the returned workflow proposal/interruption,
  - show exact `estimatedQuestions` and estimated time,
  - show unit/KP scope and difficulty mix,
  - show why this many questions are needed,
  - offer reduction actions such as `core only`, `remove application questions`, and `minimum evidence`,
  - show `Start assessment` only after proposal approval.
- For outside-current-path answers, render the warning text from the response without switching path.
- Do not expose full trace to normal users.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/agent/page.tsx frontend/components/agent/AgentChatPage.tsx frontend/components/layout/navItems.ts frontend/middleware.ts frontend/tests/routes/agent/page.test.tsx
git commit -m "feat: add ai assistant agent route"
```

---

### Task 13: Documentation And Final Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-04-29-path-agent-rag-plan.md`
- Modify: `docs/superpowers/plans/2026-04-29-path-agent-rag-implementation.md`

- [ ] **Step 1: Add implementation status note to design plan**

Append this section to `docs/superpowers/plans/2026-04-29-path-agent-rag-plan.md`:

```markdown
## 17. Implementation Plan Link

Implementation tasks are tracked in `docs/superpowers/plans/2026-04-29-path-agent-rag-implementation.md`.
```

- [ ] **Step 2: Run backend focused tests**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/repositories/test_canonical_content_repo.py tests/repositories/test_agent_conversation_repo.py tests/services/test_agent_query_normalizer.py tests/services/test_agent_context_service.py tests/services/test_agent_navigation_service.py tests/services/test_agent_search_service.py tests/services/test_agent_requirement_service.py tests/services/test_agent_unit_context_service.py tests/services/test_agent_tutor_memory_service.py tests/services/test_agent_conversation_service.py tests/services/test_agent_chat_service.py tests/services/test_agent_assessment_workflow.py tests/services/test_agent_action_service.py tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 3: Run existing adjacent tests**

Run:

```bash
pytest tests/repositories/test_canonical_content_repo.py tests/services/test_recommendation_engine_canonical_cutover.py tests/contract/test_canonical_content_routes.py -q
```

Expected: PASS.

- [ ] **Step 4: Optional frontend type-check**

Run:

```bash
npm run type-check
```

Expected: PASS or only documented unrelated existing failures. If unrelated failures occur, record exact file/error in the final response and do not modify unrelated files.

- [ ] **Step 5: Commit final docs**

```bash
git add docs/superpowers/plans/2026-04-29-path-agent-rag-plan.md docs/superpowers/plans/2026-04-29-path-agent-rag-implementation.md
git commit -m "docs: link path agent implementation plan"
```

---

## Self-Review

Spec coverage:

- Chat/orchestration endpoint with explicit `AgentIntent` override and deterministic intent routing table: Task 9 and Task 11.
- Trace exposure and full-trace restriction: Task 1 and Task 9.
- User/path scope context: Task 3 and Task 11.
- Unit-centered search with query normalization and score-first result ranking: Task 2, Task 4, Task 6.
- Runtime navigation data: Task 4, Task 5, Task 6.
- Unit context and transcript snippets: Task 1, Task 4, Task 8, Task 11.
- Last-five current-lecture Tutor memory context: Task 8.5 and Task 9.
- Conversation sessions and same-session memory summaries: Task 8.75 and Task 12.5.
- Path requirements/prerequisite graph with content/KP policy and real `learner_mastery_kp` mastery overlay: Task 4 and Task 7.
- Assessment/replan workflow orchestration: Task 1 and Task 10.
- Assessment/replan action guardrails: Task 1, Task 9, Task 10, Task 12.
- Frontend `/agent` AI Assistant route, session history, session-scoped memory UI, and proposal/negotiation action cards: Task 12.5.
- Public API contracts: Task 11 and Task 12.
- Verification and docs handoff: Task 13.

Known V1 limits:

- Search implementation starts with deterministic LIKE-style matching, content-policy filters, and score-ranked results; it can be upgraded to PostgreSQL `tsvector`/BM25 ranking without changing API shape.
- Chat response is template-based in V1; LLM wording can be added behind `AgentChatService` once tool traces are stable.
- LangGraph is used only for assessment workflow proposal/approval state; general RAG/chat stays custom and deterministic.
- Workflow start validates candidate canonical unit IDs against the authenticated user's allowed course scope before creating graph state.
- Workflow resume validates stored workflow ownership against the authenticated user before accepting a resume decision.
- LangGraph checkpointer is process-local in the V1 task to keep implementation small. Swap to a DB-backed checkpointer or `planner_session_state` persistence before horizontal scaling.
- Replan mutation is intentionally not implemented; Task 12 exposes backend-mediated validation and dry-run action contracts only.
