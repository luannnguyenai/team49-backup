from src.schemas.agent import AgentCitation, RetrievalTrace
from src.services.agent_graph_contracts import ToolResult
from src.services.agent_response_composer import AgentResponseComposer


def test_composer_refuses_grounded_answer_without_evidence():
    response = AgentResponseComposer().compose(
        conversation_id="conv-1",
        message_id="msg-1",
        result=ToolResult(
            kind="find_content",
            answer_markdown="I found it.",
            citations=[],
            requires_evidence=True,
        ),
    )

    assert response.answer.confidence == "no_source"
    assert response.fallback is not None


def test_composer_builds_system_error_with_error_code():
    response = AgentResponseComposer().compose_system_error(
        conversation_id="conv-1",
        error_code="AGENT_CHAT_ERROR",
    )

    assert response.answer.confidence == "fallback"
    assert "AGENT_CHAT_ERROR" in response.answer.markdown
    assert response.warning is not None
    assert response.warning.message == "AGENT_CHAT_ERROR"
    assert response.fallback is not None
    assert response.fallback.error_code == "AGENT_CHAT_ERROR"


def test_composer_propagates_retrieval_trace_for_grounded_answers():
    response = AgentResponseComposer().compose(
        conversation_id="conv-1",
        message_id="msg-1",
        result=ToolResult(
            kind="find_content",
            answer_markdown="Review the CNN unit.",
            citations=[
                AgentCitation(
                    canonical_unit_id="unit-cnn",
                    course_id="CS231n",
                    unit_name="CNNs",
                    source="summary",
                )
            ],
            requires_evidence=True,
            trace=RetrievalTrace(
                trace_id="trace-cnn",
                intent="navigate_to_unit",
                selected_path="current_path",
                candidate_courses=["CS231n"],
                ranking_version="unit_search_v1",
                selected_unit_ids=["unit-cnn"],
            ),
        ),
    )

    assert response.trace is not None
    assert response.trace.trace_id == "trace-cnn"
    assert response.trace.intent == "navigate_to_unit"
    assert response.trace.selected_path == "current_path"


def test_composer_allows_partial_confidence_override_with_citations():
    response = AgentResponseComposer().compose(
        conversation_id="conv-1",
        message_id="msg-1",
        result=ToolResult(
            kind="find_content",
            answer_markdown="I only found related results, not an exact match.",
            citations=[
                AgentCitation(
                    canonical_unit_id="unit-related",
                    course_id="CS231n",
                    unit_name="Related CNN unit",
                    source="summary",
                )
            ],
            metadata={"answer_confidence": "partial"},
        ),
    )

    assert response.answer.confidence == "partial"
    assert response.citations[0].canonical_unit_id == "unit-related"
