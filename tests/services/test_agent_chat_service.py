from types import SimpleNamespace

import pytest

from src.schemas.agent import AgentChatRequest, RetrievalTrace, UnitSearchResponse
from src.services.agent_chat_service import (
    AgentChatService,
    classify_agent_intent,
    extract_requirement_target_path,
)


def test_classify_agent_intent_uses_intent_table_not_single_phrase_match():
    assert classify_agent_intent("Can you verify my CNN knowledge?") == "assess_knowledge"
    assert classify_agent_intent("What should I learn before transformers?") == "ask_what_next"
    assert classify_agent_intent("Where is receptive field covered?") == "find_content"
    assert classify_agent_intent("Which DL prerequisites do I need for NLP?") == "explain_planner_decision"


def test_extract_requirement_target_path_from_message():
    assert extract_requirement_target_path("Which DL prerequisites do I need for NLP?") == "nlp"
    assert extract_requirement_target_path("Which DL parts are required for computer vision?") == "computer_vision"
    assert extract_requirement_target_path("What should I learn before Vision Transformers?") == "computer_vision"
    assert extract_requirement_target_path("What should I learn before ViT?") == "computer_vision"
    assert extract_requirement_target_path("Which prerequisites do I need for CV?") == "computer_vision"
    assert extract_requirement_target_path("Does activity recognition require DL?") is None


@pytest.mark.asyncio
async def test_chat_uses_path_requirements_for_required_parts_question():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()

    async def get_requirements(request, allowed_course_ids, user_id=None):
        assert user_id == "user-1"
        return SimpleNamespace(
            required_units=[
                SimpleNamespace(
                    canonical_unit_id="unit-a",
                    course_id="CS230",
                    unit_name="Backpropagation",
                    learn_href="/courses/cs230/learn/lecture-02-seg4",
                )
            ],
            trace=RetrievalTrace(trace_id="trace-req", ranking_version="path_requirements_v1"),
        )

    requirement_service.get_requirements = get_requirements
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Which DL parts are required for NLP?"),
        allowed_course_ids=["CS230", "CS224n"],
        user_id="user-1",
    )

    assert response.answer.confidence == "grounded"
    assert response.citations[0].canonical_unit_id == "unit-a"
    assert response.actions[0].type == "open_unit"


@pytest.mark.asyncio
async def test_chat_asks_for_target_when_requirement_question_is_ambiguous():
    service = AgentChatService(SimpleNamespace(), SimpleNamespace())

    response = await service.chat(
        AgentChatRequest(message="Which prerequisites should I learn first?"),
        allowed_course_ids=["CS230", "CS231n", "CS224n"],
    )

    assert response.answer.confidence == "partial"
    assert response.warning and response.warning.type == "ambiguous_target"
    assert [action.type for action in response.actions] == ["choose_target_path", "choose_target_path"]


@pytest.mark.asyncio
async def test_chat_marks_controlled_catalog_answer_outside_current_path():
    search_service = SimpleNamespace()

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                {
                    "canonical_unit_id": "cs224n-wordvec",
                    "course_id": "CS224n",
                    "lecture_id": "lecture-01",
                    "lecture_title": "Lecture 1",
                    "unit_name": "Word vectors and embeddings",
                    "learn_href": "/courses/cs224n/learn/lecture-01-seg3",
                    "outside_current_path": True,
                }
            ],
            trace=RetrievalTrace(trace_id="trace-1", ranking_version="unit_search_v1"),
        )

    search_service.search = search
    service = AgentChatService(search_service, SimpleNamespace())

    response = await service.chat(
        AgentChatRequest(message="What are word vectors?"),
        allowed_course_ids=["CS230", "CS231n", "CS224n"],
        current_path_course_ids=["CS230", "CS231n"],
    )

    assert response.warning and response.warning.type == "outside_current_path"
    assert response.citations[0].course_id == "CS224n"


@pytest.mark.asyncio
async def test_chat_returns_assessment_workflow_action_card_for_skip_request():
    search_service = SimpleNamespace()

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                {"canonical_unit_id": "cnn-unit-a", "course_id": "CS231n", "unit_name": "CNN A"},
                {"canonical_unit_id": "cnn-unit-b", "course_id": "CS231n", "unit_name": "CNN B"},
            ],
            trace=RetrievalTrace(trace_id="trace-1", ranking_version="unit_search_v1"),
        )

    search_service.search = search
    service = AgentChatService(search_service, SimpleNamespace())

    response = await service.chat(
        AgentChatRequest(message="I know CNN. Test me so I can skip it."),
        allowed_course_ids=["CS230", "CS231n"],
    )

    assert response.actions[0].type == "start_assessment_workflow"
    assert response.actions[0].canonical_unit_ids == ["cnn-unit-a", "cnn-unit-b"]
    assert response.warning and response.warning.type == "needs_assessment"
