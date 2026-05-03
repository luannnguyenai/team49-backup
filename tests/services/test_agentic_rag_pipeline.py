import pytest

from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agentic_rag_contracts import AgenticRAGObservation, AgenticRAGToolCall
from src.services.agentic_rag_pipeline import AgenticRAGPipeline
from src.services.agentic_rag_tools import AgenticRAGToolExecutor, AgentRAGToolRegistry


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


def test_agent_rag_tool_registry_lists_policy_metadata():
    registry = AgentRAGToolRegistry()

    current_path = registry.resolve("search_current_path_units")
    expansion = registry.resolve("offer_scope_expansion")

    assert current_path is not None
    assert current_path.requires_evidence is True
    assert expansion is not None
    assert expansion.requires_evidence is False
    assert registry.resolve("unsupported_tool") is None


def test_agent_rag_tool_registry_builds_llm_visible_prompt_text():
    registry = AgentRAGToolRegistry()

    prompt_text = registry.build_prompt_text()

    assert "search_current_path_units" in prompt_text
    assert "offer_scope_expansion" in prompt_text
    assert "requires evidence" in prompt_text
    assert "current path first" in prompt_text.lower()


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


class FailingToolNodes(FakeToolNodes):
    async def find_content(self, message, intent, slots, allowed_course_ids):
        raise RuntimeError("BM25 index timeout while searching units")


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


@pytest.mark.asyncio
async def test_tool_executor_normalizes_retrieval_errors():
    executor = AgenticRAGToolExecutor(FailingToolNodes())

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="search_current_path_units",
            arguments={"query": "RCNN"},
            rationale="Search current path.",
        ),
        message="find RCNN",
        intent="find_content",
        slots=AgentSlots(raw_topic="RCNN"),
        allowed_course_ids=["CS231N"],
    )

    assert observation.success is False
    assert observation.evidence_status == "no_source"
    assert observation.result.fallback is not None
    assert observation.result.fallback.error_code == "RAG_TIMEOUT"
    assert "BM25 index timeout" not in observation.result.answer_markdown


class FakePipelineRouter:
    def __init__(self):
        self.calls = []

    def rag_think(self, **kwargs):
        self.calls.append(("think", kwargs))
        return {"user_goal": "Find YOLO", "active_topic": "YOLO"}

    def rag_act(self, **kwargs):
        self.calls.append(("act", kwargs))
        return AgenticRAGToolCall(
            tool="search_current_path_units",
            arguments={"query": "YOLO"},
            rationale="Search current path.",
        )

    def rag_observe(self, **kwargs):
        self.calls.append(("observe", kwargs))
        return kwargs["tool_observation"]

    def rag_respond(self, **kwargs):
        self.calls.append(("respond", kwargs))
        return type(
            "Final",
            (),
            {
                "answer_markdown": "YOLO is covered as a single-stage detector.",
                "evidence_status": "grounded",
                "evidence_sufficient": True,
                "clarification_question": None,
            },
        )()


class GroundedToolNodes(FakeToolNodes):
    async def find_content(self, message, intent, slots, allowed_course_ids):
        from src.schemas.agent import AgentAction, AgentCitation

        self.calls.append(("find_content", message, intent, slots, allowed_course_ids))
        return ToolResult(
            kind="find_content",
            citations=[
                AgentCitation(
                    canonical_unit_id="u-yolo",
                    course_id="CS231N",
                    unit_name="Single-stage and transformer detectors: YOLO and DETR",
                    quote="YOLO is introduced as a single-stage detector.",
                    source="summary",
                )
            ],
            actions=[
                AgentAction(
                    type="open_unit",
                    label="Open YOLO",
                    canonical_unit_id="u-yolo",
                    learn_href="/courses/cs231n/learn/lecture-9-seg4",
                )
            ],
            requires_evidence=True,
        )


@pytest.mark.asyncio
async def test_agentic_rag_pipeline_runs_stages_in_order_and_returns_tool_result():
    router = FakePipelineRouter()
    tool_executor = AgenticRAGToolExecutor(GroundedToolNodes())
    pipeline = AgenticRAGPipeline(router=router, tool_executor=tool_executor)

    result = await pipeline.run(
        message="Tìm thông tin YOLO",
        intent="find_content",
        slots=AgentSlots(raw_topic="YOLO"),
        route_context=None,
        recent_messages=[],
        allowed_course_ids=["CS231N"],
    )

    assert [name for name, _ in router.calls] == ["think", "act", "observe", "respond"]
    assert result.answer_markdown == "YOLO is covered as a single-stage detector."
    assert result.citations[0].canonical_unit_id == "u-yolo"
    assert result.actions[0].learn_href == "/courses/cs231n/learn/lecture-9-seg4"


@pytest.mark.asyncio
async def test_agentic_rag_pipeline_does_not_emit_hidden_thinking():
    class LeakyRouter(FakePipelineRouter):
        def rag_respond(self, **kwargs):
            self.calls.append(("respond", kwargs))
            return type(
                "Final",
                (),
                {
                    "answer_markdown": "Hidden thought: search current path. Final: YOLO is covered.",
                    "evidence_status": "grounded",
                    "evidence_sufficient": True,
                    "clarification_question": None,
                },
            )()

    pipeline = AgenticRAGPipeline(
        router=LeakyRouter(),
        tool_executor=AgenticRAGToolExecutor(GroundedToolNodes()),
    )

    result = await pipeline.run(
        message="Tìm thông tin YOLO",
        intent="find_content",
        slots=AgentSlots(raw_topic="YOLO"),
        route_context=None,
        recent_messages=[],
        allowed_course_ids=["CS231N"],
    )

    assert "Hidden thought" not in result.answer_markdown
    assert result.answer_markdown == "YOLO is covered."
