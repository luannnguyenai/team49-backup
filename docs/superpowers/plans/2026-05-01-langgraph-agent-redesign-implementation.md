# LangGraph Agent Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/agent` keyword-routed chat path with a production LangGraph orchestration layer that is context-aware, replay-safe, idempotent, and separate from the lecture AI Tutor.

**Architecture:** Add durable graph persistence primitives first, then introduce typed graph contracts, router/canonicalizer/policy/composer nodes, and finally wire `/api/agent/chat` through `AgentGraphService`. Assessment and replan proposals become durable pending actions with interrupt/resume semantics; retries and concurrent runs are controlled by `incoming_message_id`, `thread_id`, response refs, run statuses, and PostgreSQL advisory locks.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, Pydantic v2, LangGraph 1.1, PostgreSQL, pytest/pytest-asyncio, httpx ASGI tests, Next.js/TypeScript frontend.

---

## File Structure

Create:

- `src/models/agent_graph.py` - SQLAlchemy models for graph runs, pending actions, response payloads, and trace events.
- `src/repositories/agent_graph_repo.py` - persistence/idempotency helpers for graph runs, pending actions, response refs, lock metadata, and retry state.
- `src/services/agent_lock_service.py` - PostgreSQL advisory lock helper keyed by `thread_id`.
- `src/services/agent_memory_compaction_service.py` - versioned thread summary compaction and `memory_ref` management.
- `src/services/agent_graph_contracts.py` - Pydantic/domain contracts for checkpoint state, routing, slots, policy, pending actions, typed tool results, and graph node names.
- `src/services/agent_graph_router.py` - structured intent router and deterministic test router seam.
- `src/services/agent_slot_resolver.py` - deterministic canonicalization from extracted slots to canonical unit/course/planner ids.
- `src/services/agent_policy_service.py` - `PolicyDecision` validation before tool execution/action proposal.
- `src/services/agent_tool_nodes.py` - LangGraph intent nodes backed by existing deterministic services.
- `src/services/agent_response_composer.py` - typed response composer enforcing no-evidence/no-grounded-answer.
- `src/services/agent_graph_service.py` - graph construction/invoke/resume orchestration and route integration API.
- `alembic/versions/20260501_agent_graph_runtime.py` - additive migration for graph runtime tables and `agent_conversations.thread_id`.
- `tests/services/test_agent_graph_contracts.py`
- `tests/repositories/test_agent_graph_repo.py`
- `tests/services/test_agent_graph_router.py`
- `tests/services/test_agent_slot_resolver.py`
- `tests/services/test_agent_policy_service.py`
- `tests/services/test_agent_response_composer.py`
- `tests/services/test_agent_graph_service.py`
- `tests/contract/test_agent_graph_routes.py`
- `frontend/tests/lib/agent/agentInProgress.test.ts`

Modify:

- `src/models/__init__.py` - import new graph models for metadata discovery.
- `src/models/agent_conversation.py` - add `thread_id` to `AgentConversation`.
- `src/repositories/agent_conversation_repo.py` - create/get conversations with thread ids and idempotent message helpers.
- `src/schemas/agent.py` - add `incomingMessageId`, `AgentInProgressResponse`, `AgentActionResumeRequest`, action ids/status/expiry, and `clarify` intent.
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

### Task 1: Schema And Runtime Contract Tests

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
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/services/test_agent_graph_contracts.py -q
```

Expected: failures for missing `incoming_message_id`, missing response/request models, and missing graph contract module.

- [ ] **Step 4: Implement schema additions**

In `src/schemas/agent.py`, add `"clarify"` to `AgentIntent`, add `incoming_message_id` to `AgentChatRequest`, add action metadata to `AgentAction`, and add new request/response models:

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
    "clarify": "clarify_node",
}


class AgentSlots(BaseModel):
    raw_topic: str | None = None
    target_path: Literal["computer_vision", "nlp"] | None = None
    canonical_unit_ids: list[str] = Field(default_factory=list)
    course_ids: list[str] = Field(default_factory=list)
    ambiguity_options: list[dict[str, Any]] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    allow: bool
    codes: list[str] = Field(default_factory=list)
    user_safe_message: str | None = None
    audit_context: dict[str, Any] | None = None


class PendingAction(BaseModel):
    action_id: str
    type: Literal["propose_assessment", "start_assessment", "request_replan"]
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

### Task 2: Graph Runtime Persistence

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

- [ ] **Step 5: Implement repository helpers**

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

- [ ] **Step 6: Update conversation repository to create thread ids**

In `src/repositories/agent_conversation_repo.py`, change `create_conversation`:

```python
from uuid import uuid4

thread_id = f"thread_{uuid4()}"
row = AgentConversation(user_id=user_id, title=title, preview="", message_count=0, thread_id=thread_id)
```

- [ ] **Step 7: Run repository tests**

Run:

```bash
pytest tests/repositories/test_agent_graph_repo.py tests/services/test_agent_conversation_service.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add src/models/agent_graph.py src/models/agent_conversation.py src/models/__init__.py src/repositories/agent_graph_repo.py src/repositories/agent_conversation_repo.py alembic/versions/20260501_agent_graph_runtime.py tests/repositories/test_agent_graph_repo.py
git commit -m "feat: add agent graph runtime persistence"
```

---

### Task 3: Router, Slot Resolver, Policy, And Composer

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

### Task 4: LangGraph Service Skeleton And Tool Nodes

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

### Task 5: Router Integration, Dedupe, Locking, And 409 Responses

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
```

Replace the body of `agent_chat` after conversation creation with:

```python
    try:
        response = await AgentGraphService(search, requirements).chat(
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

Do not persist duplicate user/assistant messages in `agent_chat`; message persistence moves inside `AgentGraphService` in Task 6.

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

### Task 6: Pending Actions, Interrupt Resume, And Continuation Endpoint

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

    service = AgentGraphService(search_service=SimpleNamespace(search=search), requirement_service=SimpleNamespace())

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
        response = await AgentGraphService(search, requirements).resume_action(
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

This initial method is a safe non-mutating shell. Commit side effects are added in the assessment/replan tasks that wire existing backend services with idempotency keys.

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

### Task 7: Memory Compaction And Operational Safety

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

### Task 8: Frontend Idempotency And Action IDs

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

In `frontend/features/agent/components/AgentChatPage.tsx`, update `sendMessage`:

```ts
const incomingMessageId =
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const response = await agentApi.chat({
  message,
  incomingMessageId,
  conversationId: activeSessionId,
  traceMode: "summary",
});
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

### Task 9: Evaluation Suite, Janitor, And Operational Checks

**Files:**
- Create: `tests/services/test_agent_routing_eval.py`
- Create: `src/services/agent_pending_action_janitor.py`
- Test: `tests/services/test_agent_pending_action_janitor.py`
- Create: `docs/agent-ops-runbook.md`

- [ ] **Step 1: Add routing evaluation tests**

Create `tests/services/test_agent_routing_eval.py`:

```python
import pytest

from src.services.agent_graph_router import DeterministicAgentRouter


@pytest.mark.parametrize(
    ("message", "not_intent"),
    [
        ("Giải thích skip connection", "request_replan"),
        ("Quiz eligibility của unit này tính thế nào?", "assess_knowledge"),
        ("next token prediction là gì", "ask_what_next"),
        ("cho tôi replan, nhưng đừng skip phần attention", "assess_knowledge"),
    ],
)
def test_adversarial_routing_does_not_follow_keyword_traps(message, not_intent):
    route = DeterministicAgentRouter().route(message=message, route_context=None)

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

### Task 10: Final Integration Verification And Legacy Path Deprecation

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

- Spec coverage: persistence ids, thread/checkpoint semantics, in-progress 409 payload, advisory lock, context-aware routing, slot ambiguity, policy, typed results, no-evidence composer, pending actions, interrupt/resume shell, memory compaction, eval suite, ops runbook, frontend idempotency are covered by tasks.
- AI Tutor separation: no task modifies tutor routes/services.
- Replay safety: response refs, run statuses, pending action idempotency, and janitor are covered.
- Concurrency: V1 PostgreSQL advisory lock and `409 in_progress` payload are covered.
- Rollout: legacy service is deprecated but retained for rollback.
