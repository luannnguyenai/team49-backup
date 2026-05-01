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
