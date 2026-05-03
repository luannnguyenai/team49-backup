from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentGraphRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_graph_runs"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    incoming_message_id: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="created")
    response_ref: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    checkpoint_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "thread_id",
            "incoming_message_id",
            name="uq_agent_graph_run_message",
        ),
        Index("ix_agent_graph_runs_thread_status", "thread_id", "status"),
    )


class AgentResponsePayload(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_response_payloads"

    response_ref: Mapped[str] = mapped_column(String(240), nullable=False, unique=True, index=True)
    graph_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_graph_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)


class AgentPendingAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_pending_actions"

    action_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="awaiting_confirmation")
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_version: Mapped[int] = mapped_column(nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_agent_pending_actions_thread_status", "thread_id", "status"),)


class AgentTraceEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_trace_events"

    graph_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_graph_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    trace_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
