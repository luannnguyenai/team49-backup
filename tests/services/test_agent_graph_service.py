from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.schemas.agent import (
    AgentActionResumeRequest,
    AgentAnswer,
    AgentChatRequest,
    AgentChatResponse,
    RetrievalTrace,
    UnitSearchResponse,
    UnitSearchResult,
)
from src.services.agent_graph_contracts import AgentInProgressError
from src.services.agent_graph_router import DeterministicAgentRouter
from src.services.agent_graph_service import AgentGraphService

pytestmark = pytest.mark.asyncio


class NoopLock:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return None


class NoopThreadLock:
    def acquire(self, **kwargs):
        return NoopLock()


async def test_graph_returns_grounded_find_content_from_search():
    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-attn",
                    course_id="CS224n",
                    unit_name="Attention",
                    summary="Attention content.",
                    score=3,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-1", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Tìm attention", incomingMessageId="msg-1"),
        conversation_id=str(uuid4()),
        thread_id="thread-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "grounded"
    assert response.citations[0].canonical_unit_id == "unit-attn"


async def test_graph_offers_scope_expansion_when_current_path_has_no_result():
    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-empty", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="attention mask ở đâu?", incomingMessageId="msg-scope-1"),
        conversation_id=str(uuid4()),
        thread_id="thread-scope-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "partial"
    assert response.warning is not None
    assert response.warning.type == "ambiguous_target"


async def test_graph_chat_returns_prior_response_for_completed_incoming_message():
    prior = AgentChatResponse(
        conversation_id="conv-1",
        message_id="assistant-1",
        answer=AgentAnswer(markdown="Prior answer", confidence="grounded"),
    )
    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=prior),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="retry", incomingMessageId="msg-dup"),
        conversation_id="conv-1",
        thread_id="thread-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
    )

    assert response == prior


async def test_graph_chat_active_run_returns_in_progress_before_invoking_graph():
    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="run-active")),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
    )

    with pytest.raises(AgentInProgressError) as exc_info:
        await service.chat(
            request=AgentChatRequest(message="new", incomingMessageId="msg-new"),
            conversation_id="conv-1",
            thread_id="thread-1",
            user_id=str(uuid4()),
            allowed_course_ids=["CS231n"],
        )

    assert exc_info.value.graph_run_id == "run-active"


async def test_graph_persists_pending_path_switch_action():
    class Router:
        def route(self, message, route_context):
            from src.services.agent_graph_contracts import AgentRoute, AgentSlots

            return AgentRoute(
                intent="request_path_switch",
                confidence=0.95,
                extracted_slots=AgentSlots(target_path="nlp"),
                rationale="switch path",
            )

    events = []
    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=None),
        create_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="run-1")),
        mark_run_running=AsyncMock(),
        create_pending_action=AsyncMock(return_value=SimpleNamespace(action_id="act-1")),
        store_response_payload=AsyncMock(return_value="resp-1"),
        mark_run_interrupted=AsyncMock(side_effect=lambda run_id, response_ref=None, checkpoint_id=None: events.append("interrupted")),
        mark_run_succeeded=AsyncMock(),
        mark_run_failed=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=Router(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Tôi muốn chuyển sang NLP", incomingMessageId="msg-path"),
        conversation_id=str(uuid4()),
        thread_id="thread-path",
        user_id=str(uuid4()),
        allowed_course_ids=["CS230", "CS224n", "CS231n"],
    )

    repo.create_pending_action.assert_awaited_once()
    assert response.actions[0].action_id == "act-1"
    assert events == ["interrupted"]


async def test_resume_reject_closes_interrupted_run_as_cancelled():
    conversation_id = str(uuid4())
    user_id = str(uuid4())
    pending = SimpleNamespace(
        action_id="act-reject",
        conversation_id=conversation_id,
        thread_id="thread-reject",
        user_id=user_id,
        status="awaiting_confirmation",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        type="request_replan",
        payload_json={},
        idempotency_key="idem-reject",
    )
    repo = SimpleNamespace(
        get_pending_action=AsyncMock(return_value=pending),
        mark_action_cancelled=AsyncMock(),
        mark_latest_interrupted_run_final=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
    )

    response = await service.resume_action(
        AgentActionResumeRequest(
            conversationId=conversation_id,
            actionId="act-reject",
            decision="reject",
        ),
        user_id=user_id,
    )

    assert response.answer.markdown == "Cancelled."
    repo.mark_action_cancelled.assert_awaited_once_with("act-reject")
    repo.mark_latest_interrupted_run_final.assert_awaited_once_with(
        thread_id="thread-reject",
        status="cancelled",
    )


async def test_resume_approve_closes_interrupted_run_as_succeeded():
    conversation_id = str(uuid4())
    user_id = str(uuid4())
    pending = SimpleNamespace(
        action_id="act-approve",
        conversation_id=conversation_id,
        thread_id="thread-approve",
        user_id=user_id,
        status="awaiting_confirmation",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        type="request_replan",
        payload_json={},
        idempotency_key="idem-approve",
    )
    repo = SimpleNamespace(
        get_pending_action=AsyncMock(return_value=pending),
        get_committed_action_result=AsyncMock(return_value=None),
        mark_action_committed=AsyncMock(),
        mark_latest_interrupted_run_final=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
    )

    response = await service.resume_action(
        AgentActionResumeRequest(
            conversationId=conversation_id,
            actionId="act-approve",
            decision="approve",
        ),
        user_id=user_id,
    )

    assert response.answer.markdown == "Action confirmed."
    repo.mark_action_committed.assert_awaited_once_with(
        "act-approve",
        result={"type": "request_replan", "status": "confirmed"},
    )
    repo.mark_latest_interrupted_run_final.assert_awaited_once_with(
        thread_id="thread-approve",
        status="succeeded",
    )
