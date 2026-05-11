from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.routers import agent as agent_router_module


@pytest.mark.asyncio
async def test_agent_title_generation_uses_sanitized_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    class StubConversationRepo:
        async def get_conversation(self, conversation_id, user_id):
            return SimpleNamespace(
                message_count=2,
                title="New chat",
            )

        async def rename_conversation(self, conversation_id, user_id, title):
            captured["renamed_title"] = title

    async def fake_generate_conversation_title(user_message: str, assistant_markdown: str) -> str:
        captured["user_message"] = user_message
        captured["assistant_markdown"] = assistant_markdown
        return "Safe title"

    monkeypatch.setattr(agent_router_module, "generate_conversation_title", fake_generate_conversation_title)

    await agent_router_module._maybe_generate_conversation_title(
        conversation_repo=StubConversationRepo(),
        conversation_id=uuid4(),
        user=SimpleNamespace(id=uuid4()),
        user_message="Email me at alice@example.com",
        assistant_markdown="Call me at 555-123-4567",
    )

    assert captured["user_message"] == "Email me at [REDACTED_EMAIL]"
    assert captured["assistant_markdown"] == "Call me at [REDACTED_PHONE]"
    assert captured["renamed_title"] == "Safe title"
