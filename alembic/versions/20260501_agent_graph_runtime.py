"""Add agent graph runtime persistence.

Revision ID: 20260501_agent_graph_runtime
Revises: 20260430_agent_conversations
Create Date: 2026-05-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260501_agent_graph_runtime"
down_revision = "20260430_agent_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_conversations", sa.Column("thread_id", sa.String(length=120), nullable=True))
    op.execute(
        "UPDATE agent_conversations SET thread_id = 'thread_' || id::text WHERE thread_id IS NULL"
    )
    op.alter_column("agent_conversations", "thread_id", nullable=False)
    op.create_index(
        "ix_agent_conversations_thread_id",
        "agent_conversations",
        ["thread_id"],
        unique=True,
    )

    op.create_table(
        "agent_graph_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("incoming_message_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="created"),
        sa.Column("response_ref", sa.String(length=240), nullable=True),
        sa.Column("checkpoint_id", sa.String(length=160), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("conversation_id", "thread_id", "incoming_message_id", name="uq_agent_graph_run_message"),
    )
    op.create_index("ix_agent_graph_runs_conversation_id", "agent_graph_runs", ["conversation_id"])
    op.create_index("ix_agent_graph_runs_response_ref", "agent_graph_runs", ["response_ref"])
    op.create_index("ix_agent_graph_runs_thread_id", "agent_graph_runs", ["thread_id"])
    op.create_index("ix_agent_graph_runs_thread_status", "agent_graph_runs", ["thread_id", "status"])

    op.create_table(
        "agent_response_payloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("response_ref", sa.String(length=240), nullable=False, unique=True),
        sa.Column("graph_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_graph_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_response_payloads_response_ref", "agent_response_payloads", ["response_ref"])

    op.create_table(
        "agent_pending_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("action_id", sa.String(length=120), nullable=False, unique=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="awaiting_confirmation"),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False, unique=True),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_pending_actions_action_id", "agent_pending_actions", ["action_id"])
    op.create_index("ix_agent_pending_actions_conversation_id", "agent_pending_actions", ["conversation_id"])
    op.create_index("ix_agent_pending_actions_thread_id", "agent_pending_actions", ["thread_id"])
    op.create_index("ix_agent_pending_actions_thread_status", "agent_pending_actions", ["thread_id", "status"])
    op.create_index("ix_agent_pending_actions_user_id", "agent_pending_actions", ["user_id"])

    op.create_table(
        "agent_trace_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("graph_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_graph_runs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("node_name", sa.String(length=120), nullable=False),
        sa.Column("event_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_trace_events_graph_run_id", "agent_trace_events", ["graph_run_id"])
    op.create_index("ix_agent_trace_events_trace_id", "agent_trace_events", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_trace_events_trace_id", table_name="agent_trace_events")
    op.drop_index("ix_agent_trace_events_graph_run_id", table_name="agent_trace_events")
    op.drop_table("agent_trace_events")
    op.drop_index("ix_agent_pending_actions_user_id", table_name="agent_pending_actions")
    op.drop_index("ix_agent_pending_actions_thread_status", table_name="agent_pending_actions")
    op.drop_index("ix_agent_pending_actions_thread_id", table_name="agent_pending_actions")
    op.drop_index("ix_agent_pending_actions_conversation_id", table_name="agent_pending_actions")
    op.drop_index("ix_agent_pending_actions_action_id", table_name="agent_pending_actions")
    op.drop_table("agent_pending_actions")
    op.drop_index("ix_agent_response_payloads_response_ref", table_name="agent_response_payloads")
    op.drop_table("agent_response_payloads")
    op.drop_index("ix_agent_graph_runs_thread_status", table_name="agent_graph_runs")
    op.drop_index("ix_agent_graph_runs_thread_id", table_name="agent_graph_runs")
    op.drop_index("ix_agent_graph_runs_response_ref", table_name="agent_graph_runs")
    op.drop_index("ix_agent_graph_runs_conversation_id", table_name="agent_graph_runs")
    op.drop_table("agent_graph_runs")
    op.drop_index("ix_agent_conversations_thread_id", table_name="agent_conversations")
    op.drop_column("agent_conversations", "thread_id")
