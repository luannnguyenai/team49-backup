from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.agent import AgentAnswer, AgentChatRequest, AgentChatResponse
from src.services.agent_graph_contracts import AgentRouterUnavailableError, PendingClarification
from src.services.agent_graph_service import AgentGraphService
from src.services.guardrail_router import (
    GuardrailDecision,
    GuardrailRouterUnavailableError,
)
from src.services.language_normalization import LanguageNormalizationResult


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


class CapturingGuardrailRouter:
    def __init__(self):
        self.messages = []
        self.scopes = []

    async def route(self, *, message, scope):
        self.messages.append(message)
        self.scopes.append(scope)
        return GuardrailDecision.allow()


class FailingGraphRouter:
    def route(self, *args, **kwargs):
        raise RuntimeError("stop after guardrail")


class TranslatingLanguageNormalizer:
    async def normalize(self, text):
        return LanguageNormalizationResult(
            original_text=text,
            normalized_text="Explain attention mechanisms in neural networks.",
            detected_language="other",
            target_language="en",
            translated=True,
        )


class OutputTranslatingLanguageNormalizer:
    def detect(self, text):
        return "vi" if "Bạn muốn" in text else "en"

    @property
    def translator(self):
        return self

    async def translate_to_english(self, text):
        return "Would you like to narrow the topic?"


def test_agent_chat_request_limits_message_to_2000_chars():
    with pytest.raises(ValidationError):
        AgentChatRequest(message="x" * 2001)


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
    assert response.fallback.reason == "unsafe_action"
    assert "guardrail router" in response.fallback.message


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


@pytest.mark.asyncio
async def test_agent_chat_normalizes_third_language_before_guardrail():
    guardrail_router = CapturingGuardrailRouter()
    service = AgentGraphService(
        search_service=object(),
        requirement_service=object(),
        router=FailingGraphRouter(),
        guardrail_router=guardrail_router,
        language_normalizer=TranslatingLanguageNormalizer(),
    )

    with pytest.raises(RuntimeError, match="stop after guardrail"):
        await service.chat(
            request=AgentChatRequest(
                message="Explique les mécanismes d’attention dans les réseaux neuronaux.",
                incomingMessageId="msg-normalized-guardrail",
            ),
            conversation_id="conv-1",
            thread_id="thread-1",
            user_id="00000000-0000-0000-0000-000000000001",
            allowed_course_ids=["CS224n"],
        )

    assert guardrail_router.messages == ["Explain attention mechanisms in neural networks."]
    scope = guardrail_router.scopes[0]
    assert scope.allowed_scope_summary == "Agent guardrail scope: current user query only."
    assert scope.recent_context == []
    assert scope.candidate_kps == []


@pytest.mark.asyncio
async def test_agent_guardrail_scope_includes_pending_retrieval_topic_for_short_detail():
    guardrail_router = CapturingGuardrailRouter()
    conversation_id = uuid4()
    user_id = uuid4()
    pending = PendingClarification(
        clarification_id="clar-cnn",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={
            "kind": "retrieval_query",
            "original_intent": "find_content",
            "proposed_raw_topic": "CNN",
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(
            return_value=SimpleNamespace(
                summary_json={
                    "pendingClarification": {
                        "threadId": "thread-cnn",
                        "clarification": pending.model_dump(mode="json"),
                    }
                }
            )
        )
    )
    service = AgentGraphService(
        search_service=object(),
        requirement_service=object(),
        router=FailingGraphRouter(),
        guardrail_router=guardrail_router,
        conversation_repo=conversation_repo,
    )

    with pytest.raises(AgentRouterUnavailableError):
        await service.chat(
            request=AgentChatRequest(
                message="khái niệm tổng quan đi",
                incomingMessageId="msg-pending-guardrail",
            ),
            conversation_id=str(conversation_id),
            thread_id="thread-cnn",
            user_id=str(user_id),
            allowed_course_ids=["CS231n"],
        )

    scope = guardrail_router.scopes[0]
    assert "pending retrieval topic" in scope.allowed_scope_summary
    assert scope.recent_context == [
        {
            "type": "pending_retrieval_query",
            "proposed_raw_topic": "CNN",
            "original_intent": "find_content",
        }
    ]


@pytest.mark.asyncio
async def test_agent_chat_translates_non_english_output_for_english_target():
    service = AgentGraphService(
        search_service=object(),
        requirement_service=object(),
        router=FailingGraphRouter(),
        guardrail_router=CapturingGuardrailRouter(),
        language_normalizer=OutputTranslatingLanguageNormalizer(),
    )
    response = AgentChatResponse(
        conversation_id="conv-1",
        message_id="msg-1",
        answer=AgentAnswer(markdown="Bạn muốn thu hẹp chủ đề không?", confidence="partial"),
    )
    language = LanguageNormalizationResult(
        original_text="Explain attention.",
        normalized_text="Explain attention.",
        detected_language="en",
        target_language="en",
        translated=False,
    )

    updated = await service._enforce_response_language(response, language)

    assert updated.answer.markdown == "Would you like to narrow the topic?"
