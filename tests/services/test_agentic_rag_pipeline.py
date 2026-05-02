import pytest

from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agentic_rag_contracts import AgenticRAGObservation, AgenticRAGToolCall
from src.services.agentic_rag_tools import AgenticRAGToolExecutor


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


class FakeToolNodes:
    def __init__(self):
        self.calls = []

    async def clarify(self, message, reason="ambiguous_target"):
        self.calls.append(("clarify", message, reason))
        return ToolResult(kind="clarification", answer_markdown=reason)

    async def find_content(self, message, intent, slots, allowed_course_ids):
        self.calls.append(("find_content", message, intent, slots, allowed_course_ids))
        return ToolResult(
            kind="find_content",
            answer_markdown=None,
            citations=[],
            metadata={"search_queries": slots.search_queries},
        )


@pytest.mark.asyncio
async def test_tool_executor_searches_current_path_with_llm_query():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)
    slots = AgentSlots(raw_topic="YOLO", search_queries=["YOLO"])

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="search_current_path_units",
            arguments={"query": "YOLO single-stage detector"},
            rationale="search topic",
        ),
        message="Tìm YOLO",
        intent="find_content",
        slots=slots,
        allowed_course_ids=["CS231N"],
    )

    assert observation.tool == "search_current_path_units"
    assert tools.calls[0][3].search_queries == ["YOLO single-stage detector"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_expanded_search_without_approval():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)
    slots = AgentSlots(raw_topic="CNN", search_scope="current_path")

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="search_allowed_other_paths",
            arguments={"query": "CNN"},
            rationale="try broader search",
        ),
        message="find CNN",
        intent="find_content",
        slots=slots,
        allowed_course_ids=["CS224N", "CS231N"],
    )

    assert observation.evidence_status == "scope_expansion_required"
    assert observation.result.kind == "clarification"
