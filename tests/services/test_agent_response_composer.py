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
