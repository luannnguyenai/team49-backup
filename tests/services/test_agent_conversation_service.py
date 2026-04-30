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
            return SimpleNamespace(id=conversation_id)

        async def get_memory(self, requested_conversation_id, requested_user_id):
            return None

    memory = await AgentConversationService(Repo()).get_memory(conversation_id, user_id)

    assert memory.summary_status == "empty"
    assert memory.summary == {}
