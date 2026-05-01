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
from src.services.agent_graph_contracts import AgentRoute, AgentSlots, PendingClarification
from src.services.agent_graph_contracts import AgentInProgressError, AgentRouterUnavailableError
from src.services.agent_graph_router import DeterministicAgentRouter
from src.services.agent_graph_service import AgentGraphService
from src.services.agent_memory_compaction_service import AgentMemoryCompactionService

pytestmark = pytest.mark.asyncio


class NoopLock:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return None


class NoopThreadLock:
    def acquire(self, **kwargs):
        return NoopLock()


class PendingDecisionRouter:
    def __init__(
        self,
        *,
        action: str = "approve",
        refined_query: str | None = None,
        clarification_question: str | None = None,
        grounded_answer: str = "Pending follow-up answer.",
        evidence_sufficient: bool = True,
        confidence: str = "grounded",
    ):
        self.action = action
        self.refined_query = refined_query
        self.clarification_question = clarification_question
        self.grounded_answer = grounded_answer
        self.evidence_sufficient = evidence_sufficient
        self.confidence = confidence

    def resolve_pending_followup(self, message, pending_payload, route_context):
        return SimpleNamespace(
            action=self.action,
            refined_query=self.refined_query,
            clarification_question=self.clarification_question,
        )

    def compose_grounded_answer(self, message, citations):
        return SimpleNamespace(
            answer_markdown=self.grounded_answer,
            evidence_sufficient=self.evidence_sufficient,
            confidence=self.confidence,
            clarification_question=None,
        )


async def test_graph_returns_grounded_find_content_from_search():
    class Router(DeterministicAgentRouter):
        def compose_grounded_answer(self, message, citations):
            return f"LLM grounded answer for {citations[0]['unit_name']}"

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-attn",
                    course_id="CS224n",
                    unit_name="Attention",
                    summary="Attention content.",
                    learn_href="/courses/cs224n/learn/attention",
                    score=3,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(
                trace_id="trace-1",
                intent="find_content",
                selected_path="current_path",
                candidate_courses=["CS224n"],
                ranking_version="unit_search_v1",
            ),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Tìm attention", incomingMessageId="msg-1"),
        conversation_id=str(uuid4()),
        thread_id="thread-1",
        user_id=str(uuid4()),
        allowed_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "grounded"
    assert response.answer.markdown == "LLM grounded answer for Attention"
    assert response.citations[0].canonical_unit_id == "unit-attn"
    assert response.actions[0].type == "open_unit"
    assert response.trace is not None
    assert response.trace.trace_id == "trace-1"
    assert response.trace.selected_path == "current_path"
    assert response.trace.selected_unit_ids == ["unit-attn"]


async def test_graph_dispatches_navigation_intent_to_content_search():
    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="navigate_to_unit",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="CNNs"),
            )

        def compose_grounded_answer(self, message, citations):
            return "Review the CNN unit."

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-cnn",
                    course_id="CS231n",
                    unit_name="Convolutional Neural Networks",
                    summary="CNN content.",
                    score=3,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-cnn", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Where should I review CNNs?", incomingMessageId="msg-nav"),
        conversation_id=str(uuid4()),
        thread_id="thread-nav",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
    )

    assert response.answer.markdown == "Review the CNN unit."
    assert response.answer.confidence == "partial"
    assert response.citations[0].canonical_unit_id == "unit-cnn"


async def test_graph_downgrades_grounded_answer_when_llm_rejects_evidence():
    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="explain_concept",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="attention mask in transformers"),
            )

        def compose_grounded_answer(self, message, citations):
            return SimpleNamespace(
                answer_markdown="I do not have enough evidence for that topic.",
                evidence_sufficient=False,
                confidence="no_source",
                clarification_question="Which masking behavior do you mean?",
            )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-overview",
                    course_id="CS230",
                    unit_name="Course Overview",
                    summary="Deep learning overview.",
                    score=1,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-weak", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(
            message="attention mask in transformers",
            incomingMessageId="msg-weak-grounding",
        ),
        conversation_id=str(uuid4()),
        thread_id="thread-weak-grounding",
        user_id=str(uuid4()),
        allowed_course_ids=["CS230"],
    )

    assert response.answer.confidence == "no_source"
    assert response.citations == []
    assert response.fallback is not None


async def test_graph_lets_llm_review_related_evidence_as_partial_context():
    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="cnn object detection"),
            )

        def compose_grounded_answer(self, message, citations):
            return SimpleNamespace(
                answer_markdown="I only found related detection context.",
                evidence_sufficient=False,
                confidence="partial",
                clarification_question=None,
            )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-related-cnn",
                    course_id="CS231n",
                    unit_name="Visual recognition project examples",
                    summary="Mentions CNNs and detection datasets at a high level.",
                    score=1,
                    quiz_available=True,
                    learn_href="/courses/cs231n/learn/related-cnn",
                )
            ],
            trace=RetrievalTrace(trace_id="trace-related-quality", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Where should I review cnn object detection?", incomingMessageId="msg-related-quality"),
        conversation_id=str(uuid4()),
        thread_id="thread-related-quality",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "partial"
    assert response.answer.markdown == "I only found related detection context."
    assert response.citations[0].canonical_unit_id == "unit-related-cnn"
    assert response.actions[0].type == "open_unit"


async def test_graph_offers_scope_expansion_when_current_path_evidence_is_weak():
    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="CNNs"),
            )

        def compose_grounded_answer(self, message, citations):
            return SimpleNamespace(
                answer_markdown="The current-path evidence is not direct enough.",
                evidence_sufficient=False,
                confidence="no_source",
                clarification_question="The current path did not have a direct CNN match. Search other paths?",
            )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-weak",
                    course_id="CS224n",
                    unit_name="Neural Network Overview",
                    summary="General neural network content.",
                    score=1,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-weak-current", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Where should I review CNNs?", incomingMessageId="msg-weak-current"),
        conversation_id=str(uuid4()),
        thread_id="thread-weak-current",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "partial"
    assert "current path" in response.answer.markdown
    assert response.citations == []
    assert response.actions == []


async def test_scope_expansion_approval_searches_other_path_directly_when_fewer_than_three_paths_match():
    conversation_id = uuid4()
    user_id = uuid4()
    pending = PendingClarification(
        clarification_id="clar-path-catalog",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={
            "original_message": "Where should I review CNNs?",
            "raw_topic": "CNNs",
            "allowed_path_ids": ["computer_vision", "nlp"],
            "current_path_ids": ["nlp"],
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-cv-cnn",
                    course_id="CS231n",
                    unit_name="CNNs for Vision",
                    summary="Computer vision CNN content.",
                    score=3,
                    quiz_available=True,
                    learn_href="/courses/cs231n/learn/cnn-vision",
                ),
                UnitSearchResult(
                    canonical_unit_id="unit-nlp-cnn",
                    course_id="CS224n",
                    unit_name="CNNs for Sentence Classification",
                    summary="NLP CNN content.",
                    score=3,
                    quiz_available=True,
                    learn_href="/courses/cs224n/learn/cnn-text",
                ),
            ],
            trace=RetrievalTrace(trace_id="trace-path-catalog", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-path-catalog",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(
            action="approve",
            grounded_answer="I found related CNN results in another path.",
            evidence_sufficient=False,
            confidence="partial",
        ),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="yes, search other paths", incomingMessageId="msg-path-catalog"),
        conversation_id=str(conversation_id),
        thread_id="thread-path-catalog",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "partial"
    assert {citation.course_id for citation in response.citations} == {"CS231n"}
    assert {action.type for action in response.actions} == {"open_unit"}


async def test_expanded_search_with_too_many_results_asks_to_refine_or_show_top_results():
    conversation_id = uuid4()
    user_id = uuid4()
    pending = PendingClarification(
        clarification_id="clar-too-many",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={
            "original_message": "Where should I review CNN?",
            "raw_topic": "CNN",
            "allowed_path_ids": ["computer_vision", "nlp"],
            "current_path_ids": ["nlp"],
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id=f"unit-cnn-{index}",
                    course_id="CS231n",
                    unit_name=f"CNN result {index}",
                    summary="CNN content.",
                    score=3,
                    quiz_available=True,
                    learn_href=f"/courses/cs231n/learn/cnn-{index}",
                )
                for index in range(30)
            ],
            trace=RetrievalTrace(trace_id="trace-too-many", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-too-many",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="approve", evidence_sufficient=False, confidence="partial"),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="yes, search other paths", incomingMessageId="msg-too-many"),
        conversation_id=str(conversation_id),
        thread_id="thread-too-many",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "partial"
    assert "30 results" in response.answer.markdown
    assert response.citations == []
    persisted = conversation_repo.upsert_memory.await_args.kwargs["summary_json"]["pendingClarification"]
    assert persisted["clarification"]["payload"]["kind"] == "retrieval_query"
    assert persisted["clarification"]["payload"]["original_intent"] == "find_content"
    assert persisted["clarification"]["payload"]["show_top_results_allowed"] is True


async def test_expanded_search_without_results_returns_no_source_not_generic_clarify():
    conversation_id = uuid4()
    user_id = uuid4()
    pending = PendingClarification(
        clarification_id="clar-expanded-empty",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={
            "original_message": "Where should I review dependency parsing?",
            "raw_topic": "dependency parsing",
            "allowed_path_ids": ["computer_vision", "nlp"],
            "current_path_ids": ["computer_vision"],
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-expanded-empty-source", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-expanded-empty-source",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="approve"),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="yes, search other paths", incomingMessageId="msg-expanded-empty-source"),
        conversation_id=str(conversation_id),
        thread_id="thread-expanded-empty-source",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "no_source"
    assert "grounded source" in response.answer.markdown
    assert response.fallback is not None


async def test_current_path_search_with_too_many_results_asks_to_refine_or_show_top_results():
    conversation_id = uuid4()
    user_id = uuid4()

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="CNN"),
            )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id=f"unit-current-cnn-{index}",
                    course_id="CS231n",
                    unit_name=f"Current CNN result {index}",
                    summary="CNN content.",
                    score=3,
                    quiz_available=True,
                    learn_href=f"/courses/cs231n/learn/current-cnn-{index}",
                )
                for index in range(30)
            ],
            trace=RetrievalTrace(trace_id="trace-current-too-many", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={"memoryRef": f"agent_memory:{conversation_id}:v1", "summaryVersion": 1},
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="Where should I review CNN?", incomingMessageId="msg-current-too-many"),
        conversation_id=str(conversation_id),
        thread_id="thread-current-too-many",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "partial"
    assert "30 results" in response.answer.markdown
    assert response.citations == []
    persisted = conversation_repo.upsert_memory.await_args.kwargs["summary_json"]["pendingClarification"]
    assert persisted["clarification"]["payload"]["search_scope"] == "current_path"
    assert persisted["clarification"]["payload"]["show_top_results_allowed"] is True


async def test_direct_evidence_is_returned_even_when_search_page_is_full():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="U-Net", search_queries=["UNet", "U-Net segmentation"]),
            )

        def compose_grounded_answer(self, message, citations):
            return SimpleNamespace(
                answer_markdown="U-Net appears in the segmentation unit.",
                evidence_sufficient=True,
                confidence="grounded",
                clarification_question=None,
            )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-unet",
                    course_id="CS231n",
                    unit_name="Semantic segmentation from per-pixel labeling to U-Net",
                    summary="U-Net content.",
                    score=3,
                    quiz_available=True,
                    learn_href="/courses/cs231n/learn/u-net",
                ),
                *[
                    UnitSearchResult(
                        canonical_unit_id=f"unit-broad-{index}",
                        course_id="CS231n",
                        unit_name=f"Broad segmentation result {index}",
                        summary="General segmentation content.",
                        score=1,
                        quiz_available=True,
                        learn_href=f"/courses/cs231n/learn/broad-{index}",
                    )
                    for index in range(29)
                ],
            ],
            trace=RetrievalTrace(trace_id="trace-unet-full", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={"memoryRef": f"agent_memory:{conversation_id}:v1", "summaryVersion": 1},
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="Tìm thông tin về UNet", incomingMessageId="msg-unet-direct"),
        conversation_id=str(conversation_id),
        thread_id="thread-unet-direct",
        user_id=str(user_id),
        allowed_course_ids=["CS231n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "grounded"
    assert [request.query for request in search_requests] == ["UNet", "U-Net segmentation"]
    assert response.citations[0].canonical_unit_id == "unit-unet"
    assert "20 results" not in response.answer.markdown


async def test_direct_evidence_buried_under_broad_search_results_is_returned():
    conversation_id = uuid4()
    user_id = uuid4()

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(
                    raw_topic="YOLO",
                    search_queries=[
                        "YOLO object detection",
                        "YOLO architecture grid prediction",
                        "YOLO loss function bounding box",
                    ],
                ),
            )

        def compose_grounded_answer(self, message, citations):
            return SimpleNamespace(
                answer_markdown="YOLO is covered in the single-stage detector unit.",
                evidence_sufficient=True,
                confidence="grounded",
                clarification_question=None,
            )

    async def search(request, allowed_course_ids):
        broad_results = [
            UnitSearchResult(
                canonical_unit_id=f"unit-broad-{request.query}-{index}",
                course_id="CS231n",
                unit_name=f"Generic detection result {index}",
                summary="This overlaps broad search terms but is not the requested topic.",
                score=4,
                quiz_available=True,
                learn_href=f"/courses/cs231n/learn/broad-{index}",
            )
            for index in range(20)
        ]
        yolo_result = UnitSearchResult(
            canonical_unit_id="unit-yolo",
            course_id="CS231n",
            unit_name="Single-stage and transformer detectors: YOLO and DETR",
            summary="YOLO is the canonical single-stage detector example.",
            score=1,
            quiz_available=True,
            learn_href="/courses/cs231n/learn/yolo",
        )
        return UnitSearchResponse(
            results=[*broad_results, yolo_result],
            trace=RetrievalTrace(trace_id="trace-yolo-broad", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="tìm thông tin về YOLO", incomingMessageId="msg-yolo-buried"),
        conversation_id=str(conversation_id),
        thread_id="thread-yolo-buried",
        user_id=str(user_id),
        allowed_course_ids=["CS231n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "grounded"
    assert response.citations[0].canonical_unit_id == "unit-yolo"
    assert "results related" not in response.answer.markdown


async def test_too_many_results_approval_shows_top_results_without_requerying_router():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    pending = PendingClarification(
        clarification_id="clar-too-many-top",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={
            "kind": "retrieval_query",
            "original_intent": "find_content",
            "original_message": "Where should I review CNN?",
            "proposed_raw_topic": "CNN",
            "search_scope": "expanded_paths",
            "resolved_search_path_ids": ["computer_vision", "nlp"],
            "excluded_search_path_ids": ["nlp"],
            "show_top_results_allowed": True,
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id=f"unit-cnn-top-{index}",
                    course_id="CS231n",
                    unit_name=f"CNN top result {index}",
                    summary="CNN content.",
                    score=3,
                    quiz_available=True,
                    learn_href=f"/courses/cs231n/learn/cnn-top-{index}",
                )
                for index in range(30)
            ],
            trace=RetrievalTrace(trace_id="trace-too-many-top", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-too-many-top",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(
            action="approve",
            grounded_answer="Here are the top related results.",
            evidence_sufficient=False,
            confidence="partial",
        ),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="show top results", incomingMessageId="msg-too-many-top"),
        conversation_id=str(conversation_id),
        thread_id="thread-too-many-top",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "partial"
    assert len(response.citations) == 3
    assert len(response.actions) == 3
    assert search_requests[0].query == "CNN"


async def test_too_many_results_approval_uses_structured_followup_not_message_as_query():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    pending = PendingClarification(
        clarification_id="clar-too-many-typo-top",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={
            "kind": "retrieval_query",
            "original_intent": "find_content",
            "proposed_raw_topic": "U-Net",
            "search_scope": "current_path",
            "resolved_search_path_ids": ["computer_vision"],
            "show_top_results_allowed": True,
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    class Router:
        def resolve_pending_followup(self, message, pending_payload, route_context):
            assert message == "top réult"
            return SimpleNamespace(
                action="approve",
                refined_query=None,
                clarification_question=None,
            )

        def compose_grounded_answer(self, message, citations):
            return SimpleNamespace(
                answer_markdown="Here are the top U-Net results.",
                evidence_sufficient=False,
                confidence="partial",
                clarification_question=None,
            )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-unet",
                    course_id="CS231n",
                    unit_name="Semantic segmentation from per-pixel labeling to U-Net",
                    summary="U-Net segmentation content.",
                    score=3,
                    quiz_available=True,
                    learn_href="/courses/cs231n/learn/u-net",
                )
            ],
            trace=RetrievalTrace(trace_id="trace-unet-top", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-too-many-typo-top",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="top réult", incomingMessageId="msg-too-many-typo-top"),
        conversation_id=str(conversation_id),
        thread_id="thread-too-many-typo-top",
        user_id=str(user_id),
        allowed_course_ids=["CS231n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "partial"
    assert search_requests[0].query == "U-Net"
    assert "top réult" not in search_requests[0].query


async def test_too_many_results_user_detail_refines_original_query():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    pending = PendingClarification(
        clarification_id="clar-too-many-refine",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={
            "kind": "retrieval_query",
            "original_intent": "find_content",
            "proposed_raw_topic": "CNN",
            "search_scope": "expanded_paths",
            "resolved_search_path_ids": ["computer_vision", "nlp"],
            "excluded_search_path_ids": ["nlp"],
            "show_top_results_allowed": True,
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-cnn-detection",
                    course_id="CS231n",
                    unit_name="CNN object detection",
                    summary="CNN detection content.",
                    score=4,
                    quiz_available=True,
                    learn_href="/courses/cs231n/learn/cnn-detection",
                )
            ],
            trace=RetrievalTrace(trace_id="trace-too-many-refine", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-too-many-refine",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(
            action="refine",
            refined_query="CNN object detection",
            grounded_answer="I found detection-specific CNN results.",
            evidence_sufficient=True,
            confidence="grounded",
        ),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="object detection", incomingMessageId="msg-too-many-refine"),
        conversation_id=str(conversation_id),
        thread_id="thread-too-many-refine",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "grounded"
    assert search_requests[0].query == "CNN object detection"


async def test_path_choice_action_searches_selected_path_with_original_topic():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    pending = PendingClarification(
        clarification_id="clar-path-select",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={
            "kind": "path_selection",
            "original_intent": "find_content",
            "original_message": "Where should I review CNNs?",
            "raw_topic": "CNNs",
            "path_options": ["computer_vision", "nlp"],
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-cv-cnn",
                    course_id="CS231n",
                    unit_name="CNNs for Vision",
                    summary="Computer vision CNN content.",
                    score=3,
                    quiz_available=True,
                    learn_href="/courses/cs231n/learn/cnn",
                ),
            ],
            trace=RetrievalTrace(trace_id="trace-path-select", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-path-select",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="approve"),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="choose_path:computer_vision", incomingMessageId="msg-path-select"),
        conversation_id=str(conversation_id),
        thread_id="thread-path-select",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "grounded"
    assert search_requests[0].query == "CNNs"
    assert search_requests[0].course_ids == ["CS231n"]
    assert response.actions[0].type == "open_unit"


async def test_selected_path_with_related_but_weak_evidence_keeps_result_cards_as_partial():
    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=1.0,
                extracted_slots=AgentSlots(
                    raw_topic="CNNs",
                    target_path="computer_vision",
                    requested_path_id="computer_vision",
                    search_scope="explicit_path",
                    resolved_search_path_ids=["computer_vision"],
                ),
            )

        def compose_grounded_answer(self, message, citations):
            return SimpleNamespace(
                answer_markdown="I only found related CNN results, not an exact match.",
                evidence_sufficient=False,
                confidence="partial",
                clarification_question=None,
            )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-cv-related",
                    course_id="CS231n",
                    unit_name="CNN applications",
                    summary="Related CNN application content.",
                    score=3,
                    quiz_available=True,
                    learn_href="/courses/cs231n/learn/cnn-applications",
                ),
            ],
            trace=RetrievalTrace(trace_id="trace-related", ranking_version="unit_search_v1"),
        )

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="choose_path:computer_vision", incomingMessageId="msg-related"),
        conversation_id=str(uuid4()),
        thread_id="thread-related",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "partial"
    assert "related CNN results" in response.answer.markdown
    assert response.citations[0].canonical_unit_id == "unit-cv-related"
    assert response.actions[0].type == "open_unit"


async def test_content_intent_without_extracted_topic_clarifies_before_search():
    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic=None),
                clarification_question="Which topic should I search for?",
            )

    async def search(request, allowed_course_ids):
        raise AssertionError("Graph must clarify before retrieval when raw_topic is missing")

    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
    )

    response = await service.chat(
        request=AgentChatRequest(message="Where should I review?", incomingMessageId="msg-missing-topic"),
        conversation_id=str(uuid4()),
        thread_id="thread-missing-topic",
        user_id=str(uuid4()),
        allowed_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "partial"
    assert response.answer.markdown == "Which topic should I search for?"


async def test_missing_retrieval_topic_persists_pending_query_clarification():
    conversation_id = uuid4()
    user_id = uuid4()

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic=None),
                clarification_question="Which topic should I search for?",
            )

    async def search(request, allowed_course_ids):
        raise AssertionError("Graph must not retrieve before query clarification")

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={"memoryRef": f"agent_memory:{conversation_id}:v1", "summaryVersion": 1},
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
        conversation_repo=conversation_repo,
    )

    await service.chat(
        request=AgentChatRequest(message="Where should I review?", incomingMessageId="msg-query-clarify"),
        conversation_id=str(conversation_id),
        thread_id="thread-query-clarify",
        user_id=str(user_id),
        allowed_course_ids=["CS231n"],
    )

    pending = conversation_repo.upsert_memory.await_args.kwargs["summary_json"]["pendingClarification"]
    assert pending["threadId"] == "thread-query-clarify"
    assert pending["clarification"]["type"] == "slot_disambiguation"
    assert pending["clarification"]["payload"]["kind"] == "retrieval_query"
    assert pending["clarification"]["payload"]["original_intent"] == "find_content"


async def test_pending_retrieval_query_confirmation_uses_proposed_topic():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    pending = PendingClarification(
        clarification_id="clar-query",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={
            "kind": "retrieval_query",
            "original_intent": "find_content",
            "proposed_raw_topic": "dependency parsing",
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-dep",
                    course_id="CS224n",
                    unit_name="Dependency Parsing",
                    summary="Dependency parsing content.",
                    score=3,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-dep", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-query-confirm",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    upserts = []
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(side_effect=lambda **kwargs: upserts.append(kwargs)),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="approve"),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="yes", incomingMessageId="msg-query-confirm"),
        conversation_id=str(conversation_id),
        thread_id="thread-query-confirm",
        user_id=str(user_id),
        allowed_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "grounded"
    assert search_requests[0].query == "dependency parsing"
    assert upserts[-1]["summary_json"].get("pendingClarification") is None


async def test_pending_retrieval_query_user_detail_becomes_search_topic():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    pending = PendingClarification(
        clarification_id="clar-query-detail",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={"kind": "retrieval_query", "original_intent": "find_content"},
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-mask",
                    course_id="CS224n",
                    unit_name="Attention Mask",
                    summary="Attention mask content.",
                    score=3,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-mask", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-query-detail",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="refine", refined_query="attention mask in transformers"),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(
            message="attention mask in transformers",
            incomingMessageId="msg-query-detail",
        ),
        conversation_id=str(conversation_id),
        thread_id="thread-query-detail",
        user_id=str(user_id),
        allowed_course_ids=["CS224n"],
    )

    assert response.answer.confidence == "grounded"
    assert search_requests[0].query == "attention mask in transformers"


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


async def test_scope_expansion_pending_clarification_persists_to_thread_memory():
    conversation_id = uuid4()
    user_id = uuid4()

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-empty", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={"memoryRef": f"agent_memory:{conversation_id}:v1", "summaryVersion": 1},
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        conversation_repo=conversation_repo,
    )

    await service.chat(
        request=AgentChatRequest(message="attention mask ở đâu?", incomingMessageId="msg-scope-save"),
        conversation_id=str(conversation_id),
        thread_id="thread-scope-save",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    summary = conversation_repo.upsert_memory.await_args.kwargs["summary_json"]
    pending = summary["pendingClarification"]
    assert summary["memoryRef"] == f"agent_memory:{conversation_id}:v1"
    assert pending["threadId"] == "thread-scope-save"
    assert pending["clarification"]["type"] == "search_scope_expansion"
    assert pending["clarification"]["payload"]["original_message"] == "attention mask ở đâu?"


async def test_scope_expansion_pending_clarification_stores_extracted_raw_topic():
    conversation_id = uuid4()
    user_id = uuid4()

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="dependency parsing"),
            )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-empty-topic", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={"memoryRef": f"agent_memory:{conversation_id}:v1", "summaryVersion": 1},
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
        conversation_repo=conversation_repo,
    )

    await service.chat(
        request=AgentChatRequest(
            message="Where should I review dependency parsing?",
            incomingMessageId="msg-scope-topic",
        ),
        conversation_id=str(conversation_id),
        thread_id="thread-scope-topic",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    pending = conversation_repo.upsert_memory.await_args.kwargs["summary_json"]["pendingClarification"]
    assert pending["clarification"]["payload"]["original_message"] == "Where should I review dependency parsing?"
    assert pending["clarification"]["payload"]["raw_topic"] == "dependency parsing"


async def test_scope_expansion_approval_loads_persisted_clarification_and_clears_it():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    upserts = []
    pending = PendingClarification(
        clarification_id="clar-persisted",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={
            "original_message": "attention mask ở đâu?",
            "allowed_path_ids": ["computer_vision", "nlp"],
            "current_path_ids": ["computer_vision"],
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        if request.course_ids and "CS224n" in request.course_ids:
            return UnitSearchResponse(
                results=[
                    UnitSearchResult(
                        canonical_unit_id="unit-mask",
                        course_id="CS224n",
                        unit_name="Attention Mask",
                        summary="Attention mask content.",
                        score=3,
                        quiz_available=True,
                    )
                ],
                trace=RetrievalTrace(trace_id="trace-expanded", ranking_version="unit_search_v1"),
            )
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-empty", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-scope-approve",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(side_effect=lambda **kwargs: upserts.append(kwargs)),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="approve"),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="ok", incomingMessageId="msg-scope-approve"),
        conversation_id=str(conversation_id),
        thread_id="thread-scope-approve",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "grounded"
    assert response.citations[0].course_id == "CS224n"
    assert any("CS224n" in (request.course_ids or []) for request in search_requests)
    assert upserts[-1]["summary_json"].get("pendingClarification") is None


async def test_scope_expansion_approval_uses_extracted_raw_topic_for_bm25_query():
    conversation_id = uuid4()
    user_id = uuid4()
    search_requests = []
    pending = PendingClarification(
        clarification_id="clar-persisted-topic",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={
            "original_message": "Where should I review dependency parsing?",
            "raw_topic": "dependency parsing",
            "allowed_path_ids": ["computer_vision", "nlp"],
            "current_path_ids": ["computer_vision"],
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        search_requests.append(request)
        return UnitSearchResponse(
            results=[],
            trace=RetrievalTrace(trace_id="trace-expanded-empty", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-scope-topic-approve",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="approve"),
        conversation_repo=conversation_repo,
    )

    await service.chat(
        request=AgentChatRequest(message="yes, search other paths", incomingMessageId="msg-scope-topic-approve"),
        conversation_id=str(conversation_id),
        thread_id="thread-scope-topic-approve",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    assert search_requests[0].query == "dependency parsing"


async def test_scope_expansion_rejection_clears_pending_clarification_without_search():
    conversation_id = uuid4()
    user_id = uuid4()
    pending = PendingClarification(
        clarification_id="clar-persisted",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={
            "original_message": "attention mask ở đâu?",
            "allowed_path_ids": ["computer_vision", "nlp"],
            "current_path_ids": ["computer_vision"],
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    async def search(request, allowed_course_ids):
        raise AssertionError("Scope expansion rejection must not run retrieval")

    memory = SimpleNamespace(
        summary_status="fresh",
        recent_message_window=10,
        summary_json={
            "memoryRef": f"agent_memory:{conversation_id}:v1",
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-scope-reject",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    upserts = []
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(side_effect=lambda **kwargs: upserts.append(kwargs)),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=PendingDecisionRouter(action="reject"),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="no, keep current path", incomingMessageId="msg-scope-reject"),
        conversation_id=str(conversation_id),
        thread_id="thread-scope-reject",
        user_id=str(user_id),
        allowed_course_ids=["CS231n", "CS224n"],
        current_path_course_ids=["CS231n"],
    )

    assert response.answer.confidence == "partial"
    assert "current path" in response.answer.markdown
    assert upserts[-1]["summary_json"].get("pendingClarification") is None


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


async def test_graph_persists_failed_request_retry_context_when_router_model_fails():
    conversation_id = uuid4()
    user_id = uuid4()
    upserts = []

    class Router:
        def route(self, message, route_context):
            raise AgentRouterUnavailableError("model timeout", "AGENT_LLM_TIMEOUT")

    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_run_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=None),
        create_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="run-failed")),
        mark_run_running=AsyncMock(),
        mark_run_failed=AsyncMock(),
    )
    conversation_repo = SimpleNamespace(
        add_message=AsyncMock(),
        get_memory=AsyncMock(return_value=None),
        upsert_memory=AsyncMock(side_effect=lambda **kwargs: upserts.append(kwargs)),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=Router(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
        conversation_repo=conversation_repo,
    )

    with pytest.raises(AgentRouterUnavailableError):
        await service.chat(
            request=AgentChatRequest(
                message="kiểm cho tôi thông tin về UNet",
                incomingMessageId="msg-failed",
            ),
            conversation_id=str(conversation_id),
            thread_id="thread-failed",
            user_id=str(user_id),
            allowed_course_ids=["CS231n"],
        )

    repo.mark_run_failed.assert_awaited_once()
    pending = upserts[-1]["summary_json"]["pendingClarification"]["clarification"]
    assert pending["payload"]["kind"] == "failed_request_retry"
    assert pending["payload"]["original_message"] == "kiểm cho tôi thông tin về UNet"


async def test_graph_retries_failed_run_with_same_incoming_message_id():
    conversation_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="U-Net"),
            )

        def compose_grounded_answer(self, message, citations):
            return "U-Net appears in the segmentation unit."

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-unet",
                    course_id="CS231n",
                    unit_name="Semantic segmentation from per-pixel labeling to U-Net",
                    summary="U-Net segmentation content.",
                    score=3,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-retry", ranking_version="unit_search_v1"),
        )

    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_run_by_incoming_message=AsyncMock(
            return_value=SimpleNamespace(id=run_id, status="failed_retryable")
        ),
        get_active_run=AsyncMock(return_value=None),
        create_run=AsyncMock(),
        mark_run_running=AsyncMock(),
        store_response_payload=AsyncMock(return_value="resp-retry"),
        mark_run_succeeded=AsyncMock(),
        mark_run_interrupted=AsyncMock(),
        mark_run_failed=AsyncMock(),
    )
    conversation_repo = SimpleNamespace(
        add_message=AsyncMock(),
        get_memory=AsyncMock(return_value=None),
        list_messages=AsyncMock(return_value=[]),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="kiểm cho tôi thông tin về UNet", incomingMessageId="msg-retry"),
        conversation_id=str(conversation_id),
        thread_id="thread-retry",
        user_id=str(user_id),
        allowed_course_ids=["CS231n"],
    )

    assert response.answer.markdown == "U-Net appears in the segmentation unit."
    repo.create_run.assert_not_called()
    repo.mark_run_running.assert_awaited_once_with(str(run_id))
    conversation_repo.add_message.assert_awaited_once()
    assert conversation_repo.add_message.await_args.kwargs["role"] == "assistant"


async def test_graph_resolves_failed_request_retry_followup_through_structured_router():
    conversation_id = uuid4()
    user_id = uuid4()
    pending = PendingClarification(
        clarification_id="clar-failed-retry",
        type="slot_disambiguation",
        status="awaiting_response",
        payload={
            "kind": "failed_request_retry",
            "original_message": "kiểm cho tôi thông tin về UNet",
            "original_incoming_message_id": "msg-original",
        },
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    routed_messages = []

    class Router(PendingDecisionRouter):
        def route(self, message, route_context):
            routed_messages.append(message)
            return AgentRoute(
                intent="find_content",
                confidence=0.9,
                extracted_slots=AgentSlots(raw_topic="U-Net"),
            )

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-unet",
                    course_id="CS231n",
                    unit_name="Semantic segmentation from per-pixel labeling to U-Net",
                    summary="U-Net segmentation content.",
                    score=3,
                    quiz_available=True,
                )
            ],
            trace=RetrievalTrace(trace_id="trace-followup-retry", ranking_version="unit_search_v1"),
        )

    memory = SimpleNamespace(
        summary_json={
            "summaryVersion": 1,
            "pendingClarification": {
                "threadId": "thread-followup-retry",
                "clarification": pending.model_dump(mode="json"),
            },
        },
    )
    conversation_repo = SimpleNamespace(
        get_memory=AsyncMock(return_value=memory),
        upsert_memory=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(search=search),
        requirement_service=SimpleNamespace(),
        router=Router(action="approve", grounded_answer="Found U-Net after retry."),
        conversation_repo=conversation_repo,
    )

    response = await service.chat(
        request=AgentChatRequest(message="thử lại", incomingMessageId="msg-followup-retry"),
        conversation_id=str(conversation_id),
        thread_id="thread-followup-retry",
        user_id=str(user_id),
        allowed_course_ids=["CS231n"],
    )

    assert routed_messages == ["kiểm cho tôi thông tin về UNet"]
    assert response.answer.markdown == "Found U-Net after retry."
    assert response.citations[0].canonical_unit_id == "unit-unet"


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
        type="custom_action",
        payload_json={},
        idempotency_key="idem-reject",
    )
    repo = SimpleNamespace(
        get_pending_action=AsyncMock(return_value=pending),
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_non_interrupted_run=AsyncMock(return_value=None),
        create_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="resume-run-reject")),
        mark_run_running=AsyncMock(),
        mark_action_cancelled=AsyncMock(),
        mark_latest_interrupted_run_final=AsyncMock(),
        store_response_payload=AsyncMock(return_value="resp-reject"),
        mark_run_succeeded=AsyncMock(),
        mark_run_failed=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
    )
    service._graph = None

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
        type="custom_action",
        payload_json={},
        idempotency_key="idem-approve",
    )
    repo = SimpleNamespace(
        get_pending_action=AsyncMock(return_value=pending),
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_non_interrupted_run=AsyncMock(return_value=None),
        create_run=AsyncMock(return_value=SimpleNamespace(graph_run_id="resume-run-approve")),
        mark_run_running=AsyncMock(),
        get_committed_action_result=AsyncMock(return_value=None),
        mark_action_committed=AsyncMock(),
        mark_latest_interrupted_run_final=AsyncMock(),
        store_response_payload=AsyncMock(return_value="resp-approve"),
        mark_run_succeeded=AsyncMock(),
        mark_run_failed=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
    )
    service._graph = None

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
        result={"type": "custom_action", "status": "confirmed"},
    )
    repo.mark_latest_interrupted_run_final.assert_awaited_once_with(
        thread_id="thread-approve",
        status="succeeded",
    )


async def test_native_resume_approve_commits_start_assessment_once():
    conversation_id = str(uuid4())
    user_id = uuid4()
    pending_holder = {}
    commit_calls = []

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="assess_knowledge",
                confidence=0.95,
                extracted_slots=AgentSlots(canonical_unit_ids=["unit-a"], raw_topic="attention"),
            )

    async def create_pending_action(**kwargs):
        pending = SimpleNamespace(
            action_id="act-assessment",
            conversation_id=kwargs["conversation_id"],
            thread_id=kwargs["thread_id"],
            user_id=kwargs["user_id"],
            status="awaiting_confirmation",
            expires_at=kwargs["expires_at"],
            type=kwargs["action_type"],
            payload_json=kwargs["payload"],
            idempotency_key=kwargs["idempotency_key"],
        )
        pending_holder["pending"] = pending
        return pending

    class CommitService:
        async def commit_start_assessment(self, db, *, user_id, payload, idempotency_key):
            commit_calls.append((user_id, payload, idempotency_key))
            return {
                "type": "start_assessment",
                "status": "committed",
                "sessionId": "session-1",
                "totalQuestions": 3,
                "questions": [],
                "canonicalUnitIds": payload["canonical_unit_ids"],
                "phase": payload["phase"],
                "href": "/assessment",
            }

    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=None),
        get_active_non_interrupted_run=AsyncMock(return_value=None),
        create_run=AsyncMock(
            side_effect=[
                SimpleNamespace(graph_run_id="run-chat"),
                SimpleNamespace(graph_run_id="run-resume"),
            ]
        ),
        mark_run_running=AsyncMock(),
        create_pending_action=AsyncMock(side_effect=create_pending_action),
        store_response_payload=AsyncMock(side_effect=["resp-chat", "resp-resume"]),
        mark_run_interrupted=AsyncMock(),
        mark_run_succeeded=AsyncMock(),
        mark_run_failed=AsyncMock(),
        get_pending_action=AsyncMock(side_effect=lambda action_id: pending_holder["pending"]),
        get_committed_action_result=AsyncMock(return_value=None),
        mark_action_committed=AsyncMock(),
        mark_latest_interrupted_run_final=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=Router(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
        action_commit_service=CommitService(),
        action_db=object(),
        action_user=SimpleNamespace(id=user_id),
    )

    proposal = await service.chat(
        request=AgentChatRequest(message="quiz me on attention", incomingMessageId="msg-chat"),
        conversation_id=conversation_id,
        thread_id="thread-assessment",
        user_id=str(user_id),
        allowed_course_ids=["CS224n"],
    )
    response = await service.resume_action(
        AgentActionResumeRequest(
            conversationId=conversation_id,
            actionId=proposal.actions[0].action_id,
            decision="approve",
            incomingMessageId="msg-resume",
        ),
        user_id=str(user_id),
    )

    assert proposal.actions[0].action_id == "act-assessment"
    assert response.answer.markdown == "Assessment is ready. You can start it now."
    assert len(commit_calls) == 1
    assert commit_calls[0][1]["canonical_unit_ids"] == ["unit-a"]
    repo.mark_run_interrupted.assert_awaited_once()
    repo.mark_action_committed.assert_awaited_once()
    repo.mark_latest_interrupted_run_final.assert_awaited_once_with(
        thread_id="thread-assessment",
        status="succeeded",
    )


async def test_native_resume_approve_commits_replan_once():
    conversation_id = str(uuid4())
    user_id = uuid4()
    pending_holder = {}
    commit_calls = []

    class Router:
        def route(self, message, route_context):
            return AgentRoute(
                intent="request_replan",
                confidence=0.95,
                extracted_slots=AgentSlots(canonical_unit_ids=["unit-a"]),
            )

    async def create_pending_action(**kwargs):
        pending = SimpleNamespace(
            action_id="act-replan",
            conversation_id=kwargs["conversation_id"],
            thread_id=kwargs["thread_id"],
            user_id=kwargs["user_id"],
            status="awaiting_confirmation",
            expires_at=kwargs["expires_at"],
            type=kwargs["action_type"],
            payload_json=kwargs["payload"],
            idempotency_key=kwargs["idempotency_key"],
        )
        pending_holder["pending"] = pending
        return pending

    class CommitService:
        async def commit_replan(self, db, *, user, payload, idempotency_key):
            commit_calls.append((user.id, payload, idempotency_key))
            return {
                "type": "request_replan",
                "status": "committed",
                "accepted": True,
                "dryRun": False,
                "impact": {"mode": "replanned", "totalUnits": 4},
            }

    repo = SimpleNamespace(
        get_completed_response_by_incoming_message=AsyncMock(return_value=None),
        get_active_run=AsyncMock(return_value=None),
        get_active_non_interrupted_run=AsyncMock(return_value=None),
        create_run=AsyncMock(
            side_effect=[
                SimpleNamespace(graph_run_id="run-chat"),
                SimpleNamespace(graph_run_id="run-resume"),
            ]
        ),
        mark_run_running=AsyncMock(),
        create_pending_action=AsyncMock(side_effect=create_pending_action),
        store_response_payload=AsyncMock(side_effect=["resp-chat", "resp-resume"]),
        mark_run_interrupted=AsyncMock(),
        mark_run_succeeded=AsyncMock(),
        mark_run_failed=AsyncMock(),
        get_pending_action=AsyncMock(side_effect=lambda action_id: pending_holder["pending"]),
        get_committed_action_result=AsyncMock(return_value=None),
        mark_action_committed=AsyncMock(),
        mark_latest_interrupted_run_final=AsyncMock(),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=Router(),
        graph_repo=repo,
        thread_lock=NoopThreadLock(),
        action_commit_service=CommitService(),
        action_db=object(),
        action_user=SimpleNamespace(id=user_id),
    )

    proposal = await service.chat(
        request=AgentChatRequest(message="replan this", incomingMessageId="msg-chat-replan"),
        conversation_id=conversation_id,
        thread_id="thread-replan",
        user_id=str(user_id),
        allowed_course_ids=["CS224n"],
    )
    response = await service.resume_action(
        AgentActionResumeRequest(
            conversationId=conversation_id,
            actionId=proposal.actions[0].action_id,
            decision="approve",
            incomingMessageId="msg-resume-replan",
        ),
        user_id=str(user_id),
    )

    assert response.answer.markdown == "I recalculated your learning plan from the latest assessment evidence."
    assert len(commit_calls) == 1
    assert commit_calls[0][1]["dry_run"] is False
    repo.mark_action_committed.assert_awaited_once()
    repo.mark_latest_interrupted_run_final.assert_awaited_once_with(
        thread_id="thread-replan",
        status="succeeded",
    )


async def test_thread_memory_compaction_persists_versioned_memory_ref():
    conversation_id = uuid4()
    user_id = uuid4()
    upserts = []
    messages = [
        SimpleNamespace(role="user", markdown=f"message {index}")
        for index in range(5)
    ]

    repo = SimpleNamespace(
        list_messages=AsyncMock(return_value=messages),
        get_memory=AsyncMock(
            return_value=SimpleNamespace(summary_json={"summaryVersion": 2})
        ),
        upsert_memory=AsyncMock(side_effect=lambda **kwargs: upserts.append(kwargs)),
    )
    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
        conversation_repo=repo,
        memory_compaction_service=AgentMemoryCompactionService(
            max_recent_turns=2,
            max_messages_before_compaction=3,
        ),
    )

    await service._compact_thread_memory_if_needed(str(conversation_id), str(user_id))

    assert upserts
    summary = upserts[0]["summary_json"]
    assert summary["memoryRef"] == f"agent_memory:{conversation_id}:v3"
    assert summary["summaryVersion"] == 3
    assert summary["messageCount"] == 3


async def test_capture_checkpoint_id_reads_langgraph_snapshot_config():
    class Graph:
        async def aget_state(self, config):
            return SimpleNamespace(
                config={"configurable": {"thread_id": "thread-1", "checkpoint_id": "chk-1"}}
            )

    service = AgentGraphService(
        search_service=SimpleNamespace(),
        requirement_service=SimpleNamespace(),
        router=DeterministicAgentRouter(),
    )
    service._graph = Graph()

    assert await service._capture_checkpoint_id("thread-1") == "chk-1"
