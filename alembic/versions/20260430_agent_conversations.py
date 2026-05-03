"""Create agent conversation persistence tables.

Revision ID: 20260430_agent_conversations
Revises: 20260427_merge_schema_v2_cat
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260430_agent_conversations"
down_revision = "20260427_merge_schema_v2_cat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New chat"),
        sa.Column("preview", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_conversations_user_id", "agent_conversations", ["user_id"])
    op.create_index("ix_agent_conversations_user_updated", "agent_conversations", ["user_id", "updated_at"])

    op.create_table(
        "agent_conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("citations_json", postgresql.JSONB(), nullable=True),
        sa.Column("actions_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_conversation_messages_conversation_id", "agent_conversation_messages", ["conversation_id"])
    op.create_index("ix_agent_conversation_messages_user_id", "agent_conversation_messages", ["user_id"])
    op.create_index(
        "ix_agent_conversation_messages_conversation_created",
        "agent_conversation_messages",
        ["conversation_id", "created_at"],
    )

    op.create_table(
        "agent_conversation_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_status", sa.String(length=40), nullable=False, server_default="empty"),
        sa.Column("recent_message_window", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_conversation_memories_user_id", "agent_conversation_memories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_conversation_memories_user_id", table_name="agent_conversation_memories")
    op.drop_table("agent_conversation_memories")
    op.drop_index(
        "ix_agent_conversation_messages_conversation_created",
        table_name="agent_conversation_messages",
    )
    op.drop_index("ix_agent_conversation_messages_user_id", table_name="agent_conversation_messages")
    op.drop_index(
        "ix_agent_conversation_messages_conversation_id",
        table_name="agent_conversation_messages",
    )
    op.drop_table("agent_conversation_messages")
    op.drop_index("ix_agent_conversations_user_updated", table_name="agent_conversations")
    op.drop_index("ix_agent_conversations_user_id", table_name="agent_conversations")
    op.drop_table("agent_conversations")
