import pytest

from src.schemas.agent import AgentChatRequest
from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_graph_service import AgentGraphService
from src.services.guardrail_router import (
    GuardrailDecision,
    GuardrailRouterUnavailableError,
)


class FailingAgentRouter:
    def route(self, *args, **kwargs):
        raise AssertionError("StructuredAgentRouter must not run for blocked guardrail decisions")


class BlockingGuardrailRouter:
    async def route(self, *, message, scope):
        return GuardrailDecision(
            safety_label="SAFE",
            topic_label="OFF_TOPIC",
            action="SOFT_REFUSE_REDIRECT",
            attack_type="none",
            selected_kp_ids=[],
        )


class FailingGuardrailRouter:
    async def route(self, *, message, scope):
        raise GuardrailRouterUnavailableError()


@pytest.mark.asyncio
async def test_agent_chat_returns_guardrail_response_before_structured_router():
    service = AgentGraphService(
        search_service=object(),
        requirement_service=object(),
        router=FailingAgentRouter(),
        guardrail_router=BlockingGuardrailRouter(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="What's the weather?", incomingMessageId="msg-guardrail"),
        conversation_id="conv-1",
        thread_id="thread-1",
        user_id="00000000-0000-0000-0000-000000000001",
        allowed_course_ids=["CS224n"],
    )

    assert response.answer.markdown == (
        "That question is outside the current lesson scope. Please ask about the current lesson."
    )
    assert response.guardrail is not None
    assert response.guardrail.blocked is True
    assert response.guardrail.block_reason == "SOFT_REFUSE_REDIRECT"
    assert response.guardrail.error_code is None
    assert response.fallback is not None
    assert response.fallback.reason == "guardrail_router"


@pytest.mark.asyncio
async def test_agent_chat_maps_guardrail_outage_to_router_unavailable():
    service = AgentGraphService(
        search_service=object(),
        requirement_service=object(),
        router=FailingAgentRouter(),
        guardrail_router=FailingGuardrailRouter(),
    )

    with pytest.raises(AgentRouterUnavailableError) as exc:
        await service.chat(
            request=AgentChatRequest(message="Explain attention.", incomingMessageId="msg-guardrail"),
            conversation_id="conv-1",
            thread_id="thread-1",
            user_id="00000000-0000-0000-0000-000000000001",
            allowed_course_ids=["CS224n"],
        )

    assert exc.value.error_code == "GUARDRAIL_ROUTER_UNAVAILABLE"
