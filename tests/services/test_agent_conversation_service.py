from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.agent_conversation_service import AgentConversationService


@pytest.mark.asyncio
async def test_conversation_service_replays_raw_json_and_datetime_fields():
    user_id = uuid4()
    conversation_id = uuid4()
    now = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)

    class Repo:
        async def get_conversation(self, requested_conversation_id, requested_user_id):
            assert requested_conversation_id == conversation_id
            assert requested_user_id == user_id
            return SimpleNamespace(id=conversation_id)

        async def list_messages(self, requested_conversation_id, requested_user_id):
            return [
                SimpleNamespace(
                    id=uuid4(),
                    role="assistant",
                    markdown="Open CNN basics.",
                    created_at=now,
                    citations_json=[{"canonicalUnitId": "unit-cnn", "title": "CNN basics"}],
                    actions_json=[{"type": "open_unit", "label": "Open unit"}],
                )
            ]

    messages = await AgentConversationService(Repo()).get_messages(conversation_id, user_id)

    assert messages[0].created_at == now
    assert messages[0].citations[0]["canonicalUnitId"] == "unit-cnn"
    assert messages[0].actions[0]["type"] == "open_unit"


@pytest.mark.asyncio
async def test_conversation_service_returns_empty_memory_when_not_summarized():
    user_id = uuid4()
    conversation_id = uuid4()

    class Repo:
        async def get_conversation(self, requested_conversation_id, requested_user_id):
            return SimpleNamespace(id=conversation_id, thread_id="thread-memory-empty")

        async def get_memory(self, requested_conversation_id, requested_user_id, thread_id=None):
            assert thread_id == "thread-memory-empty"
            return None

    memory = await AgentConversationService(Repo()).get_memory(conversation_id, user_id)

    assert memory.thread_id == "thread-memory-empty"
    assert memory.summary_status == "empty"
    assert memory.summary == {}


@pytest.mark.asyncio
async def test_conversation_service_returns_thread_scoped_memory():
    user_id = uuid4()
    conversation_id = uuid4()
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)

    class Repo:
        async def get_conversation(self, requested_conversation_id, requested_user_id):
            return SimpleNamespace(id=conversation_id, thread_id="thread-memory-fresh")

        async def get_memory(self, requested_conversation_id, requested_user_id, thread_id=None):
            assert thread_id == "thread-memory-fresh"
            return SimpleNamespace(
                thread_id="thread-memory-fresh",
                summary_status="fresh",
                recent_message_window=10,
                last_updated_at=now,
                summary_json={"memoryRef": "agent_memory:thread-memory-fresh:v1"},
            )

    memory = await AgentConversationService(Repo()).get_memory(conversation_id, user_id)

    assert memory.thread_id == "thread-memory-fresh"
    assert memory.summary["memoryRef"] == "agent_memory:thread-memory-fresh:v1"


@pytest.mark.asyncio
async def test_conversation_service_renames_conversation():
    user_id = uuid4()
    conversation_id = uuid4()
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)

    class Repo:
        async def rename_conversation(self, requested_conversation_id, requested_user_id, title):
            assert requested_conversation_id == conversation_id
            assert requested_user_id == user_id
            assert title == "YOLO follow-up"
            return SimpleNamespace(
                id=conversation_id,
                title=title,
                preview="old preview",
                updated_at=now,
                message_count=4,
            )

    summary = await AgentConversationService(Repo()).rename_conversation(
        conversation_id,
        user_id,
        " YOLO follow-up ",
    )

    assert summary.title == "YOLO follow-up"
    assert summary.message_count == 4


@pytest.mark.asyncio
async def test_conversation_service_clear_resets_thread_summary():
    user_id = uuid4()
    conversation_id = uuid4()
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)

    class Repo:
        async def clear_conversation(self, requested_conversation_id, requested_user_id):
            assert requested_conversation_id == conversation_id
            assert requested_user_id == user_id
            return SimpleNamespace(
                id=conversation_id,
                title="New chat",
                preview="",
                updated_at=now,
                message_count=0,
                thread_id="thread-new",
            )

    summary = await AgentConversationService(Repo()).clear_conversation(conversation_id, user_id)

    assert summary.title == "New chat"
    assert summary.preview == ""
    assert summary.message_count == 0


@pytest.mark.asyncio
async def test_conversation_service_clear_memory_returns_empty_summary():
    user_id = uuid4()
    conversation_id = uuid4()

    class Repo:
        async def clear_memory(self, requested_conversation_id, requested_user_id):
            assert requested_conversation_id == conversation_id
            assert requested_user_id == user_id
            return SimpleNamespace(
                thread_id="thread-cleared",
                summary_status="empty",
                recent_message_window=10,
                last_updated_at=None,
                summary_json={},
            )

    memory = await AgentConversationService(Repo()).clear_memory(conversation_id, user_id)

    assert memory.thread_id == "thread-cleared"
    assert memory.summary_status == "empty"
    assert memory.summary == {}
