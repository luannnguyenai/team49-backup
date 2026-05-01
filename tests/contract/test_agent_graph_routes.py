from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.schemas.agent import AgentAnswer, AgentChatResponse
from src.services.agent_graph_contracts import AgentInProgressError

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def _fake_checkpointer():
    yield SimpleNamespace(name="checkpointer")


async def _client_for_user(user_id):
    async def override_user():
        return SimpleNamespace(id=user_id)

    async def override_db():
        yield SimpleNamespace(commit=AsyncMock())

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_async_db] = override_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_agent_chat_returns_graph_response():
    user_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), thread_id="thread-1")
    graph_response = AgentChatResponse(
        conversation_id=str(conversation.id),
        message_id=str(uuid4()),
        answer=AgentAnswer(markdown="Graph answer", confidence="partial"),
    )

    with (
        patch(
            "src.routers.agent._agent_context_for_user",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    allowed_course_ids=["CS231n"],
                    selected_path_course_ids=["CS231n"],
                )
            ),
        ),
        patch("src.routers.agent.build_production_agent_router", return_value=SimpleNamespace()),
        patch("src.routers.agent.build_agent_graph_checkpointer", return_value=_fake_checkpointer()),
        patch("src.routers.agent.AgentConversationRepository") as conversation_repo_cls,
        patch("src.routers.agent.AgentGraphService") as service_cls,
    ):
        conversation_repo_cls.return_value.create_conversation = AsyncMock(return_value=conversation)
        service_cls.return_value.chat = AsyncMock(return_value=graph_response)
        client = await _client_for_user(user_id)
        try:
            response = await client.post(
                "/api/agent/chat",
                json={"message": "ok", "incomingMessageId": "msg-1"},
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"]["markdown"] == "Graph answer"
    assert service_cls.call_args.kwargs["checkpointer"].name == "checkpointer"


async def test_agent_chat_returns_409_in_progress_payload():
    user_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), thread_id="thread-1")

    with (
        patch(
            "src.routers.agent._agent_context_for_user",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    allowed_course_ids=["CS231n"],
                    selected_path_course_ids=["CS231n"],
                )
            ),
        ),
        patch("src.routers.agent.build_production_agent_router", return_value=SimpleNamespace()),
        patch("src.routers.agent.build_agent_graph_checkpointer", return_value=_fake_checkpointer()),
        patch("src.routers.agent.AgentConversationRepository") as conversation_repo_cls,
        patch("src.routers.agent.AgentGraphService") as service_cls,
    ):
        conversation_repo_cls.return_value.create_conversation = AsyncMock(return_value=conversation)
        service_cls.return_value.chat = AsyncMock(
            side_effect=AgentInProgressError("conv-1", "thread-1", "run-1", 1000)
        )
        client = await _client_for_user(user_id)
        try:
            response = await client.post(
                "/api/agent/chat",
                json={"message": "ok", "incomingMessageId": "msg-2"},
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "status": "in_progress",
        "conversationId": "conv-1",
        "threadId": "thread-1",
        "graphRunId": "run-1",
        "retryAfterMs": 1000,
    }


async def test_agent_chat_returns_safe_error_response_for_unhandled_failure():
    user_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), thread_id="thread-1")
    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

    async def override_user():
        return SimpleNamespace(id=user_id)

    async def override_db():
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_async_db] = override_db

    with (
        patch(
            "src.routers.agent._agent_context_for_user",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    allowed_course_ids=["CS231n"],
                    selected_path_course_ids=["CS231n"],
                )
            ),
        ),
        patch("src.routers.agent.build_production_agent_router", return_value=SimpleNamespace()),
        patch("src.routers.agent.build_agent_graph_checkpointer", return_value=_fake_checkpointer()),
        patch("src.routers.agent.AgentConversationRepository") as conversation_repo_cls,
        patch("src.routers.agent.AgentGraphService") as service_cls,
    ):
        conversation_repo_cls.return_value.create_conversation = AsyncMock(return_value=conversation)
        service_cls.return_value.chat = AsyncMock(side_effect=RuntimeError("boom"))
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        try:
            response = await client.post(
                "/api/agent/chat",
                json={"message": "ok", "incomingMessageId": "msg-error"},
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["answer"]["confidence"] == "fallback"
    assert "system incident" in body["answer"]["markdown"]
    assert body["fallback"]["errorCode"] == "AGENT_CHAT_ERROR"
    db.rollback.assert_awaited_once()


async def test_agent_action_continue_uses_durable_checkpointer():
    user_id = uuid4()
    graph_response = AgentChatResponse(
        conversation_id="conv-1",
        message_id=str(uuid4()),
        answer=AgentAnswer(markdown="Continued", confidence="partial"),
    )

    with (
        patch("src.routers.agent.build_production_agent_router", return_value=SimpleNamespace()),
        patch("src.routers.agent.build_agent_graph_checkpointer", return_value=_fake_checkpointer()),
        patch("src.routers.agent.AgentGraphService") as service_cls,
    ):
        service_cls.return_value.resume_action = AsyncMock(return_value=graph_response)
        client = await _client_for_user(user_id)
        try:
            response = await client.post(
                "/api/agent/actions/continue",
                json={
                    "conversationId": "conv-1",
                    "actionId": "act-1",
                    "decision": "approve",
                    "incomingMessageId": "msg-continue-1",
                },
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"]["markdown"] == "Continued"
    assert service_cls.call_args.kwargs["checkpointer"].name == "checkpointer"
