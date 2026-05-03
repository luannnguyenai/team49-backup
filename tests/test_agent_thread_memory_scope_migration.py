from pathlib import Path


MIGRATION = Path("alembic/versions/20260502_thread_memory_scope.py")


def test_agent_thread_memory_scope_migration_backfills_thread_id():
    text = MIGRATION.read_text()

    assert 'op.add_column(\n        "agent_conversation_memories"' in text
    assert "SET thread_id = conversation.thread_id" in text
    assert 'op.alter_column("agent_conversation_memories", "thread_id", nullable=False)' in text
    assert '"ix_agent_conversation_memories_thread_id"' in text
    assert "unique=True" in text


def test_agent_thread_memory_scope_migration_downgrades_thread_id():
    text = MIGRATION.read_text()

    assert 'op.drop_index("ix_agent_conversation_memories_thread_id"' in text
    assert 'op.drop_column("agent_conversation_memories", "thread_id")' in text
