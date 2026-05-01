# LangGraph Agent Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/agent` keyword-routed chat path with a production LangGraph orchestration layer that is context-aware, replay-safe, idempotent, and separate from the lecture AI Tutor.

**Architecture:** Add durable graph persistence primitives first, then introduce typed graph contracts, router/canonicalizer/policy/composer nodes, and finally wire `/api/agent/chat` through `AgentGraphService`. Assessment and replan proposals become durable pending actions with interrupt/resume semantics; retries and concurrent runs are controlled by `incoming_message_id`, `thread_id`, response refs, run statuses, and PostgreSQL advisory locks.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, Pydantic v2, LangGraph 1.1, PostgreSQL, pytest/pytest-asyncio, httpx ASGI tests, Next.js/TypeScript frontend.

---

## Current Implementation Status

Last updated: 2026-05-01 after commits `f0f904b`, `1299233`, `6723d0e`, `6ab4aeb`, and the durable clarification-state follow-up.

Status meanings:

- `done`: implemented and verified for the intended production path.
- `partial`: some production behavior exists, but the task still has known gaps.
- `bootstrap-only`: intentionally implemented as an integration seam or placeholder, not production-complete.
- `production-hardening added during implementation`: not originally called out as a standalone task, but added because implementation exposed a production failure mode.

| Task | Status | Notes |
|---|---|---|
| Task 1: Schema And Runtime Contract Tests | done | Agent request/response/action contracts, in-progress payload, and graph contract tests are implemented. |
| Task 2: Graph Runtime Persistence | done | Runtime tables, `thread_id`, repository, response refs, pending actions, run statuses, idempotent pending-action lookup, repository tests, and migration checks exist. Repository DB tests skip when the local test DB has not applied the migration. |
| Task 3: Bootstrap Router Seam, Slot Resolver, Policy, And Composer | bootstrap-only | Deterministic router exists only as a test/bootstrap seam. It must not be used as production fallback. Slot resolver, policy, and composer primitives exist. |
| Task 4: Production Structured Router | partial | `StructuredAgentRouter` and factory exist. Production wiring uses the factory, but provider-level failure/evaluation coverage still needs hardening. |
| Task 5: Minimal Bootstrap LangGraph Service Skeleton And Tool Nodes | bootstrap-only | Graph skeleton and typed tool nodes are implemented. This task remains intentionally non-spec-complete. |
| Task 6: Production Router Wiring And Fail-Safe | done | `/api/agent/chat` instantiates the production structured router factory; deterministic keyword routing is not used as production fallback. |
| Task 7: Search Scope Escalation | done | Current-path-first search and scope expansion offer are implemented. |
| Task 8: Scope Expansion Confirmation And Expanded Retrieval | done | Approval phrase continues expanded retrieval; pending scope-expansion clarification is stored in thread memory and cleared after resolution. |
| Task 9: Router Integration, Dedupe, Locking, And 409 Responses | done | Chat route goes through `AgentGraphService`, dedupes by `incomingMessageId`, checks active runs, and returns `409 in_progress`. |
| Task 10: Durable Run Lifecycle In `AgentGraphService` | done | Run creation/running/interrupted/succeeded/failed, response refs, active non-interrupted resume checks, and checkpoint id capture from LangGraph snapshots are wired. |
| Task 10a: Interrupted Run Finalization | production-hardening added during implementation | Added `6723d0e` so approve/reject/expire finalizes the latest interrupted run and prevents permanent `409 in_progress` locks. |
| Task 11: Pending Action API Shell And Continuation Endpoint | done | API shell, continuation contract, response persistence, and resume response replay by `incomingMessageId` are implemented. |
| Task 12: Path Switch Pending Action Workflow | done | Path switch intent, validation, proposal payload, pending action, commit service, and result persistence are implemented. Ops/dashboard coverage remains outside this task. |
| Task 13: Real LangGraph Interrupt/Resume Action Flow | done | Proposal nodes persist pending actions before a separate `interrupt()` node; `/actions/continue` resumes with `Command(resume=...)`; commit side effects run after resume with idempotency through pending-action `result_json`. Assessment and replan now call authoritative backend services. |
| Task 14: Memory Compaction And Operational Safety | partial | Versioned `memory_ref` persistence, durable clarification state, checkpoint id capture, and pending-action janitor exist. Postgres checkpointer wiring and ops dashboards remain follow-up hardening. |
| Task 15: Frontend Idempotency And Action IDs | done | Stable `incomingMessageId`, action ids, and `/actions/continue` approve/reject UI are implemented and covered by page tests. Unrelated dirty UI hunks remain isolated from the committed diff. |
| Task 16: Evaluation Suite, Janitor, And Operational Checks | partial | Janitor primitive, migration checks, action-resume tests, and route/frontend coverage exist. Full LangSmith/offline eval suite and ops dashboards remain follow-up work. |
| Task 17: Final Integration Verification And Legacy Path Deprecation | partial | Backend subset and frontend type-check/page tests pass. Legacy `AgentChatService` remains present as compatibility/reference until final deprecation is explicitly scheduled. |

### Done-True Vs Temporary Boundaries

Done-true in the current implementation:

- Production route wiring through `AgentGraphService`.
- Structured router factory on the production route.
- Inbound request idempotency using `incomingMessageId`.
- `409 in_progress` response contract.
- Per-thread lock service.
- Durable graph run rows and deterministic response refs.
- Pending action persistence for action proposals.
- Native LangGraph `interrupt()` / `Command(resume=...)` boundary for pending actions.
- Authoritative assessment/replan/path-switch commit calls after resume.
- Versioned `memory_ref` writes to conversation memory.
- Durable pending clarification storage for scope-expansion approvals.
- Checkpoint id capture from LangGraph state snapshots.
- No-evidence/no-grounded-answer composer guard.
- Search scope escalation offer and expanded-search continuation.
- Interrupted-run finalization after action approve/reject/expire.
- Frontend pending action approve/reject continuation.

Done-temporary or partial:

- Production Postgres checkpointer is dependency-injection ready, but the app still defaults to `InMemorySaver` unless a durable checkpointer is provided.
- Full offline/online eval and ops dashboards are not implemented in this code pass.
- Legacy `AgentChatService` is not removed yet.

### Implementation Deviations

- Added explicit interrupted-run finalization to prevent permanent `409 in_progress` locks.
- LangGraph is lazy-imported for non-production/test environments; production still requires LangGraph.
- Added native LangGraph `interrupt()` / `Command(resume=...)` for pending action confirmations after the initial shell implementation.
- Added `AgentActionCommitService` so assessment/replan approvals call authoritative backend services instead of generic confirmation.
- Added checkpoint id capture from LangGraph state snapshots and versioned `memory_ref` persistence into conversation memory.
- Folded scope-expansion pending clarification into the conversation memory summary store; process memory is now only a hot cache.
- Frontend retry idempotency was implemented; unrelated UI polish hunks were left out of the committed agent-flow changes.

---

## File Structure

Create:

- `src/models/agent_graph.py` - SQLAlchemy models for graph runs, pending actions, response payloads, and trace events.
- `src/repositories/agent_graph_repo.py` - persistence/idempotency helpers for graph runs, pending actions, response refs, lock metadata, and retry state.
- `src/services/agent_lock_service.py` - PostgreSQL advisory lock helper keyed by `thread_id`.
- `src/services/agent_memory_compaction_service.py` - versioned thread summary compaction and `memory_ref` management.
- `src/services/agent_graph_contracts.py` - Pydantic/domain contracts for checkpoint state, routing, slots, policy, pending actions, typed tool results, and graph node names.
- `src/services/agent_graph_router.py` - structured intent router and deterministic test router seam.
- `src/services/agent_structured_router.py` - production structured-output LLM router with schema validation and clarify fallback.
- `src/services/agent_router_factory.py` - production router factory that builds `StructuredAgentRouter` from app settings and never falls back to deterministic keyword routing.
- `src/services/agent_slot_resolver.py` - deterministic canonicalization from extracted slots to canonical unit/course/planner ids.
- `src/services/agent_search_scope_service.py` - current-path, explicit-path, and expanded-path search scope policy.
- `src/services/agent_policy_service.py` - `PolicyDecision` validation before tool execution/action proposal.
- `src/services/agent_path_switch_service.py` - validated active-path switch proposal and commit service using `GoalPreference.selected_course_ids` and planner regeneration.
- `src/services/agent_tool_nodes.py` - LangGraph intent nodes backed by existing deterministic services.
- `src/services/agent_response_composer.py` - typed response composer enforcing no-evidence/no-grounded-answer.
- `src/services/agent_graph_service.py` - graph construction/invoke/resume orchestration and route integration API.
- `alembic/versions/20260501_agent_graph_runtime.py` - additive migration for graph runtime tables and `agent_conversations.thread_id`.
- `tests/services/test_agent_graph_contracts.py`
- `tests/repositories/test_agent_graph_repo.py`
- `tests/services/test_agent_graph_router.py`
- `tests/services/test_agent_structured_router.py`
- `tests/services/test_agent_router_factory.py`
- `tests/services/test_agent_slot_resolver.py`
- `tests/services/test_agent_search_scope_service.py`
- `tests/services/test_agent_policy_service.py`
- `tests/services/test_agent_path_switch_service.py`
- `tests/services/test_agent_graph_actions.py`
- `tests/services/test_agent_response_composer.py`
- `tests/services/test_agent_graph_service.py`
- `tests/contract/test_agent_graph_routes.py`
- `frontend/tests/lib/agent/agentInProgress.test.ts`

Modify:

- `src/models/__init__.py` - import new graph models for metadata discovery.
- `src/models/agent_conversation.py` - add `thread_id` to `AgentConversation`.
- `src/repositories/agent_conversation_repo.py` - create/get conversations with thread ids and idempotent message helpers.
- `src/schemas/agent.py` - add `incomingMessageId`, `AgentInProgressResponse`, `AgentActionResumeRequest`, action ids/status/expiry, and `clarify` intent.
- `src/repositories/goal_preference_repo.py` - support active path switch commits by updating selected course ids.
- `src/routers/agent.py` - route chat/continuation through `AgentGraphService`; preserve existing direct search/context endpoints.
- `frontend/features/agent/api.ts` - send `incomingMessageId`, parse `409 in_progress`, include `actionId`.
- `frontend/features/agent/components/AgentChatPage.tsx` - generate stable message ids and send action continuation payloads.
- `tests/test_agent_schema_contract.py`
- `tests/contract/test_agent_routes.py`

Do not modify:

- Lecture AI Tutor routes/services unless a shared model import requires a no-behavior metadata import.
- Assessment scoring/mastery mutation logic except through the existing backend action services.
- Planner generation logic except through validated replan action services.

---

### Task 1: Schema And Runtime Contract Tests `[done]`

**Files:**
- Modify: `src/schemas/agent.py`
- Create: `src/services/agent_graph_contracts.py`
- Test: `tests/test_agent_schema_contract.py`
- Test: `tests/services/test_agent_graph_contracts.py`

- [ ] **Step 1: Add failing schema tests for ids, in-progress response, action continuation, and action ids**

Append to `tests/test_agent_schema_contract.py`:

```python
from src.schemas.agent import AgentActionResumeRequest, AgentChatRequest, AgentInProgressResponse


def test_agent_chat_request_requires_or_generates_incoming_message_id_contract():
    request = AgentChatRequest(
        message="Where is receptive field taught?",
        incomingMessageId="msg-client-1",
    )

    assert request.incoming_message_id == "msg-client-1"


def test_in_progress_response_contract_uses_camel_case():
    response = AgentInProgressResponse(
        status="in_progress",
        conversationId="conv-1",
        threadId="thread-1",
        graphRunId="run-1",
        retryAfterMs=1000,
    )

    assert response.status == "in_progress"
    assert response.thread_id == "thread-1"
    assert response.model_dump(by_alias=True)["retryAfterMs"] == 1000


def test_action_resume_request_requires_action_id_and_message_id():
    request = AgentActionResumeRequest(
        conversationId="conv-1",
        actionId="act-1",
        decision="approve",
        incomingMessageId="msg-client-2",
    )

    assert request.action_id == "act-1"
    assert request.decision == "approve"
```

- [ ] **Step 2: Create failing graph contract tests**

Create `tests/services/test_agent_graph_contracts.py`:

```python
from src.schemas.agent import AgentIntent
from src.services.agent_graph_contracts import (
    AGENT_INTENT_NODE_REGISTRY,
    AgentGraphRunStatus,
    AgentInProgressError,
    PolicyDecision,
)


def test_every_agent_intent_has_registered_node():
    intents = set(AgentIntent.__args__)
    assert intents == set(AGENT_INTENT_NODE_REGISTRY)
    assert "request_path_switch" in intents


def test_graph_run_status_machine_values_are_stable():
    assert AgentGraphRunStatus.__args__ == (
        "created",
        "running",
        "interrupted",
        "succeeded",
        "failed_retryable",
        "failed_terminal",
        "cancelled",
    )


def test_policy_decision_has_codes_and_audit_context():
    decision = PolicyDecision(
        allow=False,
        codes=["COURSE_SCOPE_MISMATCH"],
        user_safe_message="I cannot access that course in your current scope.",
        audit_context={"requestedCourseIds": ["CS999"]},
    )

    assert decision.allow is False
    assert decision.codes == ["COURSE_SCOPE_MISMATCH"]


def test_in_progress_error_payload_is_stable():
    error = AgentInProgressError(
        conversation_id="conv-1",
        thread_id="thread-1",
        graph_run_id="run-1",
        retry_after_ms=1000,
    )

    assert error.to_response().model_dump(by_alias=True) == {
        "status": "in_progress",
        "conversationId": "conv-1",
        "threadId": "thread-1",
        "graphRunId": "run-1",
        "retryAfterMs": 1000,
    }


def test_agent_slots_track_search_scope_state():
    from src.services.agent_graph_contracts import AgentSlots

    slots = AgentSlots(
        raw_topic="attention mask",
        search_scope="explicit_path",
        requested_path_id="nlp",
        resolved_search_path_ids=["nlp"],
    )

    assert slots.search_scope == "explicit_path"
    assert slots.scope_expansion_offered is False
    assert slots.scope_expansion_approved is False
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/services/test_agent_graph_contracts.py -q
```

Expected: failures for missing `incoming_message_id`, missing response/request models, and missing graph contract module.

- [ ] **Step 4: Implement schema additions**

In `src/schemas/agent.py`, add `"clarify"` and `"request_path_switch"` to `AgentIntent`, add `incoming_message_id` to `AgentChatRequest`, add action metadata to `AgentAction`, and add new request/response models:

```python
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
    "request_path_switch",
    "clarify",
]


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    incoming_message_id: str = Field(alias="incomingMessageId", min_length=1)
    conversation_id: str | None = Field(default=None, alias="conversationId")
    route_context: RouteContext | None = Field(default=None, alias="routeContext")
    intent: AgentIntent | None = None
    response_mode: Literal["non_streaming", "streaming"] = Field(
        default="non_streaming", alias="responseMode"
    )
    trace_mode: Literal["none", "summary", "full"] = Field(default="summary", alias="traceMode")

    model_config = ConfigDict(populate_by_name=True)


class AgentInProgressResponse(BaseModel):
    status: Literal["in_progress"]
    conversation_id: str = Field(alias="conversationId")
    thread_id: str = Field(alias="threadId")
    graph_run_id: str = Field(alias="graphRunId")
    retry_after_ms: int = Field(alias="retryAfterMs", ge=0)

    model_config = ConfigDict(populate_by_name=True)


class AgentActionResumeRequest(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    action_id: str = Field(alias="actionId")
    decision: Literal["approve", "reject", "edit"]
    edit_payload: dict[str, Any] | None = Field(default=None, alias="editPayload")
    incoming_message_id: str = Field(alias="incomingMessageId", min_length=1)

    model_config = ConfigDict(populate_by_name=True)
```

In `AgentAction`, add:

```python
    # Add "request_path_switch" to the existing AgentAction.type Literal.
    action_id: str | None = Field(default=None, alias="actionId")
    status: str | None = None
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
```

- [ ] **Step 5: Implement graph contracts**

Create `src/services/agent_graph_contracts.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.agent import AgentAction, AgentAnswer, AgentCitation, AgentFallback, AgentInProgressResponse, AgentIntent, AgentWarning, RouteContext


AgentGraphRunStatus = Literal[
    "created",
    "running",
    "interrupted",
    "succeeded",
    "failed_retryable",
    "failed_terminal",
    "cancelled",
]

AGENT_INTENT_NODE_REGISTRY: dict[AgentIntent, str] = {
    "explain_concept": "explain_concept_node",
    "find_content": "find_content_node",
    "navigate_to_unit": "navigate_to_unit_node",
    "ask_what_next": "ask_what_next_node",
    "assess_knowledge": "assess_knowledge_node",
    "request_replan": "request_replan_node",
    "explain_planner_decision": "explain_planner_decision_node",
    "summarize_progress": "summarize_progress_node",
    "general_course_question": "general_course_question_node",
    "request_path_switch": "request_path_switch_node",
    "clarify": "clarify_node",
}


class AgentSlots(BaseModel):
    raw_topic: str | None = None
    target_path: Literal["computer_vision", "nlp"] | None = None
    canonical_unit_ids: list[str] = Field(default_factory=list)
    course_ids: list[str] = Field(default_factory=list)
    ambiguity_options: list[dict[str, Any]] = Field(default_factory=list)
    search_scope: Literal["current_path", "explicit_path", "expanded_paths"] = "current_path"
    scope_expansion_offered: bool = False
    scope_expansion_approved: bool = False
    requested_path_id: str | None = None
    resolved_search_path_ids: list[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    allow: bool
    codes: list[str] = Field(default_factory=list)
    user_safe_message: str | None = None
    audit_context: dict[str, Any] | None = None


class PendingAction(BaseModel):
    action_id: str
    type: Literal["propose_assessment", "start_assessment", "request_replan", "request_path_switch"]
    status: Literal["proposed", "awaiting_confirmation", "confirmed", "cancelled", "committed", "expired"]
    payload_ref: str
    idempotency_key: str
    expires_at: datetime


class AgentCheckpointState(BaseModel):
    state_version: int = 1
    thread_id: str
    conversation_id: str
    user_id: str
    incoming_message_id: str
    route_context: RouteContext | None = None
    intent: AgentIntent | None = None
    intent_confidence: float = 0.0
    slots: AgentSlots = Field(default_factory=AgentSlots)
    policy: PolicyDecision | None = None
    pending_action: PendingAction | None = None
    last_committed_action_id: str | None = None
    last_committed_action_type: str | None = None
    learning_context_ref: str | None = None
    memory_ref: str | None = None
    tool_result_ref: str | None = None
    response_ref: str | None = None
    trace_id: str


class ToolResult(BaseModel):
    kind: Literal[
        "find_content",
        "explain_concept",
        "navigation",
        "planner_decision",
        "what_next",
        "assessment_proposal",
        "replan_proposal",
        "path_switch_proposal",
        "progress_summary",
        "clarification",
    ]
    answer_markdown: str | None = None
    citations: list[AgentCitation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    warning: AgentWarning | None = None
    fallback: AgentFallback | None = None
    requires_evidence: bool = False


class ComposedAgentResponse(BaseModel):
    answer: AgentAnswer
    citations: list[AgentCitation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    warning: AgentWarning | None = None
    fallback: AgentFallback | None = None


class AgentInProgressError(Exception):
    def __init__(self, conversation_id: str, thread_id: str, graph_run_id: str, retry_after_ms: int = 1000):
        self.conversation_id = conversation_id
        self.thread_id = thread_id
        self.graph_run_id = graph_run_id
        self.retry_after_ms = retry_after_ms

    def to_response(self) -> AgentInProgressResponse:
        return AgentInProgressResponse(
            status="in_progress",
            conversationId=self.conversation_id,
            threadId=self.thread_id,
            graphRunId=self.graph_run_id,
            retryAfterMs=self.retry_after_ms,
        )
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/services/test_agent_graph_contracts.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/schemas/agent.py src/services/agent_graph_contracts.py tests/test_agent_schema_contract.py tests/services/test_agent_graph_contracts.py
git commit -m "feat: add agent graph runtime contracts"
```

---

### Task 2: Graph Runtime Persistence `[done]`

**Files:**
- Create: `src/models/agent_graph.py`
- Modify: `src/models/agent_conversation.py`
- Modify: `src/models/__init__.py`
- Create: `alembic/versions/20260501_agent_graph_runtime.py`
- Create: `src/repositories/agent_graph_repo.py`
- Modify: `src/repositories/agent_conversation_repo.py`
- Test: `tests/repositories/test_agent_graph_repo.py`
- Test: `tests/test_agent_schema_contract.py`

- [ ] **Step 1: Write failing repository tests for thread id, run status, response refs, pending actions, and in-progress dedupe**

Create `tests/repositories/test_agent_graph_repo.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.models.agent_conversation import AgentConversation
from src.repositories.agent_graph_repo import AgentGraphRepository

pytestmark = pytest.mark.asyncio


async def test_create_run_and_complete_response_ref(db_session):
    user_id = uuid4()
    conversation = AgentConversation(user_id=user_id, thread_id="thread-1")
    db_session.add(conversation)
    await db_session.flush()

    repo = AgentGraphRepository(db_session)
    run = await repo.create_run(
        conversation_id=conversation.id,
        thread_id="thread-1",
        incoming_message_id="msg-1",
    )
    await repo.store_response_payload("resp-1", {"answer": {"markdown": "Done"}})
    await repo.mark_run_succeeded(run.id, response_ref="resp-1", checkpoint_id="chk-1")
    existing = await repo.get_completed_response_ref(
        conversation_id=conversation.id,
        thread_id="thread-1",
        incoming_message_id="msg-1",
    )

    assert existing == "resp-1"


async def test_active_run_reports_in_progress(db_session):
    user_id = uuid4()
    conversation = AgentConversation(user_id=user_id, thread_id="thread-2")
    db_session.add(conversation)
    await db_session.flush()

    repo = AgentGraphRepository(db_session)
    run = await repo.create_run(
        conversation_id=conversation.id,
        thread_id="thread-2",
        incoming_message_id="msg-2",
    )
    await repo.mark_run_running(run.id)
    active = await repo.get_active_run(thread_id="thread-2")

    assert active is not None
    assert active.id == run.id
    assert active.status == "running"


async def test_pending_action_expiry(db_session):
    user_id = uuid4()
    conversation = AgentConversation(user_id=user_id, thread_id="thread-3")
    db_session.add(conversation)
    await db_session.flush()

    repo = AgentGraphRepository(db_session)
    action = await repo.upsert_pending_action(
        action_id="act-1",
        conversation_id=conversation.id,
        thread_id="thread-3",
        user_id=user_id,
        action_type="request_replan",
        payload_ref="payload-1",
        idempotency_key="idem-1",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    expired = await repo.expire_pending_actions(now=datetime.now(UTC))

    assert action.action_id == "act-1"
    assert expired == 1
```

- [ ] **Step 2: Run failing repository tests**

Run:

```bash
pytest tests/repositories/test_agent_graph_repo.py -q
```

Expected: failures for missing models/repository and missing `thread_id` column.

- [ ] **Step 3: Add models**

Create `src/models/agent_graph.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentGraphRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_graph_runs"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    incoming_message_id: Mapped[str] = mapped_column(String(120), nullable=False)
    checkpoint_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    response_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="created", server_default="created")
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("conversation_id", "thread_id", "incoming_message_id", name="uq_agent_graph_run_message"),
        Index("ix_agent_graph_runs_thread_status", "thread_id", "status"),
    )


class AgentPendingAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_pending_actions"

    action_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="awaiting_confirmation", server_default="awaiting_confirmation")
    payload_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentResponsePayload(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_response_payloads"

    response_ref: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentTraceEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_trace_events"

    trace_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    graph_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_graph_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    node_name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
```

Modify `src/models/agent_conversation.py`:

```python
    thread_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
```

Add imports to `src/models/__init__.py`:

```python
from src.models.agent_graph import AgentGraphRun, AgentPendingAction, AgentResponsePayload, AgentTraceEvent
```

- [ ] **Step 4: Add Alembic migration**

Create `alembic/versions/20260501_agent_graph_runtime.py` with additive tables and `thread_id` backfill:

```python
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260501_agent_graph_runtime"
down_revision = "20260430_units_cat_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_conversations", sa.Column("thread_id", sa.String(length=80), nullable=True))
    op.execute("UPDATE agent_conversations SET thread_id = 'thread_' || id::text WHERE thread_id IS NULL")
    op.alter_column("agent_conversations", "thread_id", nullable=False)
    op.create_index("ix_agent_conversations_thread_id", "agent_conversations", ["thread_id"], unique=True)

    op.create_table(
        "agent_graph_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", sa.String(length=80), nullable=False),
        sa.Column("incoming_message_id", sa.String(length=120), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=160), nullable=True),
        sa.Column("response_ref", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="created", nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["agent_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "thread_id", "incoming_message_id", name="uq_agent_graph_run_message"),
    )
    op.create_index("ix_agent_graph_runs_thread_status", "agent_graph_runs", ["thread_id", "status"])

    op.create_table(
        "agent_response_payloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_ref", sa.String(length=160), nullable=False),
        sa.Column("payload_json", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_ref"),
    )
    op.create_table(
        "agent_pending_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", sa.String(length=80), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="awaiting_confirmation", nullable=False),
        sa.Column("payload_ref", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["agent_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
```

- [ ] **Step 5: Add migration safety checks**

Append to `tests/test_agent_schema_contract.py` or create `tests/test_agent_graph_runtime_migration.py`:

```python
from pathlib import Path


def test_agent_graph_runtime_migration_backfills_thread_id_and_uniqueness():
    text = Path("alembic/versions/20260501_agent_graph_runtime.py").read_text()

    assert "UPDATE agent_conversations SET thread_id" in text
    assert "thread_id IS NULL" in text
    assert "nullable=False" in text
    assert "ix_agent_conversations_thread_id" in text
    assert "unique=True" in text


def test_agent_graph_runtime_migration_has_run_status_and_dedupe_constraint():
    text = Path("alembic/versions/20260501_agent_graph_runtime.py").read_text()

    assert "agent_graph_runs" in text
    assert "uq_agent_graph_run_message" in text
    assert "incoming_message_id" in text
    assert "status" in text
```

Run:

```bash
pytest tests/test_agent_graph_runtime_migration.py -q
```

Expected: pass after the migration file is created.

- [ ] **Step 6: Implement repository helpers**

Create `src/repositories/agent_graph_repo.py` with methods used by the tests:

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_graph import AgentGraphRun, AgentPendingAction, AgentResponsePayload


class AgentGraphRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, conversation_id: UUID, thread_id: str, incoming_message_id: str) -> AgentGraphRun:
        existing = await self.session.execute(
            select(AgentGraphRun).where(
                AgentGraphRun.conversation_id == conversation_id,
                AgentGraphRun.thread_id == thread_id,
                AgentGraphRun.incoming_message_id == incoming_message_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = AgentGraphRun(conversation_id=conversation_id, thread_id=thread_id, incoming_message_id=incoming_message_id)
        self.session.add(row)
        await self.session.flush()
        return row

    async def mark_run_running(self, run_id: UUID) -> None:
        await self.session.execute(update(AgentGraphRun).where(AgentGraphRun.id == run_id).values(status="running"))
        await self.session.flush()

    async def mark_run_succeeded(self, run_id: UUID, response_ref: str, checkpoint_id: str | None) -> None:
        await self.session.execute(
            update(AgentGraphRun)
            .where(AgentGraphRun.id == run_id)
            .values(status="succeeded", response_ref=response_ref, checkpoint_id=checkpoint_id, completed_at=func.now())
        )
        await self.session.flush()

    async def get_completed_response_ref(self, conversation_id: UUID, thread_id: str, incoming_message_id: str) -> str | None:
        result = await self.session.execute(
            select(AgentGraphRun.response_ref).where(
                AgentGraphRun.conversation_id == conversation_id,
                AgentGraphRun.thread_id == thread_id,
                AgentGraphRun.incoming_message_id == incoming_message_id,
                AgentGraphRun.status == "succeeded",
            )
        )
        return result.scalar_one_or_none()

    async def get_active_run(self, thread_id: str) -> AgentGraphRun | None:
        result = await self.session.execute(
            select(AgentGraphRun).where(
                AgentGraphRun.thread_id == thread_id,
                AgentGraphRun.status.in_(["created", "running", "interrupted"]),
            )
        )
        return result.scalar_one_or_none()

    async def store_response_payload(self, response_ref: str, payload: dict) -> AgentResponsePayload:
        existing = await self.session.execute(select(AgentResponsePayload).where(AgentResponsePayload.response_ref == response_ref))
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = AgentResponsePayload(response_ref=response_ref, payload_json=payload)
        self.session.add(row)
        await self.session.flush()
        return row

    async def upsert_pending_action(self, *, action_id: str, conversation_id: UUID, thread_id: str, user_id: UUID, action_type: str, payload_ref: str, idempotency_key: str, expires_at: datetime) -> AgentPendingAction:
        existing = await self.session.execute(select(AgentPendingAction).where(AgentPendingAction.action_id == action_id))
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = AgentPendingAction(
            action_id=action_id,
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_id=user_id,
            type=action_type,
            status="awaiting_confirmation",
            payload_ref=payload_ref,
            idempotency_key=idempotency_key,
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def expire_pending_actions(self, now: datetime) -> int:
        result = await self.session.execute(
            update(AgentPendingAction)
            .where(AgentPendingAction.expires_at < now, AgentPendingAction.status == "awaiting_confirmation")
            .values(status="expired")
        )
        await self.session.flush()
        return int(result.rowcount or 0)
```

- [ ] **Step 7: Update conversation repository to create thread ids**

In `src/repositories/agent_conversation_repo.py`, change `create_conversation`:

```python
from uuid import uuid4

thread_id = f"thread_{uuid4()}"
row = AgentConversation(user_id=user_id, title=title, preview="", message_count=0, thread_id=thread_id)
```

- [ ] **Step 8: Run repository tests**

Run:

```bash
pytest tests/repositories/test_agent_graph_repo.py tests/services/test_agent_conversation_service.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add src/models/agent_graph.py src/models/agent_conversation.py src/models/__init__.py src/repositories/agent_graph_repo.py src/repositories/agent_conversation_repo.py alembic/versions/20260501_agent_graph_runtime.py tests/repositories/test_agent_graph_repo.py tests/test_agent_graph_runtime_migration.py
git commit -m "feat: add agent graph runtime persistence"
```

---

### Task 3: Bootstrap Router Seam, Slot Resolver, Policy, And Composer `[bootstrap-only]`

This task creates a deterministic router seam only for early tests and graph integration. It is not the production router and must not become the production fallback. The production structured-output router is implemented in a later task and must replace this seam before rollout.

**Files:**
- Create: `src/services/agent_graph_router.py`
- Create: `src/services/agent_slot_resolver.py`
- Create: `src/services/agent_policy_service.py`
- Create: `src/services/agent_response_composer.py`
- Test: `tests/services/test_agent_graph_router.py`
- Test: `tests/services/test_agent_slot_resolver.py`
- Test: `tests/services/test_agent_policy_service.py`
- Test: `tests/services/test_agent_response_composer.py`

- [ ] **Step 1: Write router adversarial tests**

Create `tests/services/test_agent_graph_router.py`:

```python
import pytest

from src.services.agent_graph_router import DeterministicAgentRouter


@pytest.mark.parametrize(
    ("message", "expected_intent"),
    [
        ("Giải thích skip connection", "explain_concept"),
        ("Quiz eligibility của unit này tính thế nào?", "general_course_question"),
        ("Cho tôi quiz về attention mechanism", "assess_knowledge"),
    ],
)
def test_router_uses_context_not_raw_keyword_traps(message, expected_intent):
    route = DeterministicAgentRouter().route(message=message, route_context=None)

    assert route.intent == expected_intent


def test_router_low_confidence_clarifies():
    route = DeterministicAgentRouter().route(message="ok", route_context=None)

    assert route.intent == "clarify"
    assert route.confidence < 0.65
```

- [ ] **Step 2: Write slot ambiguity tests**

Create `tests/services/test_agent_slot_resolver.py`:

```python
from types import SimpleNamespace

import pytest

from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_slot_resolver import AgentSlotResolver


@pytest.mark.asyncio
async def test_slot_resolver_marks_multiple_attention_units_ambiguous():
    async def search(request, allowed_course_ids):
        return SimpleNamespace(
            results=[
                SimpleNamespace(canonical_unit_id="attention", unit_name="Attention", course_id="CS224n", score=3),
                SimpleNamespace(canonical_unit_id="self-attention", unit_name="Self-attention", course_id="CS224n", score=3),
            ]
        )

    resolver = AgentSlotResolver(search_service=SimpleNamespace(search=search))
    slots = await resolver.canonicalize(
        raw_slots=AgentSlots(raw_topic="attention"),
        intent="assess_knowledge",
        allowed_course_ids=["CS224n"],
    )

    assert slots.canonical_unit_ids == []
    assert len(slots.ambiguity_options) == 2
```

- [ ] **Step 3: Write policy and composer tests**

Create `tests/services/test_agent_policy_service.py`:

```python
from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_policy_service import AgentPolicyService


def test_policy_denies_course_scope_mismatch():
    decision = AgentPolicyService().evaluate(
        intent="find_content",
        slots=AgentSlots(course_ids=["CS999"]),
        allowed_course_ids=["CS231n"],
    )

    assert decision.allow is False
    assert decision.codes == ["COURSE_SCOPE_MISMATCH"]
```

Create `tests/services/test_agent_response_composer.py`:

```python
from src.services.agent_graph_contracts import ToolResult
from src.services.agent_response_composer import AgentResponseComposer


def test_composer_does_not_ground_without_required_evidence():
    response = AgentResponseComposer().compose(
        conversation_id="conv-1",
        message_id="msg-1",
        result=ToolResult(
            kind="explain_concept",
            answer_markdown="Attention is covered in the course.",
            requires_evidence=True,
            citations=[],
        ),
    )

    assert response.answer.confidence == "no_source"
    assert response.fallback is not None
```

- [ ] **Step 4: Run failing service tests**

Run:

```bash
pytest tests/services/test_agent_graph_router.py tests/services/test_agent_slot_resolver.py tests/services/test_agent_policy_service.py tests/services/test_agent_response_composer.py -q
```

Expected: missing modules.

- [ ] **Step 5: Implement router, resolver, policy, and composer**

Create `src/services/agent_graph_router.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

from src.schemas.agent import AgentIntent, RouteContext
from src.services.agent_graph_contracts import AgentSlots


class AgentRoute(BaseModel):
    intent: AgentIntent
    confidence: float
    extracted_slots: AgentSlots
    rationale: str


class DeterministicAgentRouter:
    """Test/integration seam only. Do not use as the production router."""

    def route(self, message: str, route_context: RouteContext | None) -> AgentRoute:
        text = message.lower().strip()
        if text in {"ok", "yes", "approve"}:
            return AgentRoute(intent="clarify", confidence=0.25, extracted_slots=AgentSlots(), rationale="confirmation_without_pending_action")
        if "skip connection" in text:
            return AgentRoute(intent="explain_concept", confidence=0.9, extracted_slots=AgentSlots(raw_topic="skip connection"), rationale="concept_phrase")
        if "quiz eligibility" in text:
            return AgentRoute(intent="general_course_question", confidence=0.85, extracted_slots=AgentSlots(raw_topic="quiz eligibility"), rationale="assessment_policy_concept")
        if "quiz" in text or "test me" in text or "kiểm tra" in text:
            topic = text.replace("cho tôi quiz về", "").replace("quiz me on", "").replace("test me on", "").strip()
            return AgentRoute(intent="assess_knowledge", confidence=0.86, extracted_slots=AgentSlots(raw_topic=topic or None), rationale="assessment_request")
        if "explain" in text or "giải thích" in text:
            return AgentRoute(intent="explain_concept", confidence=0.82, extracted_slots=AgentSlots(raw_topic=text), rationale="concept_explanation")
        return AgentRoute(intent="general_course_question", confidence=0.7, extracted_slots=AgentSlots(raw_topic=text), rationale="default_general")
```

Create `src/services/agent_slot_resolver.py`:

```python
from __future__ import annotations

from src.schemas.agent import UnitSearchRequest
from src.services.agent_graph_contracts import AgentSlots


class AgentSlotResolver:
    def __init__(self, search_service):
        self.search_service = search_service

    async def canonicalize(self, raw_slots: AgentSlots, intent: str, allowed_course_ids: list[str]) -> AgentSlots:
        if not raw_slots.raw_topic:
            return raw_slots
        search = await self.search_service.search(
            UnitSearchRequest(query=raw_slots.raw_topic, scope="current_path", limit=5, intent=intent),
            allowed_course_ids=allowed_course_ids,
        )
        scored = [result for result in search.results if getattr(result, "score", 0) > 0]
        if len(scored) > 1 and intent == "assess_knowledge":
            return raw_slots.model_copy(
                update={
                    "ambiguity_options": [
                        {"canonical_unit_id": result.canonical_unit_id, "unit_name": result.unit_name}
                        for result in scored
                    ],
                    "canonical_unit_ids": [],
                }
            )
        return raw_slots.model_copy(
            update={
                "canonical_unit_ids": [result.canonical_unit_id for result in scored[:3]],
                "course_ids": sorted({result.course_id for result in scored[:3]}),
            }
        )
```

Create `src/services/agent_policy_service.py`:

```python
from __future__ import annotations

from src.services.agent_graph_contracts import AgentSlots, PolicyDecision


class AgentPolicyService:
    def evaluate(self, intent: str, slots: AgentSlots, allowed_course_ids: list[str]) -> PolicyDecision:
        out_of_scope = [course_id for course_id in slots.course_ids if course_id not in allowed_course_ids]
        if out_of_scope:
            return PolicyDecision(
                allow=False,
                codes=["COURSE_SCOPE_MISMATCH"],
                user_safe_message="I cannot access that course in your current scope.",
                audit_context={"requestedCourseIds": out_of_scope},
            )
        return PolicyDecision(allow=True, codes=[], user_safe_message=None, audit_context=None)
```

Create `src/services/agent_response_composer.py`:

```python
from __future__ import annotations

from src.schemas.agent import AgentAnswer, AgentChatResponse, AgentFallback
from src.services.agent_graph_contracts import ToolResult


class AgentResponseComposer:
    def compose(self, conversation_id: str, message_id: str, result: ToolResult) -> AgentChatResponse:
        if result.requires_evidence and not result.citations:
            return AgentChatResponse(
                conversation_id=conversation_id,
                message_id=message_id,
                answer=AgentAnswer(
                    markdown="I could not find grounded evidence for that request. Please narrow the topic or choose a specific unit.",
                    confidence="no_source",
                ),
                fallback=AgentFallback(
                    reason="no_retrieval_result",
                    message="No grounded evidence was available for this answer.",
                ),
            )
        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=message_id,
            answer=AgentAnswer(
                markdown=result.answer_markdown or "I need one more detail before I can answer reliably.",
                confidence="grounded" if result.citations else "partial",
            ),
            citations=result.citations,
            actions=result.actions,
            warning=result.warning,
            fallback=result.fallback,
        )
```

- [ ] **Step 6: Run service tests**

Run:

```bash
pytest tests/services/test_agent_graph_router.py tests/services/test_agent_slot_resolver.py tests/services/test_agent_policy_service.py tests/services/test_agent_response_composer.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/services/agent_graph_router.py src/services/agent_slot_resolver.py src/services/agent_policy_service.py src/services/agent_response_composer.py tests/services/test_agent_graph_router.py tests/services/test_agent_slot_resolver.py tests/services/test_agent_policy_service.py tests/services/test_agent_response_composer.py
git commit -m "feat: add agent graph routing primitives"
```

---

### Task 4: Production Structured Router `[partial]`

**Files:**
- Create: `src/services/agent_structured_router.py`
- Test: `tests/services/test_agent_structured_router.py`

- [ ] **Step 1: Write structured router tests with a fake structured-output model**

Create `tests/services/test_agent_structured_router.py`:

```python
from src.services.agent_structured_router import StructuredAgentRouter


class FakeStructuredModel:
    def __init__(self, payload):
        self.payload = payload
        self.schema = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        return self.schema(**self.payload)


def test_structured_router_returns_explicit_path_route():
    model = FakeStructuredModel(
        {
            "intent": "find_content",
            "confidence": 0.91,
            "raw_topic": "attention mask",
            "target_path": "nlp",
            "rationale": "User explicitly asked for NLP content.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="Trong path NLP có bài nào về attention mask không?",
        route_context=None,
    )

    assert route.intent == "find_content"
    assert route.extracted_slots.raw_topic == "attention mask"
    assert route.extracted_slots.requested_path_id == "nlp"
    assert route.extracted_slots.search_scope == "explicit_path"


def test_structured_router_low_confidence_clarifies():
    model = FakeStructuredModel(
        {
            "intent": "request_replan",
            "confidence": 0.4,
            "raw_topic": None,
            "target_path": None,
            "rationale": "Ambiguous short confirmation.",
        }
    )

    route = StructuredAgentRouter(model=model).route(message="ok", route_context=None)

    assert route.intent == "clarify"
    assert route.confidence == 0.4


def test_structured_router_path_switch_intent():
    model = FakeStructuredModel(
        {
            "intent": "request_path_switch",
            "confidence": 0.94,
            "raw_topic": None,
            "target_path": "nlp",
            "rationale": "User asked to switch to NLP.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="Tôi muốn chuyển từ CV sang NLP.",
        route_context=None,
    )

    assert route.intent == "request_path_switch"
    assert route.extracted_slots.target_path == "nlp"
```

- [ ] **Step 2: Run failing structured router tests**

Run:

```bash
pytest tests/services/test_agent_structured_router.py -q
```

Expected: missing `agent_structured_router` module.

- [ ] **Step 3: Implement production structured router**

Create `src/services/agent_structured_router.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.agent import AgentIntent, RouteContext
from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_graph_router import AgentRoute


class StructuredRouteOutput(BaseModel):
    intent: AgentIntent
    confidence: float = Field(ge=0.0, le=1.0)
    raw_topic: str | None = None
    target_path: Literal["computer_vision", "nlp"] | None = None
    rationale: str


class StructuredAgentRouter:
    """Production router backed by structured model output."""

    def __init__(self, model, confidence_threshold: float = 0.65):
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.structured_model = model.with_structured_output(StructuredRouteOutput)

    def route(self, message: str, route_context: RouteContext | None) -> AgentRoute:
        result = self.structured_model.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "Classify the user's /agent request. Do not route by raw keywords. "
                        "Distinguish concepts like skip connection from path/replan actions, "
                        "and quiz eligibility questions from assessment creation requests. "
                        "Use request_path_switch only when the user asks to change their active learning path."
                    ),
                },
                {"role": "user", "content": message},
            ]
        )
        intent: AgentIntent = result.intent
        if result.confidence < self.confidence_threshold:
            intent = "clarify"
        search_scope = "explicit_path" if result.target_path else "current_path"
        return AgentRoute(
            intent=intent,
            confidence=result.confidence,
            extracted_slots=AgentSlots(
                raw_topic=result.raw_topic,
                target_path=result.target_path,
                requested_path_id=result.target_path,
                resolved_search_path_ids=[result.target_path] if result.target_path else [],
                search_scope=search_scope,
            ),
            rationale=result.rationale,
        )
```

- [ ] **Step 4: Mark deterministic router as test/bootstrap-only in the router module**

In `src/services/agent_graph_router.py`, keep the deterministic router docstring explicit:

```python
class DeterministicAgentRouter:
    """Test/integration seam only. Do not use as the production router."""
```

Production route wiring is handled in the dedicated production wiring task after the graph service skeleton exists.

- [ ] **Step 5: Run structured router tests**

Run:

```bash
pytest tests/services/test_agent_structured_router.py tests/services/test_agent_graph_router.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/services/agent_structured_router.py src/services/agent_graph_router.py tests/services/test_agent_structured_router.py
git commit -m "feat: add structured agent intent router"
```

---

### Task 5: Minimal Bootstrap LangGraph Service Skeleton And Tool Nodes `[bootstrap-only]`

This is a minimal bootstrap skeleton to prove graph invocation and typed tool-node flow. It is not spec-complete: `hydrate_min_context`, `load_intent_scoped_context`, `compose_response_ref`, durable pending actions, real `interrupt()`/resume, and policy-safe denial responses are completed in later tasks.

**Files:**
- Create: `src/services/agent_tool_nodes.py`
- Create: `src/services/agent_graph_service.py`
- Test: `tests/services/test_agent_graph_service.py`

- [ ] **Step 1: Write graph service tests for clarify, grounded search, and ambiguity**

Create `tests/services/test_agent_graph_service.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.schemas.agent import AgentChatRequest, RetrievalTrace, UnitSearchResponse
from src.services.agent_graph_service import AgentGraphService

pytestmark = pytest.mark.asyncio


async def test_graph_clarifies_low_confidence_confirmation_without_pending_action():
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="ok", incomingMessageId="msg-1"),
        conversation_id=str(uuid4()),
        thread_id="thread-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "partial"
    assert response.warning is not None
    assert response.warning.type == "ambiguous_target"


async def test_graph_returns_grounded_find_content_from_search():
    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                {
                    "canonical_unit_id": "unit-rf",
                    "course_id": "CS231n",
                    "unit_name": "Receptive fields",
                    "summary": "Effective receptive field is covered here.",
                    "score": 3,
                }
            ],
            trace=RetrievalTrace(trace_id="trace-1", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Where is receptive field taught?", incomingMessageId="msg-2"),
        conversation_id=str(uuid4()),
        thread_id="thread-2",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "grounded"
    assert response.citations[0].canonical_unit_id == "unit-rf"
```

- [ ] **Step 2: Run failing graph service tests**

Run:

```bash
pytest tests/services/test_agent_graph_service.py -q
```

Expected: missing graph service/tool node modules.

- [ ] **Step 3: Implement tool nodes**

Create `src/services/agent_tool_nodes.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.schemas.agent import AgentCitation, AgentWarning, UnitSearchRequest
from src.services.agent_graph_contracts import AgentSlots, ToolResult


class AgentToolNodes:
    def __init__(self, search_service, requirement_service):
        self.search_service = search_service
        self.requirement_service = requirement_service

    async def clarify(self, message: str) -> ToolResult:
        return ToolResult(
            kind="clarification",
            answer_markdown="I need one more detail before I can do that safely.",
            warning=AgentWarning(type="ambiguous_target", message="The request is ambiguous in the current context."),
        )

    async def find_content(self, message: str, intent: str, slots: AgentSlots, allowed_course_ids: list[str]) -> ToolResult:
        search = await self.search_service.search(
            UnitSearchRequest(query=slots.raw_topic or message, scope="current_path", limit=5, intent=intent),
            allowed_course_ids=allowed_course_ids,
        )
        results = [result for result in search.results if result.score > 0][:3]
        citations = [
            AgentCitation(
                canonical_unit_id=result.canonical_unit_id,
                course_id=result.course_id,
                lecture_id=getattr(result, "lecture_id", None),
                lecture_title=getattr(result, "lecture_title", None),
                unit_name=result.unit_name,
                learn_href=getattr(result, "learn_href", None),
                quote=getattr(result, "summary", None),
                source="summary",
            )
            for result in results
        ]
        return ToolResult(
            kind="find_content",
            answer_markdown="I found relevant learning units." if citations else None,
            citations=citations,
            requires_evidence=True,
        )

    async def general_question(self, message: str, slots: AgentSlots, allowed_course_ids: list[str]) -> ToolResult:
        return await self.find_content(message, "general_course_question", slots, allowed_course_ids)
```

- [ ] **Step 4: Implement graph service skeleton**

Create `src/services/agent_graph_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from src.schemas.agent import AgentChatRequest, AgentChatResponse
from src.services.agent_graph_contracts import AgentCheckpointState, PolicyDecision
from src.services.agent_graph_router import DeterministicAgentRouter
from src.services.agent_policy_service import AgentPolicyService
from src.services.agent_response_composer import AgentResponseComposer
from src.services.agent_slot_resolver import AgentSlotResolver
from src.services.agent_tool_nodes import AgentToolNodes


class AgentGraphService:
    def __init__(self, search_service, requirement_service, router=None):
        self.search_service = search_service
        self.requirement_service = requirement_service
        self.router = router or DeterministicAgentRouter()
        self.policy = AgentPolicyService()
        self.composer = AgentResponseComposer()
        self.tools = AgentToolNodes(search_service, requirement_service)

    def _build_graph(self):
        graph = StateGraph(dict)
        graph.add_node("route_intent", self._route_intent)
        graph.add_node("canonicalize_slots", self._canonicalize_slots)
        graph.add_node("policy_guard", self._policy_guard)
        graph.add_node("dispatch", self._dispatch)
        graph.add_edge(START, "route_intent")
        graph.add_edge("route_intent", "canonicalize_slots")
        graph.add_edge("canonicalize_slots", "policy_guard")
        graph.add_edge("policy_guard", "dispatch")
        graph.add_edge("dispatch", END)
        return graph.compile()

    async def chat(
        self,
        request: AgentChatRequest,
        conversation_id: str,
        thread_id: str,
        user_id: str,
        allowed_course_ids: list[str],
    ) -> AgentChatResponse:
        state = AgentCheckpointState(
            thread_id=thread_id,
            conversation_id=conversation_id,
            user_id=user_id,
            incoming_message_id=request.incoming_message_id,
            route_context=request.route_context,
            trace_id=str(uuid4()),
        ).model_dump()
        state["message"] = request.message
        state["allowed_course_ids"] = allowed_course_ids
        graph = self._build_graph()
        final_state = await graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})
        return self.composer.compose(
            conversation_id=conversation_id,
            message_id=str(uuid4()),
            result=final_state["tool_result"],
        )

    async def _route_intent(self, state: dict) -> dict:
        route = self.router.route(message=state["message"], route_context=state.get("route_context"))
        return {
            "intent": route.intent,
            "intent_confidence": route.confidence,
            "slots": route.extracted_slots,
        }

    async def _canonicalize_slots(self, state: dict) -> dict:
        if state["intent_confidence"] < 0.65:
            return state
        resolver = AgentSlotResolver(self.search_service)
        slots = await resolver.canonicalize(
            raw_slots=state["slots"],
            intent=state["intent"],
            allowed_course_ids=state["allowed_course_ids"],
        )
        return {"slots": slots}

    async def _policy_guard(self, state: dict) -> dict:
        decision = self.policy.evaluate(
            intent=state["intent"],
            slots=state["slots"],
            allowed_course_ids=state["allowed_course_ids"],
        )
        return {"policy": decision}

    async def _dispatch(self, state: dict) -> dict:
        policy: PolicyDecision = state["policy"]
        if not policy.allow:
            result = await self.tools.clarify(state["message"])
            return {"tool_result": result}
        if state["intent_confidence"] < 0.65 or state["slots"].ambiguity_options:
            result = await self.tools.clarify(state["message"])
            return {"tool_result": result}
        if state["intent"] in {"find_content", "explain_concept", "general_course_question"}:
            result = await self.tools.find_content(
                state["message"],
                state["intent"],
                state["slots"],
                state["allowed_course_ids"],
            )
            return {"tool_result": result}
        result = await self.tools.clarify(state["message"])
        return {"tool_result": result}
```

- [ ] **Step 5: Run graph service tests**

Run:

```bash
pytest tests/services/test_agent_graph_service.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/services/agent_tool_nodes.py src/services/agent_graph_service.py tests/services/test_agent_graph_service.py
git commit -m "feat: add agent LangGraph service skeleton"
```

---

### Task 6: Production Router Wiring And Fail-Safe `[done]`

This task is the production cutover from the deterministic seam to the structured-output router. The deterministic router remains importable for tests/bootstrap only. Production `/api/agent/chat` must not fall back to keyword routing when the model/provider is unavailable.

**Files:**
- Create: `src/services/agent_router_factory.py`
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/routers/agent.py`
- Test: `tests/services/test_agent_router_factory.py`
- Test: `tests/contract/test_agent_graph_routes.py`

- [ ] **Step 1: Write router factory tests**

Create `tests/services/test_agent_router_factory.py`:

```python
import pytest

from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_router_factory import build_production_agent_router
from src.services.agent_structured_router import StructuredAgentRouter


class Settings:
    model_provider = "openai"
    fast_model = "gpt-5-mini"


class FakeChatModel:
    def with_structured_output(self, schema):
        return self


def test_production_router_factory_builds_structured_router():
    router = build_production_agent_router(
        settings=Settings(),
        init_chat_model=lambda **kwargs: FakeChatModel(),
    )

    assert isinstance(router, StructuredAgentRouter)


def test_production_router_factory_fails_safe_without_provider():
    class MissingSettings:
        model_provider = ""
        fast_model = "gpt-5-mini"

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(
            settings=MissingSettings(),
            init_chat_model=lambda **kwargs: FakeChatModel(),
        )


def test_production_router_factory_does_not_return_deterministic_router_on_model_error():
    def fail_model(**kwargs):
        raise RuntimeError("provider unavailable")

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(settings=Settings(), init_chat_model=fail_model)
```

- [ ] **Step 2: Run failing router factory tests**

Run:

```bash
pytest tests/services/test_agent_router_factory.py -q
```

Expected: missing `agent_router_factory` and `AgentRouterUnavailableError`.

- [ ] **Step 3: Add fail-safe error contract**

In `src/services/agent_graph_contracts.py`, add:

```python
from src.schemas.agent import AgentAnswer, AgentChatResponse, AgentWarning


class AgentRouterUnavailableError(RuntimeError):
    def to_response(self) -> AgentChatResponse:
        return AgentChatResponse(
            conversation_id="",
            message_id="",
            answer=AgentAnswer(
                markdown="I cannot classify this request right now. Please try again shortly.",
                confidence="fallback",
            ),
            warning=AgentWarning(
                type="agent_unavailable",
                message="The production router model is unavailable.",
            ),
        )
```

- [ ] **Step 4: Implement production router factory**

Create `src/services/agent_router_factory.py`:

```python
from __future__ import annotations

from langchain.chat_models import init_chat_model

from src.config import settings
from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_structured_router import StructuredAgentRouter
from src.services.chat_model_factory import build_chat_model_kwargs


def build_production_agent_router(
    *,
    settings=settings,
    init_chat_model=init_chat_model,
) -> StructuredAgentRouter:
    provider = str(settings.model_provider or "").strip()
    model = str(settings.fast_model or "").strip()
    if not provider or not model:
        raise AgentRouterUnavailableError("Agent router model/provider is not configured.")
    try:
        chat_model = init_chat_model(
            **build_chat_model_kwargs(
                model=model,
                model_provider=provider,
                temperature=0,
            )
        )
    except Exception as exc:
        raise AgentRouterUnavailableError("Agent router model/provider is unavailable.") from exc
    return StructuredAgentRouter(model=chat_model)
```

This factory must never import or instantiate `DeterministicAgentRouter`.

- [ ] **Step 5: Require explicit router injection in production graph service**

In `src/services/agent_graph_service.py`, keep test ergonomics explicit:

```python
class AgentGraphService:
    def __init__(self, search_service, requirement_service, router):
        self.search_service = search_service
        self.requirement_service = requirement_service
        self.router = router
```

Update existing unit tests to pass `router=DeterministicAgentRouter()` or a fake router explicitly.

- [ ] **Step 6: Wire `/api/agent/chat` to production router factory**

In `src/routers/agent.py`, add:

```python
from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_router_factory import build_production_agent_router
```

Instantiate:

```python
router = build_production_agent_router()
response = await AgentGraphService(search, requirements, router=router).chat(
    request=body,
    conversation_id=str(conversation_id),
    thread_id=conversation.thread_id,
    user_id=str(user.id),
    allowed_course_ids=context.allowed_course_ids,
)
```

Handle fail-safe without deterministic fallback:

```python
except AgentRouterUnavailableError as exc:
    fallback = exc.to_response()
    fallback.conversation_id = str(conversation_id)
    fallback.message_id = str(uuid4())
    return fallback
```

- [ ] **Step 7: Run router wiring tests**

Run:

```bash
pytest tests/services/test_agent_router_factory.py tests/services/test_agent_graph_service.py tests/contract/test_agent_graph_routes.py -q
```

Expected: pass, with production route tests asserting `build_production_agent_router` is called and no deterministic router fallback is used.

- [ ] **Step 8: Commit**

```bash
git add src/services/agent_router_factory.py src/services/agent_graph_contracts.py src/services/agent_graph_service.py src/routers/agent.py tests/services/test_agent_router_factory.py tests/services/test_agent_graph_service.py tests/contract/test_agent_graph_routes.py
git commit -m "feat: wire production structured agent router"
```

---

### Task 7: Search Scope Escalation `[done]`

**Files:**
- Create: `src/services/agent_search_scope_service.py`
- Modify: `src/services/agent_graph_contracts.py`
- Modify: `src/services/agent_slot_resolver.py`
- Modify: `src/services/agent_tool_nodes.py`
- Test: `tests/services/test_agent_search_scope_service.py`
- Test: `tests/services/test_agent_graph_service.py`

- [ ] **Step 1: Write search scope escalation tests**

Create `tests/services/test_agent_search_scope_service.py`:

```python
from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_search_scope_service import AgentSearchScopeService


def test_default_scope_starts_current_path():
    slots = AgentSearchScopeService().resolve_initial_scope(
        slots=AgentSlots(raw_topic="attention mask"),
        current_path_ids=["computer_vision"],
    )

    assert slots.search_scope == "current_path"
    assert slots.resolved_search_path_ids == ["computer_vision"]


def test_explicit_path_uses_requested_scope_directly():
    slots = AgentSearchScopeService().resolve_initial_scope(
        slots=AgentSlots(raw_topic="attention mask", requested_path_id="nlp"),
        current_path_ids=["computer_vision"],
    )

    assert slots.search_scope == "explicit_path"
    assert slots.resolved_search_path_ids == ["nlp"]


def test_no_current_path_result_offers_expansion():
    slots = AgentSearchScopeService().offer_expansion_if_no_results(
        slots=AgentSlots(raw_topic="attention mask", search_scope="current_path"),
        current_path_result_count=0,
        allowed_path_ids=["computer_vision", "nlp"],
    )

    assert slots.scope_expansion_offered is True
    assert slots.search_scope == "current_path"


def test_approved_expansion_uses_allowed_paths():
    slots = AgentSearchScopeService().approve_expansion(
        slots=AgentSlots(raw_topic="attention mask", scope_expansion_offered=True),
        allowed_path_ids=["computer_vision", "nlp"],
    )

    assert slots.scope_expansion_approved is True
    assert slots.search_scope == "expanded_paths"
    assert slots.resolved_search_path_ids == ["computer_vision", "nlp"]
```

- [ ] **Step 2: Run failing search scope tests**

Run:

```bash
pytest tests/services/test_agent_search_scope_service.py -q
```

Expected: missing search scope service.

- [ ] **Step 3: Implement search scope service**

Create `src/services/agent_search_scope_service.py`:

```python
from __future__ import annotations

from src.services.agent_graph_contracts import AgentSlots


class AgentSearchScopeService:
    def resolve_initial_scope(self, slots: AgentSlots, current_path_ids: list[str]) -> AgentSlots:
        if slots.requested_path_id:
            return slots.model_copy(
                update={
                    "search_scope": "explicit_path",
                    "resolved_search_path_ids": [slots.requested_path_id],
                }
            )
        return slots.model_copy(
            update={
                "search_scope": "current_path",
                "resolved_search_path_ids": current_path_ids,
            }
        )

    def offer_expansion_if_no_results(
        self,
        slots: AgentSlots,
        current_path_result_count: int,
        allowed_path_ids: list[str],
    ) -> AgentSlots:
        if slots.search_scope != "current_path" or current_path_result_count > 0:
            return slots
        if len(allowed_path_ids) <= len(slots.resolved_search_path_ids):
            return slots
        return slots.model_copy(update={"scope_expansion_offered": True})

    def approve_expansion(self, slots: AgentSlots, allowed_path_ids: list[str]) -> AgentSlots:
        return slots.model_copy(
            update={
                "scope_expansion_approved": True,
                "search_scope": "expanded_paths",
                "resolved_search_path_ids": allowed_path_ids,
            }
        )
```

- [ ] **Step 4: Add graph behavior test for no-result current path expansion clarification**

Append to `tests/services/test_agent_graph_service.py`:

```python
async def test_graph_offers_scope_expansion_when_current_path_has_no_result():
    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-empty", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="attention mask ở đâu?", incomingMessageId="msg-scope-1"),
        conversation_id=str(uuid4()),
        thread_id="thread-scope-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n", "CS224n"],
    )

    assert response.answer.confidence == "no_source"
    assert response.warning is not None
    assert response.warning.type == "ambiguous_target"
```

- [ ] **Step 5: Wire initial scope resolution into slot resolver/tool node**

In `src/services/agent_slot_resolver.py`, apply `AgentSearchScopeService.resolve_initial_scope` before search. For V1 path ids map directly to path keys, and course id filtering still uses `allowed_course_ids`; later path-to-course mapping can be added in `AgentContextResolver`.

In `src/services/agent_tool_nodes.py`, if `find_content` returns no citations and `slots.search_scope == "current_path"`, return a clarification/no-source response that asks for approval before expanded search:

```python
from src.schemas.agent import AgentFallback, AgentWarning

def build_current_scope_no_source_result(slots: AgentSlots, citations: list[AgentCitation]) -> ToolResult | None:
    if citations or slots.search_scope != "current_path":
        return None

    return ToolResult(
        kind="clarification",
        answer_markdown="I could not find this in your current path. Do you want me to expand the search to other allowed paths?",
        warning=AgentWarning(type="ambiguous_target", message="No result was found in the current path; expansion requires confirmation."),
        fallback=AgentFallback(reason="no_retrieval_result", message="Current-path search returned no grounded result."),
    )
```

- [ ] **Step 6: Run search scope tests**

Run:

```bash
pytest tests/services/test_agent_search_scope_service.py tests/services/test_agent_graph_service.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/services/agent_search_scope_service.py src/services/agent_graph_contracts.py src/services/agent_slot_resolver.py src/services/agent_tool_nodes.py tests/services/test_agent_search_scope_service.py tests/services/test_agent_graph_service.py
git commit -m "feat: add agent search scope escalation"
```

---

### Task 8: Scope Expansion Confirmation And Expanded Retrieval `[partial]`

This task completes the scope escalation loop. A current-path no-result offer must create thread-bound clarification state; a later "ok, search elsewhere" turn must approve expansion, rerun retrieval over expanded allowed paths, and disclose which path produced the answer.

**Files:**
- Modify: `src/services/agent_graph_contracts.py`
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/services/agent_search_scope_service.py`
- Modify: `src/services/agent_tool_nodes.py`
- Test: `tests/services/test_agent_graph_service.py`
- Test: `tests/services/test_agent_search_scope_service.py`

- [ ] **Step 1: Add pending clarification contract tests**

Append to `tests/services/test_agent_graph_contracts.py`:

```python
from src.services.agent_graph_contracts import PendingClarification


def test_pending_clarification_tracks_scope_expansion():
    pending = PendingClarification(
        clarification_id="clar-scope-1",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={
            "original_message": "attention mask ở đâu?",
            "allowed_path_ids": ["computer_vision", "nlp"],
            "current_path_ids": ["computer_vision"],
        },
    )

    assert pending.type == "search_scope_expansion"
    assert pending.payload["allowed_path_ids"] == ["computer_vision", "nlp"]
```

- [ ] **Step 2: Add expanded retrieval graph test**

Append to `tests/services/test_agent_graph_service.py`:

```python
async def test_scope_expansion_confirmation_reruns_search_and_discloses_path():
    calls = []

    async def search(request, allowed_course_ids):
        calls.append(list(allowed_course_ids))
        if len(calls) == 1:
            return UnitSearchResponse(
                results=[],
                trace=RetrievalTrace(trace_id="trace-current", ranking_version="unit_search_v1"),
            )
        return UnitSearchResponse(
            results=[
                {
                    "canonical_unit_id": "unit-attention-mask",
                    "course_id": "CS224n",
                    "unit_name": "Attention Masks",
                    "score": 3,
                    "summary": "Attention mask content.",
                    "path_id": "nlp",
                }
            ],
            trace=RetrievalTrace(trace_id="trace-expanded", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
    )
    conversation_id = str(uuid4())

    first = await service.chat(
        request=AgentChatRequest(message="attention mask ở đâu?", incomingMessageId="msg-scope-offer"),
        conversation_id=conversation_id,
        thread_id="thread-scope-expand",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n", "CS224n"],
    )
    second = await service.chat(
        request=AgentChatRequest(message="ok, tìm path khác đi", incomingMessageId="msg-scope-approve"),
        conversation_id=conversation_id,
        thread_id="thread-scope-expand",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n", "CS224n"],
    )

    assert first.warning.type == "ambiguous_target"
    assert second.answer.confidence in {"grounded", "partial"}
    assert "NLP" in second.answer.markdown or "CS224n" in second.answer.markdown
    assert calls == [["CS231n"], ["CS231n", "CS224n"]]
```

- [ ] **Step 3: Add pending clarification contract**

In `src/services/agent_graph_contracts.py`, add:

```python
class PendingClarification(BaseModel):
    clarification_id: str
    type: Literal["search_scope_expansion", "slot_disambiguation", "intent_clarification"]
    status: Literal["awaiting_response", "resolved", "cancelled", "expired"]
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None
```

Add `pending_clarification: PendingClarification | None = None` to `AgentCheckpointState`.

- [ ] **Step 4: Implement approval detection without keyword routing override**

In `src/services/agent_search_scope_service.py`, add:

```python
APPROVAL_PHRASES = {"ok", "yes", "approve", "được", "tìm path khác đi", "mở rộng tìm kiếm"}


class AgentSearchScopeService:
    def is_scope_expansion_approval(self, message: str, pending: PendingClarification | None) -> bool:
        if pending is None or pending.type != "search_scope_expansion":
            return False
        normalized = message.lower().strip()
        return normalized in APPROVAL_PHRASES or "mở rộng" in normalized or "path khác" in normalized
```

This approval detector may only resolve an already-pending scope expansion clarification. It must not classify fresh user intent.

- [ ] **Step 5: Wire graph continuation**

In `AgentGraphService._route_intent`, before calling the main router, check for a pending scope expansion clarification:

```python
pending = state.get("pending_clarification")
scope_service = AgentSearchScopeService()
if scope_service.is_scope_expansion_approval(state["message"], pending):
    slots = AgentSlots(
        raw_topic=pending.payload["original_message"],
        search_scope="expanded_paths",
        scope_expansion_approved=True,
        resolved_search_path_ids=pending.payload["allowed_path_ids"],
    )
    return {
        "intent": "find_content",
        "intent_confidence": 1.0,
        "slots": slots,
        "pending_clarification": None,
    }
```

In the no-result current-path branch, set:

```python
PendingClarification(
    clarification_id=f"clar_{uuid4()}",
    type="search_scope_expansion",
    status="awaiting_response",
    payload={
        "original_message": state["message"],
        "allowed_path_ids": ["computer_vision", "nlp"],
        "current_path_ids": state["slots"].resolved_search_path_ids,
    },
)
```

- [ ] **Step 6: Run scope expansion continuation tests**

Run:

```bash
pytest tests/services/test_agent_search_scope_service.py tests/services/test_agent_graph_service.py tests/services/test_agent_graph_contracts.py -q
```

Expected: pass and expanded retrieval discloses the non-current path/source.

- [ ] **Step 7: Commit**

```bash
git add src/services/agent_graph_contracts.py src/services/agent_graph_service.py src/services/agent_search_scope_service.py src/services/agent_tool_nodes.py tests/services/test_agent_graph_service.py tests/services/test_agent_search_scope_service.py tests/services/test_agent_graph_contracts.py
git commit -m "feat: add agent scope expansion continuation"
```

---

### Task 9: Router Integration, Dedupe, Locking, And 409 Responses `[done]`

This task routes traffic through the graph service and standardizes `409 in_progress`. It is not the full replay-safe persistence boundary. Until the following tasks move message persistence, response refs, and pending actions fully inside `AgentGraphService`, do not use this task as the production readiness checkpoint for dedupe/replay.

**Files:**
- Create: `src/services/agent_lock_service.py`
- Modify: `src/routers/agent.py`
- Modify: `src/repositories/agent_conversation_repo.py`
- Modify: `src/repositories/agent_graph_repo.py`
- Test: `tests/contract/test_agent_graph_routes.py`

- [ ] **Step 1: Write contract tests for graph chat route and in-progress conflict**

Create `tests/contract/test_agent_graph_routes.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.schemas.agent import AgentAnswer, AgentChatResponse
from src.services.agent_graph_contracts import AgentInProgressError

pytestmark = pytest.mark.anyio


async def _client_for_user(user_id):
    async def override_user():
        return SimpleNamespace(id=user_id)

    async def override_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_async_db] = override_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_agent_chat_returns_graph_response():
    user_id = uuid4()
    graph_response = AgentChatResponse(
        conversation_id=str(uuid4()),
        message_id=str(uuid4()),
        answer=AgentAnswer(markdown="Graph answer", confidence="partial"),
    )

    with (
        patch("src.routers.agent._agent_context_for_user", new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"], selected_path_course_ids=["CS231n"]))),
        patch("src.routers.agent.AgentGraphService") as service_cls,
    ):
        service_cls.return_value.chat = AsyncMock(return_value=graph_response)
        client = await _client_for_user(user_id)
        try:
            response = await client.post("/api/agent/chat", json={"message": "ok", "incomingMessageId": "msg-1"})
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"]["markdown"] == "Graph answer"


async def test_agent_chat_returns_409_in_progress_payload():
    user_id = uuid4()

    with (
        patch("src.routers.agent._agent_context_for_user", new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"], selected_path_course_ids=["CS231n"]))),
        patch("src.routers.agent.AgentGraphService") as service_cls,
    ):
        service_cls.return_value.chat = AsyncMock(side_effect=AgentInProgressError("conv-1", "thread-1", "run-1", 1000))
        client = await _client_for_user(user_id)
        try:
            response = await client.post("/api/agent/chat", json={"message": "ok", "incomingMessageId": "msg-2"})
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "status": "in_progress",
        "conversationId": "conv-1",
        "threadId": "thread-1",
        "graphRunId": "run-1",
        "retryAfterMs": 1000,
    }
```

- [ ] **Step 2: Run failing contract tests**

Run:

```bash
pytest tests/contract/test_agent_graph_routes.py -q
```

Expected: route still calls `AgentChatService` and does not catch `AgentInProgressError`.

- [ ] **Step 3: Implement advisory lock helper**

Create `src/services/agent_lock_service.py`:

```python
from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.agent_graph_contracts import AgentInProgressError


def advisory_lock_key(thread_id: str) -> int:
    digest = hashlib.sha256(thread_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


class AgentThreadLock:
    def __init__(self, session: AsyncSession):
        self.session = session

    @asynccontextmanager
    async def acquire(self, *, conversation_id: str, thread_id: str, graph_run_id: str):
        key = advisory_lock_key(thread_id)
        result = await self.session.execute(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key})
        locked = bool(result.scalar())
        if not locked:
            raise AgentInProgressError(conversation_id, thread_id, graph_run_id, retry_after_ms=1000)
        yield
```

- [ ] **Step 4: Wire router chat to `AgentGraphService` and 409 handling**

Modify imports in `src/routers/agent.py`:

```python
from fastapi.responses import JSONResponse
from src.services.agent_graph_contracts import AgentInProgressError
from src.services.agent_graph_service import AgentGraphService
from src.services.agent_router_factory import build_production_agent_router
```

Replace the body of `agent_chat` after conversation creation with:

```python
    try:
        response = await AgentGraphService(search, requirements, router=build_production_agent_router()).chat(
            request=body,
            conversation_id=str(conversation_id),
            thread_id=conversation.thread_id,
            user_id=str(user.id),
            allowed_course_ids=context.allowed_course_ids,
        )
    except AgentInProgressError as exc:
        return JSONResponse(
            status_code=409,
            content=exc.to_response().model_dump(by_alias=True),
        )
    await db.commit()
    return response
```

Do not persist duplicate user/assistant messages in `agent_chat`; message persistence moves inside `AgentGraphService` in the pending-action/persistence tasks. Before those tasks are complete, persistence behavior is intentionally bootstrap-only and not full-spec replay-safe.

- [ ] **Step 5: Run contract tests**

Run:

```bash
pytest tests/contract/test_agent_graph_routes.py tests/contract/test_agent_routes.py -q
```

Expected: pass after updating existing tests to include `incomingMessageId` where they post `/api/agent/chat`.

- [ ] **Step 6: Commit**

```bash
git add src/services/agent_lock_service.py src/routers/agent.py tests/contract/test_agent_graph_routes.py tests/contract/test_agent_routes.py
git commit -m "feat: route agent chat through LangGraph service"
```

---

### Task 10: Durable Run Lifecycle In `AgentGraphService` `[done]`

This task wires the runtime primitives into the graph orchestration path. After this task, `AgentGraphService.chat()` owns inbound dedupe, active-run checks, run status transitions, thread locking, response payload persistence, and exact replay of a prior `response_ref`.

**Files:**
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/repositories/agent_graph_repo.py`
- Modify: `src/services/agent_lock_service.py`
- Test: `tests/services/test_agent_graph_service.py`
- Test: `tests/repositories/test_agent_graph_repo.py`

- [ ] **Step 1: Add durable lifecycle tests**

Append to `tests/services/test_agent_graph_service.py`:

```python
async def test_graph_chat_returns_prior_response_for_completed_incoming_message():
    prior = AgentChatResponse(
        conversation_id="conv-1",
        message_id="assistant-1",
        answer=AgentAnswer(markdown="Prior answer", confidence="grounded"),
    )
    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=prior),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
        thread_lock=SimpleNamespace(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="retry", incomingMessageId="msg-dup"),
        conversation_id="conv-1",
        thread_id="thread-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
    )

    assert response == prior


async def test_graph_chat_active_run_returns_in_progress_before_invoking_graph():
    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="run-active")),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
        thread_lock=SimpleNamespace(),
    )

    with pytest.raises(AgentInProgressError) as exc_info:
        await service.chat(
            request=AgentChatRequest(message="new", incomingMessageId="msg-new"),
            conversation_id="conv-1",
            thread_id="thread-1",
            user_id=str(uuid4()),
            allowed_course_ids=["CS231n"],
        )

    assert exc_info.value.graph_run_id == "run-active"
```

- [ ] **Step 2: Add success transition test**

Append to `tests/services/test_agent_graph_service.py`:

```python
async def test_graph_chat_creates_run_locks_stores_response_and_marks_succeeded():
    events = []

    class Lock:
        async def __aenter__(self):
            events.append("lock")

        async def __aexit__(self, exc_type, exc, tb):
            events.append("unlock")

    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=None),
        create_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="run-1")),
        mark_run_running=AsyncMock(side_effect=lambda run_id: events.append("running")),
        store_response_payload=AsyncMock(return_value="resp-1"),
        mark_run_succeeded=AsyncMock(side_effect=lambda run_id, response_ref, checkpoint_id=None: events.append(("succeeded", response_ref))),
        mark_run_failed=AsyncMock(),
    )
    lock_service = SimpleNamespace(
        acquire=lambda **kwargs: Lock(),
    )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-1", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
        thread_lock=lock_service,
    )

    await service.chat(
        request=AgentChatRequest(message="where is attention?", incomingMessageId="msg-1"),
        conversation_id="conv-1",
        thread_id="thread-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
    )

    assert events == ["lock", "running", ("succeeded", "resp-1"), "unlock"]
```

- [ ] **Step 3: Implement lifecycle orchestration**

In `AgentGraphService.chat()`, wrap the existing graph invoke with this order:

```python
completed = await self.graph_repo.get_completed_response_by_incoming_message(
    conversation_id=conversation_id,
    thread_id=thread_id,
    incoming_message_id=request.incoming_message_id,
)
if completed is not None:
    return completed

active_run = await self.graph_repo.get_active_run(thread_id=thread_id)
if active_run is not None:
    raise AgentInProgressError(conversation_id, thread_id, active_run.graph_run_id, retry_after_ms=1000)

run = await self.graph_repo.create_run(
    conversation_id=conversation_id,
    thread_id=thread_id,
    incoming_message_id=request.incoming_message_id,
)

async with self.thread_lock.acquire(
    conversation_id=conversation_id,
    thread_id=thread_id,
    graph_run_id=run.graph_run_id,
):
    await self.graph_repo.mark_run_running(run.graph_run_id)
    try:
        response = await self._invoke_graph_and_compose(
            request=request,
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_id=user_id,
            allowed_course_ids=allowed_course_ids,
        )
        response_ref = await self.graph_repo.store_response_payload(
            graph_run_id=run.graph_run_id,
            response=response,
            deterministic_key=f"{thread_id}:{request.incoming_message_id}",
        )
        await self.graph_repo.mark_run_succeeded(run.graph_run_id, response_ref=response_ref)
        return response
    except Exception as exc:
        await self.graph_repo.mark_run_failed(run.graph_run_id, error=str(exc), retryable=True)
        raise
```

Keep graph invocation in a private `_invoke_graph_and_compose()` helper so dedupe and run lifecycle cannot be bypassed by future route code.

- [ ] **Step 4: Add repository response-ref helpers**

In `src/repositories/agent_graph_repo.py`, add methods used above:

```python
async def get_completed_response_by_incoming_message(self, *, conversation_id: str, thread_id: str, incoming_message_id: str) -> AgentChatResponse | None:
    run = await self.get_run_by_incoming_message(conversation_id, thread_id, incoming_message_id)
    if run is None or run.status != "succeeded" or not run.response_ref:
        return None
    return await self.load_response_payload(run.response_ref)


async def store_response_payload(self, *, graph_run_id: str, response: AgentChatResponse, deterministic_key: str) -> str:
    response_ref = f"agent_response:{deterministic_key}"
    await self.upsert_response_payload(response_ref=response_ref, graph_run_id=graph_run_id, payload=response.model_dump(mode="json", by_alias=True))
    return response_ref
```

`response_ref` must be stable for the same `(thread_id, incoming_message_id)` so retries reuse the same assistant payload.

- [ ] **Step 5: Run durable lifecycle tests**

Run:

```bash
pytest tests/services/test_agent_graph_service.py tests/repositories/test_agent_graph_repo.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/services/agent_graph_service.py src/repositories/agent_graph_repo.py src/services/agent_lock_service.py tests/services/test_agent_graph_service.py tests/repositories/test_agent_graph_repo.py
git commit -m "feat: wire durable agent graph run lifecycle"
```

---

### Task 11: Pending Action API Shell And Continuation Endpoint `[done]`

This task creates the API and contract shell for pending-action continuation. It is not the production interrupt/resume implementation. Real LangGraph `interrupt()` boundaries, persisted pending-action validation, and idempotent commit nodes are completed in the path-switch, assessment, and replan action implementation tasks.

**Files:**
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/services/agent_tool_nodes.py`
- Modify: `src/repositories/agent_graph_repo.py`
- Modify: `src/routers/agent.py`
- Test: `tests/services/test_agent_graph_service.py`
- Test: `tests/contract/test_agent_graph_routes.py`

- [ ] **Step 1: Add tests for pending action proposal and resume validation**

Append to `tests/services/test_agent_graph_service.py`:

```python
async def test_assessment_request_returns_pending_action_with_action_id():
    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[{"canonical_unit_id": "unit-attn", "course_id": "CS224n", "unit_name": "Attention", "score": 3, "quiz_available": True}],
            trace=RetrievalTrace(trace_id="trace-2", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Cho tôi quiz về attention mechanism", incomingMessageId="msg-3"),
        conversation_id=str(uuid4()),
        thread_id="thread-3",
        user_id=str(uuid4()),
        allowed_course_ids=["CS224n"],
    )

    assert response.actions
    assert response.actions[0].action_id
    assert response.actions[0].type == "start_assessment_workflow"
```

- [ ] **Step 2: Add contract test for continuation endpoint**

Append to `tests/contract/test_agent_graph_routes.py`:

```python
async def test_action_continue_requires_action_id_and_returns_graph_response():
    user_id = uuid4()
    graph_response = AgentChatResponse(
        conversation_id="conv-1",
        message_id="assistant-1",
        answer=AgentAnswer(markdown="Action confirmed.", confidence="partial"),
    )

    with patch("src.routers.agent.AgentGraphService") as service_cls:
        service_cls.return_value.resume_action = AsyncMock(return_value=graph_response)
        client = await _client_for_user(user_id)
        try:
            response = await client.post(
                "/api/agent/actions/continue",
                json={
                    "conversationId": "conv-1",
                    "actionId": "act-1",
                    "decision": "approve",
                    "incomingMessageId": "msg-resume-1",
                },
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"]["markdown"] == "Action confirmed."
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
pytest tests/services/test_agent_graph_service.py tests/contract/test_agent_graph_routes.py -q
```

Expected: missing proposal action behavior and continuation endpoint.

- [ ] **Step 4: Implement pending action proposal in tool nodes**

In `src/services/agent_tool_nodes.py`, add:

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from src.schemas.agent import AgentAction

    async def assessment_proposal(self, slots: AgentSlots) -> ToolResult:
        action_id = f"act_{uuid4()}"
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return ToolResult(
            kind="assessment_proposal",
            answer_markdown="I can prepare an assessment proposal for that topic.",
            actions=[
                AgentAction(
                    type="start_assessment_workflow",
                    label="Prepare assessment proposal",
                    actionId=action_id,
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    canonical_unit_ids=slots.canonical_unit_ids,
                    eligible=True,
                )
            ],
            requires_evidence=False,
        )
```

In `AgentGraphService._dispatch`, route `assess_knowledge` with resolved canonical ids to `assessment_proposal`.

- [ ] **Step 5: Add continuation route**

In `src/routers/agent.py`, add import:

```python
from src.schemas.agent import AgentActionResumeRequest
```

Add route:

```python
@agent_router.post("/actions/continue", response_model=AgentChatResponse)
async def agent_continue_action(
    body: AgentActionResumeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentChatResponse:
    repo, _navigation, search, requirements = _services(db)
    try:
        response = await AgentGraphService(search, requirements, router=build_production_agent_router()).resume_action(
            request=body,
            user_id=str(user.id),
        )
    except AgentInProgressError as exc:
        return JSONResponse(status_code=409, content=exc.to_response().model_dump(by_alias=True))
    await db.commit()
    return response
```

Add `resume_action` to `AgentGraphService`:

```python
    async def resume_action(self, request, user_id: str) -> AgentChatResponse:
        return AgentChatResponse(
            conversation_id=request.conversation_id,
            message_id=str(uuid4()),
            answer={"markdown": "Action confirmed.", "confidence": "partial"},
        )
```

This initial method is a safe non-mutating shell. It is not the production interrupt/resume flow. Commit side effects are added in the assessment/replan/path-switch tasks that wire existing backend services with idempotency keys.

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/services/test_agent_graph_service.py tests/contract/test_agent_graph_routes.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/services/agent_graph_service.py src/services/agent_tool_nodes.py src/routers/agent.py tests/services/test_agent_graph_service.py tests/contract/test_agent_graph_routes.py
git commit -m "feat: add agent pending action continuation shell"
```

---

### Task 12: Path Switch Pending Action Workflow `[done]`

**Files:**
- Create: `src/services/agent_path_switch_service.py`
- Modify: `src/services/agent_graph_contracts.py`
- Modify: `src/services/agent_tool_nodes.py`
- Modify: `src/services/agent_policy_service.py`
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/repositories/goal_preference_repo.py`
- Test: `tests/services/test_agent_path_switch_service.py`
- Test: `tests/services/test_agent_graph_service.py`

- [ ] **Step 1: Write path switch service tests**

Create `tests/services/test_agent_path_switch_service.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.agent_path_switch_service import AgentPathSwitchService

pytestmark = pytest.mark.asyncio


async def test_path_switch_rejects_same_path():
    service = AgentPathSwitchService(
        goal_repo=SimpleNamespace(),
        planner=lambda *args, **kwargs: None,
    )

    result = await service.validate_request(
        user_id=uuid4(),
        current_course_ids=["CS230", "CS224n"],
        target_path_id="nlp",
        allowed_course_ids=["CS230", "CS224n", "CS231n"],
    )

    assert result.allow is False
    assert result.codes == ["SAME_PATH_SWITCH"]


async def test_path_switch_builds_valid_proposal_for_nlp():
    service = AgentPathSwitchService(
        goal_repo=SimpleNamespace(),
        planner=lambda *args, **kwargs: None,
    )

    result = await service.validate_request(
        user_id=uuid4(),
        current_course_ids=["CS230", "CS231n"],
        target_path_id="nlp",
        allowed_course_ids=["CS230", "CS224n", "CS231n"],
    )

    assert result.allow is True
    proposal = service.build_proposal(
        current_course_ids=["CS230", "CS231n"],
        target_path_id="nlp",
    )
    assert proposal["target_path_id"] == "nlp"
    assert proposal["target_course_ids"] == ["CS230", "CS224n"]
    assert proposal["reuse_profile"] is True
    assert proposal["recompute_plan"] is True


async def test_commit_path_switch_updates_goal_and_replans_once():
    calls = {"goal": 0, "planner": 0}

    async def upsert_for_user(user_id, **goal_data):
        calls["goal"] += 1
        return SimpleNamespace(selected_course_ids=goal_data["selected_course_ids"])

    async def planner(db, user, request):
        calls["planner"] += 1
        return SimpleNamespace(total_units=10, total_hours=8.5, warnings=[])

    service = AgentPathSwitchService(
        goal_repo=SimpleNamespace(upsert_for_user=upsert_for_user),
        planner=planner,
    )

    result = await service.commit(
        db=SimpleNamespace(),
        user=SimpleNamespace(id=uuid4()),
        target_path_id="nlp",
        idempotency_key="idem-path-1",
    )

    assert result["targetPathId"] == "nlp"
    assert calls == {"goal": 1, "planner": 1}


async def test_commit_path_switch_replay_reuses_idempotency_key():
    calls = {"goal": 0, "planner": 0}

    async def upsert_for_user(user_id, **goal_data):
        calls["goal"] += 1
        return SimpleNamespace(selected_course_ids=goal_data["selected_course_ids"])

    async def planner(db, user, request):
        calls["planner"] += 1
        return SimpleNamespace(total_units=10, total_hours=8.5, warnings=[])

    service = AgentPathSwitchService(
        goal_repo=SimpleNamespace(upsert_for_user=upsert_for_user),
        planner=planner,
    )
    user = SimpleNamespace(id=uuid4())

    first = await service.commit(SimpleNamespace(), user, "nlp", "idem-path-1")
    second = await service.commit(SimpleNamespace(), user, "nlp", "idem-path-1")

    assert first == second
    assert calls == {"goal": 1, "planner": 1}
```

- [ ] **Step 2: Run failing path switch tests**

Run:

```bash
pytest tests/services/test_agent_path_switch_service.py -q
```

Expected: missing path switch service.

- [ ] **Step 3: Implement path switch service**

Create `src/services/agent_path_switch_service.py`:

The in-memory `_commit_cache` below is a unit-test seam. Production must not rely on process memory for idempotency; production wiring must back idempotency with `agent_pending_actions` / graph idempotency records.

```python
from __future__ import annotations

from typing import Any
from uuid import UUID

from src.schemas.learning_path import GeneratePathRequest
from src.services.agent_graph_contracts import PolicyDecision


SUPPORTED_AGENT_PATHS: dict[str, dict[str, Any]] = {
    "computer_vision": {
        "label": "Computer Vision",
        "selected_course_ids": ["CS230", "CS231n"],
    },
    "nlp": {
        "label": "Natural Language Processing",
        "selected_course_ids": ["CS230", "CS224n"],
    },
}


class AgentPathSwitchService:
    def __init__(self, goal_repo, planner):
        self.goal_repo = goal_repo
        self.planner = planner
        self._commit_cache: dict[str, dict[str, Any]] = {}

    async def validate_request(
        self,
        user_id: UUID,
        current_course_ids: list[str],
        target_path_id: str | None,
        allowed_course_ids: list[str],
    ) -> PolicyDecision:
        if target_path_id not in SUPPORTED_AGENT_PATHS:
            return PolicyDecision(
                allow=False,
                codes=["TARGET_PATH_NOT_FOUND"],
                user_safe_message="That learning path is not available.",
                audit_context={"targetPathId": target_path_id},
            )
        target_courses = SUPPORTED_AGENT_PATHS[target_path_id]["selected_course_ids"]
        if sorted(current_course_ids) == sorted(target_courses):
            return PolicyDecision(
                allow=False,
                codes=["SAME_PATH_SWITCH"],
                user_safe_message="You are already on that learning path.",
                audit_context={"targetPathId": target_path_id},
            )
        missing = [course_id for course_id in target_courses if course_id not in allowed_course_ids]
        if missing:
            return PolicyDecision(
                allow=False,
                codes=["TARGET_PATH_OUT_OF_SCOPE"],
                user_safe_message="That learning path is outside your current access scope.",
                audit_context={"missingCourseIds": missing},
            )
        return PolicyDecision(allow=True)

    def build_proposal(self, current_course_ids: list[str], target_path_id: str) -> dict[str, Any]:
        target = SUPPORTED_AGENT_PATHS[target_path_id]
        return {
            "current_course_ids": current_course_ids,
            "target_path_id": target_path_id,
            "target_course_ids": target["selected_course_ids"],
            "reuse_profile": True,
            "recompute_plan": True,
            "impact_summary": f"Switch to {target['label']} and recompute the learning plan using the learner profile.",
            "payload_version": 1,
        }

    async def commit(self, db, user, target_path_id: str, idempotency_key: str) -> dict[str, Any]:
        if idempotency_key in self._commit_cache:
            return self._commit_cache[idempotency_key]
        target = SUPPORTED_AGENT_PATHS[target_path_id]
        await self.goal_repo.upsert_for_user(
            user.id,
            selected_course_ids=target["selected_course_ids"],
            notes=f"agent_path_switch:{idempotency_key}",
        )
        generated = await self.planner(db, user, GeneratePathRequest())
        result = {
            "targetPathId": target_path_id,
            "targetCourseIds": target["selected_course_ids"],
            "totalUnits": generated.total_units,
            "totalHours": generated.total_hours,
            "warnings": generated.warnings,
        }
        self._commit_cache[idempotency_key] = result
        return result
```

- [ ] **Step 4: Add path switch graph behavior test**

Append to `tests/services/test_agent_graph_service.py`:

```python
async def test_graph_path_switch_request_returns_pending_action():
    class Router:
        def route(self, message, route_context):
            from src.services.agent_graph_router import AgentRoute
            from src.services.agent_graph_contracts import AgentSlots

            return AgentRoute(
                intent="request_path_switch",
                confidence=0.92,
                extracted_slots=AgentSlots(target_path="nlp", requested_path_id="nlp"),
                rationale="User asked to switch to NLP.",
            )

    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Tôi muốn chuyển từ CV sang NLP.", incomingMessageId="msg-path-1"),
        conversation_id=str(uuid4()),
        thread_id="thread-path-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS230", "CS224n", "CS231n"],
    )

    assert response.actions
    assert response.actions[0].action_id
    assert response.actions[0].type == "request_path_switch"
```

- [ ] **Step 5: Wire path switch proposal into tool nodes**

In `src/services/agent_tool_nodes.py`, add a path-switch proposal method:

```python
    async def path_switch_proposal(self, slots: AgentSlots) -> ToolResult:
        action_id = f"act_{uuid4()}"
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return ToolResult(
            kind="path_switch_proposal",
            answer_markdown="I can switch your active learning path after you confirm.",
            actions=[
                AgentAction(
                    type="request_path_switch",
                    label="Confirm path switch",
                    actionId=action_id,
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    eligible=True,
                )
            ],
            requires_evidence=False,
        )
```

In `AgentGraphService._dispatch`, route `request_path_switch` to `self.tools.path_switch_proposal(state["slots"])`.

- [ ] **Step 6: Run path switch tests**

Run:

```bash
pytest tests/services/test_agent_path_switch_service.py tests/services/test_agent_graph_service.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/services/agent_path_switch_service.py src/services/agent_graph_contracts.py src/services/agent_tool_nodes.py src/services/agent_policy_service.py src/services/agent_graph_service.py src/repositories/goal_preference_repo.py tests/services/test_agent_path_switch_service.py tests/services/test_agent_graph_service.py
git commit -m "feat: add agent path switch proposal workflow"
```

---

### Task 13: Real LangGraph Interrupt/Resume Action Flow `[done]`

This task replaces the pending-action shell with production graph boundaries. Assessment, replan, and path switch proposals must persist pending actions, pause with `interrupt()`, resume with the same `thread_id`, validate ownership/status/expiry/payload version, commit side effects with `idempotency_key`, and mark final action state exactly once.

**Files:**
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/services/agent_tool_nodes.py`
- Modify: `src/repositories/agent_graph_repo.py`
- Modify: `src/services/agent_path_switch_service.py`
- Modify: `src/services/agent_action_service.py`
- Test: `tests/services/test_agent_graph_actions.py`
- Test: `tests/services/test_agent_path_switch_service.py`

- [ ] **Step 1: Write interrupt proposal persistence test**

Create `tests/services/test_agent_graph_actions.py`:

```python
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.schemas.agent import AgentActionResumeRequest, AgentChatRequest
from src.services.agent_graph_router import AgentRoute, DeterministicAgentRouter
from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_graph_service import AgentGraphService

pytestmark = pytest.mark.asyncio


class NoopLock:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return None


class NoopThreadLock:
    def acquire(self, **kwargs):
        return NoopLock()


class PathSwitchRouter:
    def route(self, message, route_context):
        return AgentRoute(
            intent="request_path_switch",
            confidence=0.95,
            extracted_slots=AgentSlots(target_path="nlp", requested_path_id="nlp"),
            rationale="switch path",
        )


async def test_path_switch_proposal_persists_pending_action_before_interrupt():
    repo = SimpleNamespace(
        create_pending_action=AsyncMock(return_value=SimpleNamespace(action_id="act-1")),
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=None),
        create_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="run-1")),
        mark_run_running=AsyncMock(),
        store_response_payload=AsyncMock(return_value="resp-1"),
        mark_run_succeeded=AsyncMock(),
        mark_run_failed=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=PathSwitchRouter(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Tôi muốn chuyển từ CV sang NLP.", incomingMessageId="msg-path"),
        conversation_id="conv-1",
        thread_id="thread-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS230", "CS224n", "CS231n"],
    )

    repo.create_pending_action.assert_awaited_once()
    assert response.actions[0].action_id == "act-1"
```

- [ ] **Step 2: Write approve replay idempotency test**

Append to `tests/services/test_agent_graph_actions.py`:

```python
async def test_resume_approve_commits_action_once_for_replayed_request():
    pending = SimpleNamespace(
        action_id="act-1",
        type="request_path_switch",
        status="awaiting_confirmation",
        thread_id="thread-1",
        conversation_id="conv-1",
        user_id="user-1",
        payload={"target_path_id": "nlp", "payload_version": 1},
        payload_version=1,
        idempotency_key="idem-act-1",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    repo = SimpleNamespace(
        get_pending_action=AsyncMock(return_value=pending),
        get_committed_action_result=AsyncMock(side_effect=[None, {"targetPathId": "nlp"}]),
        mark_action_committed=AsyncMock(),
        mark_action_cancelled=AsyncMock(),
    )
    path_switch = SimpleNamespace(commit=AsyncMock(return_value={"targetPathId": "nlp"}))
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
        path_switch_service=path_switch,
    )
    request = AgentActionResumeRequest(
        conversationId="conv-1",
        actionId="act-1",
        decision="approve",
        incomingMessageId="msg-resume-1",
    )

    first = await service.resume_action(request=request, user_id="user-1")
    second = await service.resume_action(request=request, user_id="user-1")

    path_switch.commit.assert_awaited_once()
    assert first.answer.markdown == second.answer.markdown
```

- [ ] **Step 3: Implement pending action persistence before interrupt**

In `src/services/agent_graph_service.py`, add proposal nodes:

```python
from langgraph.types import interrupt


async def _persist_pending_action_node(self, state: dict) -> dict:
    proposal = state["action_proposal"]
    pending = await self.graph_repo.create_pending_action(
        conversation_id=state["conversation_id"],
        thread_id=state["thread_id"],
        user_id=state["user_id"],
        action_type=proposal.type,
        payload=proposal.payload,
        payload_version=proposal.payload_version,
        idempotency_key=proposal.idempotency_key,
        expires_at=proposal.expires_at,
    )
    return {"pending_action": pending}


async def _await_confirmation_node(self, state: dict) -> dict:
    pending = state["pending_action"]
    decision = interrupt(
        {
            "action_id": pending.action_id,
            "type": pending.type,
            "summary": pending.payload.get("impact_summary"),
            "expires_at": pending.expires_at.isoformat(),
        }
    )
    return {"resume_decision": decision}
```

The node that calls `interrupt()` must not perform business side effects. It only returns the resume decision.

- [ ] **Step 4: Implement resume validation node**

In `src/services/agent_graph_service.py`, add:

```python
async def _validate_pending_action_node(self, state: dict) -> dict:
    pending = await self.graph_repo.get_pending_action(action_id=state["action_id"])
    if pending is None:
        return {"action_error": "missing_action"}
    if pending.user_id != state["user_id"] or pending.thread_id != state["thread_id"]:
        return {"action_error": "ownership_mismatch"}
    if pending.status != "awaiting_confirmation":
        return {"action_error": f"invalid_status:{pending.status}"}
    if pending.expires_at <= datetime.now(UTC):
        await self.graph_repo.mark_action_expired(pending.action_id)
        return {"action_error": "expired"}
    if pending.payload.get("payload_version") != pending.payload_version:
        return {"action_error": "payload_version_mismatch"}
    return {"pending_action": pending}
```

- [ ] **Step 5: Implement commit action node**

In `src/services/agent_graph_service.py`, add dispatch by action type:

```python
async def _commit_action_node(self, state: dict) -> dict:
    pending = state["pending_action"]
    existing = await self.graph_repo.get_committed_action_result(pending.action_id)
    if existing is not None:
        return {"committed_action_result": existing}

    if pending.type == "request_path_switch":
        result = await self.path_switch_service.commit(
            db=state["db"],
            user=state["user"],
            target_path_id=pending.payload["target_path_id"],
            idempotency_key=pending.idempotency_key,
        )
    elif pending.type == "request_replan":
        result = await self.replan_service.commit_replan(
            db=state["db"],
            user=state["user"],
            payload=pending.payload,
            idempotency_key=pending.idempotency_key,
        )
    elif pending.type in {"propose_assessment", "start_assessment"}:
        result = await self.assessment_service.commit_assessment(
            db=state["db"],
            user=state["user"],
            payload=pending.payload,
            idempotency_key=pending.idempotency_key,
        )
    else:
        raise ValueError(f"Unsupported pending action type: {pending.type}")

    await self.graph_repo.mark_action_committed(pending.action_id, result=result)
    return {"committed_action_result": result}
```

All business side effects must be inside commit services that accept `idempotency_key`; no proposal or interrupt node may mutate planner, assessment, or active path state.

- [ ] **Step 6: Wire `resume_action()` to same `thread_id` and graph resume**

In `resume_action()`, load the pending action, acquire the same thread lock, and resume:

```python
pending = await self.graph_repo.get_pending_action(action_id=request.action_id)
if pending is None:
    return self.composer.compose_action_error(request.conversation_id, "missing_action")

async with self.thread_lock.acquire(
    conversation_id=pending.conversation_id,
    thread_id=pending.thread_id,
    graph_run_id=f"resume:{request.incoming_message_id}",
):
    if request.decision == "reject":
        await self.graph_repo.mark_action_cancelled(pending.action_id)
        return self.composer.compose_action_cancelled(pending.conversation_id)
    if request.decision == "edit":
        edited = await self._validate_and_rebuild_action_proposal(pending, request.edit_payload)
        return await self._interrupt_with_rebuilt_proposal(edited)
    return await self._resume_graph_with_command(
        thread_id=pending.thread_id,
        resume_payload={"decision": "approve", "action_id": pending.action_id},
    )
```

- [ ] **Step 7: Run real action flow tests**

Run:

```bash
pytest tests/services/test_agent_graph_actions.py tests/services/test_agent_path_switch_service.py tests/services/test_agent_graph_service.py -q
```

Expected: pass, including replay-safe approve behavior.

- [ ] **Step 8: Commit**

```bash
git add src/services/agent_graph_service.py src/services/agent_tool_nodes.py src/repositories/agent_graph_repo.py src/services/agent_path_switch_service.py src/services/agent_action_service.py tests/services/test_agent_graph_actions.py tests/services/test_agent_path_switch_service.py tests/services/test_agent_graph_service.py
git commit -m "feat: implement agent interrupt resume action flow"
```

---

### Task 14: Memory Compaction And Operational Safety `[bootstrap-only]`

This task creates the initial compaction primitive and tests preservation of active context. It is not the final memory policy implementation: it does not yet integrate into `memory_ref`, enforce the full token/message threshold policy, or persist/version refreshes idempotently inside `AgentGraphService`.

**Files:**
- Create: `src/services/agent_memory_compaction_service.py`
- Modify: `src/repositories/agent_conversation_repo.py`
- Test: `tests/services/test_agent_conversation_service.py`
- Test: `tests/services/test_agent_memory_compaction_service.py`

- [ ] **Step 1: Write compaction tests**

Create `tests/services/test_agent_memory_compaction_service.py`:

```python
from types import SimpleNamespace

from src.services.agent_memory_compaction_service import AgentMemoryCompactionService


def test_compaction_preserves_active_context_and_versions_summary():
    messages = [
        SimpleNamespace(role="user", markdown=f"old message {index}") for index in range(12)
    ] + [
        SimpleNamespace(role="assistant", markdown="recent answer"),
        SimpleNamespace(role="user", markdown="recent question"),
    ]

    result = AgentMemoryCompactionService(max_recent_turns=2).compact(
        messages=messages,
        pending_action={"action_id": "act-1"},
        active_slots={"canonical_unit_ids": ["unit-1"]},
        clarification_target={"field": "canonical_unit_id"},
    )

    assert result.summary_version == 1
    assert len(result.recent_messages) == 2
    assert result.pending_action == {"action_id": "act-1"}
    assert result.active_slots == {"canonical_unit_ids": ["unit-1"]}
```

- [ ] **Step 2: Run failing compaction test**

Run:

```bash
pytest tests/services/test_agent_memory_compaction_service.py -q
```

Expected: missing module.

- [ ] **Step 3: Implement compaction service**

Create `src/services/agent_memory_compaction_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompactedThreadMemory:
    summary_version: int
    summary: dict[str, Any]
    recent_messages: list[Any]
    pending_action: dict[str, Any] | None
    active_slots: dict[str, Any]
    clarification_target: dict[str, Any] | None


class AgentMemoryCompactionService:
    def __init__(self, max_recent_turns: int = 10):
        self.max_recent_turns = max_recent_turns

    def compact(
        self,
        messages: list[Any],
        pending_action: dict[str, Any] | None,
        active_slots: dict[str, Any],
        clarification_target: dict[str, Any] | None,
    ) -> CompactedThreadMemory:
        recent = messages[-self.max_recent_turns :]
        older = messages[: max(0, len(messages) - self.max_recent_turns)]
        summary_text = "\n".join(f"{message.role}: {message.markdown}" for message in older)
        return CompactedThreadMemory(
            summary_version=1,
            summary={"summaryText": summary_text, "messageCount": len(older)},
            recent_messages=recent,
            pending_action=pending_action,
            active_slots=active_slots,
            clarification_target=clarification_target,
        )
```

- [ ] **Step 4: Run compaction test**

Run:

```bash
pytest tests/services/test_agent_memory_compaction_service.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_memory_compaction_service.py tests/services/test_agent_memory_compaction_service.py
git commit -m "feat: add agent thread memory compaction"
```

---

### Task 15: Frontend Idempotency And Action IDs `[done]`

**Files:**
- Modify: `frontend/features/agent/api.ts`
- Modify: `frontend/features/agent/components/AgentChatPage.tsx`
- Test: `frontend/tests/lib/agent/agentInProgress.test.ts`
- Test: `frontend/tests/routes/agent/page.test.tsx`

- [ ] **Step 1: Add frontend API tests for in-progress parsing**

Create `frontend/tests/lib/agent/agentInProgress.test.ts`:

```ts
import { getInProgressRetryAfter, isAgentInProgress } from "@/features/agent/api";

describe("agent in-progress response helpers", () => {
  it("recognizes 409 in-progress payloads", () => {
    const payload = {
      status: "in_progress",
      conversationId: "conv-1",
      threadId: "thread-1",
      graphRunId: "run-1",
      retryAfterMs: 1000,
    };

    expect(isAgentInProgress(payload)).toBe(true);
    expect(getInProgressRetryAfter(payload)).toBe(1000);
  });
});
```

- [ ] **Step 2: Run failing frontend test**

Run:

```bash
cd frontend && npm test -- agentInProgress.test.ts
```

Expected: missing helper exports.

- [ ] **Step 3: Implement API helpers and payload fields**

In `frontend/features/agent/api.ts`, add:

```ts
export interface AgentInProgressResponse {
  status: "in_progress";
  conversationId: string;
  threadId: string;
  graphRunId: string;
  retryAfterMs: number;
}

export function isAgentInProgress(value: unknown): value is AgentInProgressResponse {
  return Boolean(
    value &&
      typeof value === "object" &&
      (value as AgentInProgressResponse).status === "in_progress" &&
      typeof (value as AgentInProgressResponse).retryAfterMs === "number",
  );
}

export function getInProgressRetryAfter(value: AgentInProgressResponse) {
  return value.retryAfterMs;
}
```

Extend `AgentAction`:

```ts
// Add "request_path_switch" to AgentActionType.
  action_id?: string | null;
  actionId?: string | null;
  status?: string | null;
  expires_at?: string | null;
  expiresAt?: string | null;
```

Add helper:

```ts
export function getActionId(value: AgentAction) {
  return value.actionId ?? value.action_id ?? "";
}
```

Change `agentApi.chat` payload type:

```ts
  chat: (payload: {
    message: string;
    incomingMessageId: string;
    conversationId?: string | null;
    routeContext?: Record<string, unknown>;
    traceMode?: "none" | "summary" | "full";
  }) => api.post<AgentChatResponse>("/api/agent/chat", payload).then((r) => r.data),
```

Add continuation API:

```ts
  continueAction: (payload: {
    conversationId: string;
    actionId: string;
    decision: "approve" | "reject" | "edit";
    editPayload?: Record<string, unknown> | null;
    incomingMessageId: string;
  }) => api.post<AgentChatResponse>("/api/agent/actions/continue", payload).then((r) => r.data),
```

- [ ] **Step 4: Send stable incoming message ids from chat page**

In `frontend/features/agent/components/AgentChatPage.tsx`, create `incomingMessageId` once when the outbound user message object is created and store it on that local pending message. Retries for the same outbound message must reuse the stored id; they must not call `crypto.randomUUID()` again.

```ts
type PendingAgentMessage = {
  localId: string;
  role: "user";
  content: string;
  incomingMessageId: string;
  retryCount: number;
};

function createIncomingMessageId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const pendingMessage: PendingAgentMessage = {
  localId:
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  role: "user",
  content: message,
  incomingMessageId: createIncomingMessageId(),
  retryCount: 0,
};
```

Send and retry with the same `pendingMessage.incomingMessageId`:

```ts
const response = await agentApi.chat({
  message: pendingMessage.content,
  incomingMessageId: pendingMessage.incomingMessageId,
  conversationId: activeSessionId,
  traceMode: "summary",
});

async function retryPendingMessage(pendingMessage: PendingAgentMessage) {
  return agentApi.chat({
    message: pendingMessage.content,
    incomingMessageId: pendingMessage.incomingMessageId,
    conversationId: activeSessionId,
    traceMode: "summary",
  });
}
```

Do not implement retry by constructing a new outbound message object. A new UUID is correct only for a new user message or a new action continuation request:

```ts
const actionIncomingMessageId =
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
```

When action buttons trigger backend continuation, use `getActionId(action)` and a new `incomingMessageId` for the continuation.

- [ ] **Step 5: Run frontend tests**

Run:

```bash
cd frontend && npm test -- agentInProgress.test.ts page.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/features/agent/api.ts frontend/features/agent/components/AgentChatPage.tsx frontend/tests/lib/agent/agentInProgress.test.ts frontend/tests/routes/agent/page.test.tsx
git commit -m "feat: add agent idempotency fields to frontend"
```

---

### Task 16: Evaluation Suite, Janitor, And Operational Checks `[partial]`

The evaluation lane must target the production `StructuredAgentRouter` when a model provider is configured. The deterministic router seam may be used only for local unit tests that do not call a model.

**Files:**
- Create: `tests/services/test_agent_routing_eval.py`
- Create: `src/services/agent_pending_action_janitor.py`
- Test: `tests/services/test_agent_pending_action_janitor.py`
- Create: `docs/agent-ops-runbook.md`

- [ ] **Step 1: Add routing evaluation tests**

Create `tests/services/test_agent_routing_eval.py`:

```python
import os

import pytest

from src.services.agent_router_factory import build_production_agent_router


@pytest.mark.parametrize(
    ("message", "not_intent"),
    [
        ("Giải thích skip connection", "request_replan"),
        ("Quiz eligibility của unit này tính thế nào?", "assess_knowledge"),
        ("next token prediction là gì", "ask_what_next"),
        ("cho tôi replan, nhưng đừng skip phần attention", "assess_knowledge"),
        ("Tôi muốn chuyển từ CV sang NLP.", "find_content"),
        ("Trong path NLP có bài nào về attention mask không?", "request_path_switch"),
    ],
)
@pytest.mark.skipif(
    os.getenv("RUN_AGENT_ROUTER_EVAL") != "1",
    reason="Set RUN_AGENT_ROUTER_EVAL=1 to call the configured production router model.",
)
def test_adversarial_routing_does_not_follow_keyword_traps(message, not_intent):
    route = build_production_agent_router().route(message=message, route_context=None)

    assert route.intent != not_intent
```

- [ ] **Step 2: Add janitor test**

Create `tests/services/test_agent_pending_action_janitor.py`:

```python
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.services.agent_pending_action_janitor import AgentPendingActionJanitor

pytestmark = pytest.mark.asyncio


async def test_janitor_expires_pending_actions():
    calls = []

    async def expire_pending_actions(now):
        calls.append(now)
        return 2

    repo = SimpleNamespace(expire_pending_actions=expire_pending_actions)
    count = await AgentPendingActionJanitor(repo).run_once(now=datetime.now(UTC))

    assert count == 2
    assert calls
```

- [ ] **Step 3: Implement janitor**

Create `src/services/agent_pending_action_janitor.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime


class AgentPendingActionJanitor:
    def __init__(self, graph_repo):
        self.graph_repo = graph_repo

    async def run_once(self, now: datetime | None = None) -> int:
        return await self.graph_repo.expire_pending_actions(now or datetime.now(UTC))
```

- [ ] **Step 4: Add ops runbook**

Create `docs/agent-ops-runbook.md`:

```markdown
# Agent Ops Runbook

## In-Progress Conflicts

Look up `agent_graph_runs` by `thread_id` and status `created`, `running`, or `interrupted`.

## Stuck Pending Actions

Look up `agent_pending_actions` by `conversation_id`, `thread_id`, or `action_id`.
If `expires_at` is in the past and status is `awaiting_confirmation`, run the pending-action janitor.

## Response Persist Failed After Graph Success

Look up the run by `incoming_message_id`.
If `response_ref` exists, upsert the missing assistant message using `agent_response_payloads.payload_json`.

## State Migration Failure

Archive the old thread, create a new thread for the conversation, and attach a migration note message.
Do not mutate committed assessment, progress, mastery, or planner state.
```

- [ ] **Step 5: Run eval and janitor tests**

Run:

```bash
pytest tests/services/test_agent_routing_eval.py tests/services/test_agent_pending_action_janitor.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add tests/services/test_agent_routing_eval.py tests/services/test_agent_pending_action_janitor.py src/services/agent_pending_action_janitor.py docs/agent-ops-runbook.md
git commit -m "test: add agent routing eval and ops janitor"
```

---

### Task 17: Final Integration Verification And Legacy Path Deprecation `[partial]`

**Files:**
- Modify: `src/services/agent_chat_service.py`
- Modify: `tests/services/test_agent_chat_service.py`
- Modify: `docs/superpowers/specs/2026-05-01-langgraph-agent-redesign-design.md` if implementation reveals a documented constraint mismatch.

- [ ] **Step 1: Mark keyword chat service as deprecated compatibility path**

At the top of `src/services/agent_chat_service.py`, add:

```python
"""
Deprecated compatibility service for pre-LangGraph tests and rollback.
Production /api/agent/chat requests must use AgentGraphService.
"""
```

Do not delete the file until the rollout has completed and existing tests have been migrated.

- [ ] **Step 2: Run backend focused suite**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/services/test_agent_* tests/repositories/test_agent_graph_repo.py tests/contract/test_agent_graph_routes.py tests/contract/test_agent_routes.py -q
```

Expected: pass.

- [ ] **Step 3: Run frontend focused suite**

Run:

```bash
cd frontend && npm test -- agent
```

Expected: pass.

- [ ] **Step 4: Run full available test suite if time permits**

Run:

```bash
pytest -q
```

Expected: pass or only known unrelated failures documented in the final implementation report.

- [ ] **Step 5: Commit deprecation note and final test fixes**

```bash
git add src/services/agent_chat_service.py tests/services/test_agent_chat_service.py
git commit -m "chore: mark legacy agent chat service deprecated"
```

---

## Self-Review Checklist

- Spec coverage: persistence ids, thread/checkpoint semantics, in-progress 409 payload, advisory lock, production structured router wiring, context-aware routing, slot ambiguity, search scope escalation, scope expansion continuation, path switch workflow, durable run lifecycle, policy, typed results, no-evidence composer, pending actions, real interrupt/resume action flow, memory compaction, eval suite, ops runbook, frontend idempotency are covered by tasks.
- AI Tutor separation: no task modifies tutor routes/services.
- Replay safety: response refs, run statuses, pending action idempotency, and janitor are covered.
- Concurrency: V1 PostgreSQL advisory lock and `409 in_progress` payload are covered.
- Rollout: legacy service is deprecated but retained for rollback.
- Bootstrap caveats: deterministic router, graph skeleton, pending-action shell, and memory compaction primitive are explicitly marked as non-production-complete until later tasks replace or harden them. Production must not fall back to deterministic keyword routing or process-memory idempotency.
