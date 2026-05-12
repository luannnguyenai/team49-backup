from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.routers.agent import agent_chat
from src.schemas.agent import AgentChatRequest
from src.services.model_registry import ChatModelUnavailableError


@pytest.mark.asyncio
async def test_agent_chat_rejects_unavailable_chat_model_before_invocation():
    with (
        patch(
            "src.routers.agent.ensure_chat_model_available",
            new=AsyncMock(
                side_effect=ChatModelUnavailableError(
                    model_id="qwen35_4b",
                    label="Qwen 3.5 4B",
                    status="down",
                )
            ),
        ),
        patch("src.routers.agent.AgentGraphService") as graph_service,
    ):
        with pytest.raises(HTTPException) as exc:
            await agent_chat(
                body=AgentChatRequest(message="Explain CNNs", chatModelId="qwen35_4b"),
                user=SimpleNamespace(id="user-1"),
                db=AsyncMock(),
            )

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "chat_model_unavailable"
    assert exc.value.detail["modelId"] == "qwen35_4b"
    graph_service.assert_not_called()
