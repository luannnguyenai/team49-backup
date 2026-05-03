"""Scope agent conversation memory by LangGraph thread.

Revision ID: 20260502_thread_memory_scope
Revises: 20260501_agent_graph_runtime
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_thread_memory_scope"
down_revision = "20260501_agent_graph_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_conversation_memories",
        sa.Column("thread_id", sa.String(length=120), nullable=True),
    )
    op.execute(
        """
        UPDATE agent_conversation_memories AS memory
        SET thread_id = conversation.thread_id
        FROM agent_conversations AS conversation
        WHERE memory.conversation_id = conversation.id
          AND memory.thread_id IS NULL
        """
    )
    op.alter_column("agent_conversation_memories", "thread_id", nullable=False)
    op.create_index(
        "ix_agent_conversation_memories_thread_id",
        "agent_conversation_memories",
        ["thread_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_conversation_memories_thread_id", table_name="agent_conversation_memories")
    op.drop_column("agent_conversation_memories", "thread_id")
