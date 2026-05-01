from pathlib import Path


MIGRATION = Path("alembic/versions/20260501_agent_graph_runtime.py")


def test_agent_graph_runtime_migration_backfills_thread_id_and_tables():
    text = MIGRATION.read_text()

    assert "UPDATE agent_conversations SET thread_id" in text
    assert 'op.alter_column("agent_conversations", "thread_id", nullable=False)' in text
    assert 'op.create_index(\n        "ix_agent_conversations_thread_id"' in text
    assert '"agent_graph_runs"' in text
    assert '"agent_pending_actions"' in text
    assert '"agent_response_payloads"' in text
    assert '"agent_trace_events"' in text
    assert "uq_agent_graph_run_message" in text
    assert '"idempotency_key"' in text


def test_agent_graph_runtime_migration_downgrades_runtime_tables():
    text = MIGRATION.read_text()

    assert 'op.drop_table("agent_trace_events")' in text
    assert 'op.drop_table("agent_pending_actions")' in text
    assert 'op.drop_table("agent_response_payloads")' in text
    assert 'op.drop_table("agent_graph_runs")' in text
    assert 'op.drop_column("agent_conversations", "thread_id")' in text
