import pytest

from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agentic_rag_contracts import AgenticRAGObservation, AgenticRAGToolCall


def test_agentic_rag_tool_call_rejects_unknown_tool():
    with pytest.raises(Exception) as exc:
        AgenticRAGToolCall(tool="search_web", arguments={}, rationale="bad")

    assert "search_web" in str(exc.value)


def test_agentic_rag_observation_wraps_tool_result():
    result = ToolResult(kind="clarification", answer_markdown="Need more detail.")
    observation = AgenticRAGObservation(
        tool="ask_clarification",
        success=True,
        evidence_status="needs_clarification",
        result=result,
    )

    assert observation.result.answer_markdown == "Need more detail."
