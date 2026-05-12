from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New chat")
    preview: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    thread_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)

    __table_args__ = (Index("ix_agent_conversations_user_updated", "user_id", "updated_at"),)


class AgentConversationMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_conversation_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    actions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_agent_conversation_messages_conversation_created", "conversation_id", "created_at"
        ),
    )


class AgentConversationMemory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_conversation_memories"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    thread_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_status: Mapped[str] = mapped_column(String(40), nullable=False, default="empty")
    recent_message_window: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
