import pytest

from src.services.agent_graph_contracts import AgentRouterUnavailableError, AgentSlots, ToolResult
from src.services.agent_prompt_manager import AgentPromptManager
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
    user_context = registry.resolve("get_user_learning_context")
    lecture_context = registry.resolve("get_lecture_context")

    assert current_path is not None
    assert current_path.requires_evidence is True
    assert expansion is not None
    assert expansion.requires_evidence is False
    assert user_context is not None
    assert user_context.requires_evidence is False
    assert "quiz_history_analysis" in user_context.input_schema["context_kind"]
    assert lecture_context is not None
    assert lecture_context.requires_evidence is True
    assert registry.resolve("unsupported_tool") is None


def test_agent_rag_tool_registry_builds_llm_visible_prompt_text():
    registry = AgentRAGToolRegistry()

    prompt_text = registry.build_prompt_text()

    assert "search_current_path_units" in prompt_text
    assert "get_user_learning_context" in prompt_text
    assert "quiz-history" in prompt_text
    assert "get_lecture_context" in prompt_text
    assert "offer_scope_expansion" in prompt_text
    assert "requires evidence" in prompt_text
    assert "current path first" in prompt_text.lower()


def test_agentic_rag_responding_prompt_disallows_unsolicited_followup_offers():
    prompt = AgentPromptManager().get("agentic_rag", "responding.system")

    assert "Do not end with optional invitations" in prompt
    assert "unless the user explicitly requested that action" in prompt


def test_agentic_rag_tool_call_allows_missing_rationale_from_provider():
    call = AgenticRAGToolCall(
        tool="get_lecture_context",
        arguments={"canonical_unit_id": "unit-current"},
    )

    assert call.rationale == ""


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

    async def user_learning_context(
        self,
        *,
        message,
        slots,
        allowed_course_ids,
        current_path_course_ids=None,
        route_context=None,
        context_kind=None,
    ):
        self.calls.append(
            (
                "user_learning_context",
                message,
                allowed_course_ids,
                current_path_course_ids,
                route_context,
                context_kind,
            )
        )
        return ToolResult(
            kind="progress_summary",
            metadata={"learner_context": {"context_kind": context_kind}},
        )

    async def lecture_context(
        self,
        *,
        message,
        slots,
        allowed_course_ids,
        current_path_course_ids=None,
        canonical_unit_id=None,
        query=None,
    ):
        self.calls.append(
            (
                "lecture_context",
                message,
                allowed_course_ids,
                current_path_course_ids,
                canonical_unit_id,
                query,
            )
        )
        return ToolResult(kind="find_content", metadata={"lecture_context_found": True})


class FailingToolNodes(FakeToolNodes):
    async def find_content(self, message, intent, slots, allowed_course_ids):
        raise RuntimeError("BM25 index timeout while searching units")


@pytest.mark.asyncio
async def test_tool_executor_searches_current_path_with_llm_query_and_slot_fallback():
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
    assert tools.calls[0][3].search_queries == ["YOLO single-stage detector", "YOLO"]


@pytest.mark.asyncio
async def test_tool_executor_preserves_slot_fallback_after_llm_search_queries():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)
    slots = AgentSlots(raw_topic="CNN refined topic", search_queries=["CNN refined topic", "CNN"])

    await executor.execute(
        AgenticRAGToolCall(
            tool="search_current_path_units",
            arguments={
                "query": "CNN refined topic",
                "search_queries": ["CNN refined topic"],
            },
            rationale="search refined topic",
        ),
        message="khái niệm cơ bản",
        intent="find_content",
        slots=slots,
        allowed_course_ids=["CS231N"],
    )

    assert tools.calls[0][3].search_queries == ["CNN refined topic", "CNN"]


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
async def test_tool_executor_reads_authenticated_user_learning_context():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="get_user_learning_context",
            arguments={"context_kind": "weak_areas"},
            rationale="Need learner progress.",
        ),
        message="mình yếu phần nào?",
        intent="summarize_progress",
        slots=AgentSlots(),
        allowed_course_ids=["CS230", "CS231N"],
        current_path_course_ids=["CS230"],
        route_context={"route": "/agent"},
    )

    assert observation.tool == "get_user_learning_context"
    assert observation.evidence_status == "partial"
    assert tools.calls[0] == (
        "user_learning_context",
        "mình yếu phần nào?",
        ["CS230", "CS231N"],
        ["CS230"],
        {"route": "/agent"},
        "weak_areas",
    )


@pytest.mark.asyncio
async def test_tool_executor_gets_lecture_context_without_sql_access():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="get_lecture_context",
            arguments={"canonical_unit_id": "unit-1"},
            rationale="Need lecture evidence.",
        ),
        message="tóm tắt lecture này",
        intent="find_content",
        slots=AgentSlots(canonical_unit_ids=["unit-1"]),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
    )

    assert observation.tool == "get_lecture_context"
    assert tools.calls[0] == (
        "lecture_context",
        "tóm tắt lecture này",
        ["CS230"],
        ["CS230"],
        "unit-1",
        None,
    )


@pytest.mark.asyncio
async def test_tool_executor_uses_current_unit_context_instead_of_reasking():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="ask_clarification",
            arguments={"question": "Which video should I summarize?"},
            rationale="The model thought context was missing.",
        ),
        message="mình vừa xem tới nửa video, tóm tắt nội dung video này giúp mình",
        intent="find_content",
        slots=AgentSlots(canonical_unit_ids=["unit-current"]),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
    )

    assert observation.tool == "get_lecture_context"
    assert tools.calls[0] == (
        "lecture_context",
        "mình vừa xem tới nửa video, tóm tắt nội dung video này giúp mình",
        ["CS230"],
        ["CS230"],
        "unit-current",
        None,
    )


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
async def test_agentic_rag_pipeline_does_not_let_observer_replace_tool_result():
    class MutatingObserverRouter(FakePipelineRouter):
        def rag_observe(self, **kwargs):
            self.calls.append(("observe", kwargs))
            return AgenticRAGObservation(
                tool="ask_clarification",
                success=True,
                evidence_status="needs_clarification",
                result=ToolResult(
                    kind="clarification",
                    answer_markdown="Which variant do you mean?",
                    citations=[],
                    actions=[],
                ),
            )

    pipeline = AgenticRAGPipeline(
        router=MutatingObserverRouter(),
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

    assert result.answer_markdown == "YOLO is covered as a single-stage detector."
    assert result.citations[0].canonical_unit_id == "u-yolo"
    assert result.actions[0].learn_href == "/courses/cs231n/learn/lecture-9-seg4"
    assert result.metadata["agentic_rag_evidence_status"] == "grounded"


@pytest.mark.asyncio
async def test_agentic_rag_pipeline_continues_when_observer_model_is_unavailable():
    class UnavailableObserverRouter(FakePipelineRouter):
        def rag_observe(self, **kwargs):
            self.calls.append(("observe", kwargs))
            raise AgentRouterUnavailableError(
                "agentic_rag_observing_model_error",
                "AGENT_LLM_UNAVAILABLE",
            )

    router = UnavailableObserverRouter()
    pipeline = AgenticRAGPipeline(
        router=router,
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

    assert [name for name, _ in router.calls] == ["think", "act", "observe", "respond"]
    assert result.answer_markdown == "YOLO is covered as a single-stage detector."
    assert result.citations[0].canonical_unit_id == "u-yolo"
    assert result.metadata["agentic_rag_evidence_status"] == "grounded"


@pytest.mark.asyncio
async def test_agentic_rag_pipeline_preserves_tool_evidence_status_over_final_downgrade():
    class DowngradingFinalRouter(FakePipelineRouter):
        def rag_act(self, **kwargs):
            self.calls.append(("act", kwargs))
            return AgenticRAGToolCall(
                tool="get_user_learning_context",
                arguments={"context_kind": "weak_areas"},
                rationale="Need learner context.",
            )

        def rag_respond(self, **kwargs):
            self.calls.append(("respond", kwargs))
            return type(
                "Final",
                (),
                {
                    "answer_markdown": "Bạn đang yếu nhất ở supervised window classification.",
                    "evidence_status": "no_source",
                    "evidence_sufficient": False,
                    "clarification_question": None,
                },
            )()

    pipeline = AgenticRAGPipeline(
        router=DowngradingFinalRouter(),
        tool_executor=AgenticRAGToolExecutor(FakeToolNodes()),
    )

    result = await pipeline.run(
        message="mình yếu phần nào?",
        intent="summarize_progress",
        slots=AgentSlots(),
        route_context=None,
        recent_messages=[],
        allowed_course_ids=["CS230"],
    )

    assert result.metadata["agentic_rag_evidence_status"] == "partial"
    assert result.requires_evidence is False
    assert result.fallback is None


@pytest.mark.asyncio
async def test_agentic_rag_pipeline_keeps_nonevidence_tool_status_when_observer_downgrades():
    class DowngradingObserverRouter(FakePipelineRouter):
        def rag_act(self, **kwargs):
            self.calls.append(("act", kwargs))
            return AgenticRAGToolCall(
                tool="get_user_learning_context",
                arguments={"context_kind": "quiz_history_analysis"},
                rationale="Need learner quiz history.",
            )

        def rag_observe(self, **kwargs):
            self.calls.append(("observe", kwargs))
            return AgenticRAGObservation(
                tool="get_user_learning_context",
                success=True,
                evidence_status="no_source",
                result=ToolResult(kind="progress_summary", requires_evidence=True),
            )

        def rag_respond(self, **kwargs):
            self.calls.append(("respond", kwargs))
            return type(
                "Final",
                (),
                {
                    "answer_markdown": "Bạn hay sai nhất ở adaptive optimizers.",
                    "evidence_status": "no_source",
                    "evidence_sufficient": False,
                    "clarification_question": None,
                },
            )()

    pipeline = AgenticRAGPipeline(
        router=DowngradingObserverRouter(),
        tool_executor=AgenticRAGToolExecutor(FakeToolNodes()),
    )

    result = await pipeline.run(
        message="mình hay sai phần nào trong quiz?",
        intent="summarize_progress",
        slots=AgentSlots(),
        route_context=None,
        recent_messages=[],
        allowed_course_ids=["CS230"],
    )

    assert result.metadata["agentic_rag_evidence_status"] == "partial"
    assert result.requires_evidence is False
    assert result.fallback is None


@pytest.mark.asyncio
async def test_agentic_rag_stream_uses_structured_responder_contract():
    class StructuredOnlyRouter(FakePipelineRouter):
        def rag_think(self, **kwargs):
            self.calls.append(("think", kwargs))
            return type(
                "Thought",
                (),
                {
                    "user_goal": "Find YOLO",
                    "active_topic": "YOLO",
                    "evidence_need": "retrieval",
                    "tool_plan": ["search_current_path_units"],
                },
            )()

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

        def rag_respond_stream(self, **kwargs):
            raise AssertionError("raw response streaming should not be used")

    pipeline = AgenticRAGPipeline(
        router=StructuredOnlyRouter(),
        tool_executor=AgenticRAGToolExecutor(GroundedToolNodes()),
    )

    events = [
        line
        async for line in pipeline.run_stream(
            message="Tìm thông tin YOLO",
            intent="find_content",
            slots=AgentSlots(raw_topic="YOLO"),
            route_context=None,
            recent_messages=[],
            allowed_course_ids=["CS231N"],
        )
    ]

    assert any('"chunk"' in event and "YOLO is covered" in event for event in events)
    assert any('"done"' in event and "YOLO is covered" in event for event in events)


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


@pytest.mark.asyncio
async def test_agentic_rag_pipeline_strips_llm_footnote_citation_markers():
    class FootnoteRouter(FakePipelineRouter):
        def rag_respond(self, **kwargs):
            self.calls.append(("respond", kwargs))
            return type(
                "Final",
                (),
                {
                    "answer_markdown": (
                        "Mask R-CNN adds a pixel-level mask branch for each detected object."
                        "[^maskrcnn-proposals]"
                    ),
                    "evidence_status": "grounded",
                    "evidence_sufficient": True,
                    "clarification_question": None,
                },
            )()

    pipeline = AgenticRAGPipeline(
        router=FootnoteRouter(),
        tool_executor=AgenticRAGToolExecutor(GroundedToolNodes()),
    )

    result = await pipeline.run(
        message="Giải thích Mask R-CNN",
        intent="find_content",
        slots=AgentSlots(raw_topic="Mask R-CNN"),
        route_context=None,
        recent_messages=[],
        allowed_course_ids=["CS231N"],
    )

    assert "[^" not in result.answer_markdown
    assert result.answer_markdown == "Mask R-CNN adds a pixel-level mask branch for each detected object."


@pytest.mark.asyncio
async def test_agentic_rag_pipeline_preserves_topic_choice_tool_answer():
    from src.schemas.agent import AgentAction

    class TopicChoiceToolNodes(FakeToolNodes):
        async def find_content(self, message, intent, slots, allowed_course_ids):
            return ToolResult(
                kind="clarification",
                answer_markdown="I found several matching topics for CNN. Choose one below.",
                actions=[
                    AgentAction(
                        type="choose_topic",
                        label="Learn about CNN foundations",
                        canonical_unit_id="unit-cnn",
                    )
                ],
                requires_evidence=False,
                metadata={"topic_selection_offered": True},
            )

    class OverwritingRouter(FakePipelineRouter):
        def rag_respond(self, **kwargs):
            self.calls.append(("respond", kwargs))
            return type(
                "Final",
                (),
                {
                    "answer_markdown": "Unrelated generated options that do not match the cards.",
                    "evidence_status": "needs_clarification",
                    "evidence_sufficient": False,
                    "clarification_question": None,
                },
            )()

    pipeline = AgenticRAGPipeline(
        router=OverwritingRouter(),
        tool_executor=AgenticRAGToolExecutor(TopicChoiceToolNodes()),
    )

    result = await pipeline.run(
        message="Explain CNN",
        intent="explain_concept",
        slots=AgentSlots(raw_topic="CNN"),
        route_context=None,
        recent_messages=[],
        allowed_course_ids=["CS224n", "CS231n"],
    )

    assert result.answer_markdown == "I found several matching topics for CNN. Choose one below."
    assert result.actions[0].type == "choose_topic"
    assert result.metadata["preserved_tool_topic_selection_answer"] is True
