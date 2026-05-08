import pytest

from src.services.agent_graph_contracts import AgentRouterUnavailableError, ToolResult
from src.services.agentic_rag_contracts import AgenticRAGObservation, AgenticRAGToolCall
from src.services.agent_structured_router import StructuredAgentRouter


class FakeStructuredModel:
    def __init__(self, payload, owner=None):
        self.payload = payload
        self.schema = None
        self.messages = None
        self.owner = owner

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.messages = messages
        if self.owner is not None:
            self.owner.messages = messages
        return self.schema(**self.payload)


class MethodAwareStructuredModel(FakeStructuredModel):
    def __init__(self, payload):
        super().__init__(payload)
        self.method = None

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        self.method = method
        return self


def test_structured_router_prefers_function_calling_structured_output():
    model = MethodAwareStructuredModel(
        {
            "intent": "find_content",
            "confidence": 0.91,
            "raw_topic": "RCNN",
            "search_queries": ["RCNN"],
            "target_path": None,
            "explicit_scope_requested": False,
            "rationale": "The user asked for course content.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="có thể tìm cho mình nội dung về RCNN không",
        route_context=None,
    )

    assert route.intent == "find_content"
    assert model.method == "function_calling"


def test_structured_router_returns_explicit_path_route():
    model = FakeStructuredModel(
        {
            "intent": "find_content",
            "confidence": 0.91,
            "raw_topic": "attention mask",
            "search_queries": ["attention mask", "transformer attention mask"],
            "target_path": "nlp",
            "explicit_scope_requested": True,
            "rationale": "User explicitly asked for NLP content.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="Trong path NLP có bài nào về attention mask không?",
        route_context=None,
    )

    assert route.intent == "find_content"
    assert route.extracted_slots.raw_topic == "attention mask"
    assert route.extracted_slots.search_queries == ["attention mask", "transformer attention mask"]
    assert route.extracted_slots.requested_path_id == "nlp"
    assert route.extracted_slots.search_scope == "explicit_path"


def test_structured_router_accepts_serialized_route_context():
    model = FakeStructuredModel(
        {
            "intent": "assistant_help",
            "confidence": 0.93,
            "raw_topic": None,
            "target_path": None,
            "rationale": "User asked for help.",
        }
    )

    route = StructuredAgentRouter(model=model).route(message="hi", route_context={"route": "/agent"})

    assert route.intent == "assistant_help"
    assert "Route context: {'route': '/agent'}" in model.messages[1]["content"]


def test_structured_router_low_confidence_clarifies():
    model = FakeStructuredModel(
        {
            "intent": "request_replan",
            "confidence": 0.4,
            "raw_topic": None,
            "target_path": None,
            "rationale": "Ambiguous short confirmation.",
            "clarification_question": "Which action are you approving?",
        }
    )

    route = StructuredAgentRouter(model=model).route(message="ok", route_context=None)

    assert route.intent == "clarify"
    assert route.confidence == 0.4
    assert route.clarification_question == "Which action are you approving?"
    assert route.candidate_intent == "request_replan"


def test_structured_router_routes_general_help_to_assistant_help():
    model = FakeStructuredModel(
        {
            "intent": "assistant_help",
            "confidence": 0.93,
            "raw_topic": None,
            "target_path": None,
            "rationale": "User asked for general assistant help.",
        }
    )

    route = StructuredAgentRouter(model=model).route(message="Can you help me?", route_context=None)

    assert route.intent == "assistant_help"


def test_structured_router_path_switch_intent_is_not_explicit_search_scope():
    model = FakeStructuredModel(
        {
            "intent": "request_path_switch",
            "confidence": 0.94,
            "raw_topic": None,
            "target_path": "nlp",
            "explicit_scope_requested": True,
            "rationale": "User asked to switch to NLP.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="Tôi muốn chuyển từ CV sang NLP.",
        route_context=None,
    )

    assert route.intent == "request_path_switch"
    assert route.extracted_slots.target_path == "nlp"
    assert route.extracted_slots.requested_path_id is None
    assert route.extracted_slots.search_scope == "current_path"


def test_structured_router_ignores_inferred_target_path_without_explicit_scope():
    model = FakeStructuredModel(
        {
            "intent": "find_content",
            "confidence": 0.9,
            "raw_topic": "CNNs",
            "target_path": "computer_vision",
            "explicit_scope_requested": False,
            "rationale": "The topic is related to computer vision but the user did not name a path.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="Where should I review CNNs?",
        route_context=None,
    )

    assert route.extracted_slots.target_path is None
    assert route.extracted_slots.requested_path_id is None
    assert route.extracted_slots.search_scope == "current_path"


def test_structured_router_prompt_rejects_keyword_routing_as_source_of_truth():
    model = FakeStructuredModel(
        {
            "intent": "explain_concept",
            "confidence": 0.9,
            "raw_topic": "skip connection",
            "target_path": None,
            "rationale": "Concept question.",
        }
    )

    StructuredAgentRouter(model=model).route(
        message="Giải thích skip connection",
        route_context=None,
    )

    system_prompt = model.messages[0]["content"]
    assert "Do not use raw keyword matching as the source of truth" in system_prompt
    assert "policy/course-mechanics questions from action creation" in system_prompt
    assert "short title-level BM25 queries first" in system_prompt
    assert "try retrieval before asking about the desired angle" in system_prompt


def test_structured_router_prompt_uses_recent_context_for_short_followups():
    model = FakeStructuredModel(
        {
            "intent": "find_content",
            "confidence": 0.86,
            "raw_topic": "YOLO architecture",
            "search_queries": ["YOLO architecture", "YOLO"],
            "target_path": None,
            "rationale": "The short reply refers to the previous YOLO answer.",
        }
    )

    StructuredAgentRouter(model=model).route(
        message="kiến trúc",
        route_context=None,
        recent_messages=[
            {
                "role": "assistant",
                "markdown": "Mình thấy một unit phù hợp với nội dung YOLO trong bài CS231n.",
                "citations": [{"unit_name": "Single-stage and transformer detectors: YOLO and DETR"}],
            }
        ],
    )

    system_prompt = model.messages[0]["content"]
    user_prompt = model.messages[1]["content"]
    assert "Use recent thread context to resolve short follow-up replies" in system_prompt
    assert "YOLO" in user_prompt
    assert "kiến trúc" in user_prompt


def test_structured_router_prompt_requires_contextual_followup_before_clarify():
    model = FakeStructuredModel(
        {
            "intent": "find_content",
            "confidence": 0.82,
            "raw_topic": "YOLO variants",
            "search_queries": ["YOLO variants", "YOLO"],
            "target_path": None,
            "rationale": "The short aspect request refers to the prior cited YOLO topic.",
        }
    )

    StructuredAgentRouter(model=model).route(
        message="tóm tắt các biến thể",
        route_context=None,
        recent_messages=[
            {
                "role": "assistant",
                "markdown": "YOLO là một single-stage detector.",
                "citations": [{"unit_name": "Single-stage and transformer detectors: YOLO and DETR"}],
            }
        ],
    )

    system_prompt = model.messages[0]["content"]
    assert "one active cited topic" in system_prompt
    assert "route to retrieval first" in system_prompt
    route = StructuredAgentRouter(model=model).route(
        message="tóm tắt các biến thể",
        route_context=None,
        recent_messages=[
            {
                "role": "assistant",
                "markdown": "YOLO là một single-stage detector.",
                "citations": [{"unit_name": "Single-stage and transformer detectors: YOLO and DETR"}],
            }
        ],
    )
    assert route.extracted_slots.search_queries == ["YOLO variants"]


def test_structured_router_prompt_routes_current_topic_questions_to_help():
    model = FakeStructuredModel(
        {
            "intent": "assistant_help",
            "confidence": 0.9,
            "raw_topic": None,
            "target_path": None,
            "rationale": "The user asks what the current visible conversation topic is.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="bạn có nhớ nãy giờ chúng ta đang nói chủ đề gì k",
        route_context=None,
        recent_messages=[{"role": "assistant", "markdown": "Mình vừa tóm tắt YOLO."}],
    )

    assert route.intent == "assistant_help"
    assert "currently discussing" in model.messages[0]["content"]


def test_structured_router_agentic_rag_thinking_stage_is_internal():
    model = FakeStructuredModel(
        {
            "user_goal": "Find course evidence about YOLO.",
            "active_topic": "YOLO",
            "missing_information": ["course source"],
            "evidence_need": "retrieval",
            "tool_plan": ["search current path units"],
        }
    )

    thought = StructuredAgentRouter(model=model).rag_think(
        message="Tìm thông tin YOLO",
        intent="find_content",
        slots={"raw_topic": "YOLO"},
        route_context=None,
        recent_messages=[],
    )

    assert thought.active_topic == "YOLO"
    assert "internal thinking stage" in model.messages[0]["content"]
    assert "never shown to the user" in model.messages[0]["content"]


def test_structured_router_agentic_rag_acting_stage_uses_allowed_tools():
    model = FakeStructuredModel(
        {
            "tool": "search_current_path_units",
            "arguments": {"query": "YOLO"},
            "rationale": "Search current path before answering.",
        }
    )

    call = StructuredAgentRouter(model=model).rag_act(
        message="Tìm thông tin YOLO",
        thought={"active_topic": "YOLO"},
        slots={"raw_topic": "YOLO"},
        route_context=None,
        recent_messages=[],
        observations=[],
    )

    assert call.tool == "search_current_path_units"
    system_prompt = model.messages[0]["content"]
    assert "search_current_path_units" in system_prompt
    assert "offer_scope_expansion" in system_prompt
    assert "Do not invent domain-specific synonyms" in system_prompt
    assert "Do not answer directly" in system_prompt


def test_structured_router_agentic_rag_acting_prompt_uses_dynamic_tool_text():
    model = FakeStructuredModel(
        {
            "tool": "search_current_path_units",
            "arguments": {"query": "YOLO"},
            "rationale": "Search current path first.",
        }
    )

    StructuredAgentRouter(model=model).rag_act(
        message="Tìm thông tin YOLO",
        thought={"active_topic": "YOLO"},
        slots={"raw_topic": "YOLO"},
        route_context=None,
        recent_messages=[],
        observations=[],
    )

    system_prompt = model.messages[0]["content"]
    assert "{tool_list}" not in system_prompt
    assert "Current-path search must be preferred" in system_prompt
    assert "search_current_path_units" in system_prompt
    assert "Search title-level course units" in system_prompt


def test_structured_router_agentic_rag_observing_stage_judges_evidence():
    model = FakeStructuredModel(
        {
            "tool": "search_current_path_units",
            "success": True,
            "evidence_status": "grounded",
            "result": {
                "kind": "find_content",
                "answer_markdown": None,
                "citations": [],
                "actions": [],
                "requires_evidence": True,
                "metadata": {},
            },
        }
    )

    observation = StructuredAgentRouter(model=model).rag_observe(
        message="Tìm thông tin YOLO",
        thought={"active_topic": "YOLO"},
        tool_call=AgenticRAGToolCall(
            tool="search_current_path_units",
            arguments={"query": "YOLO"},
            rationale="Search.",
        ),
        tool_observation=AgenticRAGObservation(
            tool="search_current_path_units",
            success=True,
            evidence_status="grounded",
            result=ToolResult(kind="find_content", requires_evidence=True),
        ),
        route_context=None,
        recent_messages=[],
    )

    assert observation.evidence_status == "grounded"
    assert "internal observing stage" in model.messages[0]["content"]
    assert "grounded, partial, no_source, or needs_clarification" in model.messages[0]["content"]


def test_structured_router_agentic_rag_responding_stage_uses_validated_evidence():
    model = FakeStructuredModel(
        {
            "answer_markdown": "YOLO is covered as a single-stage detector.",
            "evidence_status": "grounded",
            "evidence_sufficient": True,
            "clarification_question": None,
        }
    )

    final = StructuredAgentRouter(model=model).rag_respond(
        message="Tìm thông tin YOLO",
        thought={"active_topic": "YOLO"},
        observations=[
            {
                "tool": "search_current_path_units",
                "evidence_status": "grounded",
                "result": {"citations": [{"unit_name": "YOLO and DETR"}]},
            }
        ],
        route_context=None,
        recent_messages=[],
    )

    assert final.evidence_sufficient is True
    assert "Use only validated observations and accepted citations" in model.messages[0]["content"]
    assert "Do not reveal hidden thinking" in model.messages[0]["content"]


def test_structured_router_resolves_pending_followup_with_model_output():
    model = FakeStructuredModel(
        {
            "action": "approve",
            "refined_query": None,
            "clarification_question": None,
            "rationale": "User asked to show the offered top results.",
        }
    )

    decision = StructuredAgentRouter(model=model).resolve_pending_followup(
        message="top réult",
        pending_payload={
            "kind": "retrieval_query",
            "proposed_raw_topic": "U-Net",
            "show_top_results_allowed": True,
        },
        route_context=None,
    )

    assert decision.action == "approve"
    assert decision.refined_query is None
    system_prompt = model.messages[0]["content"]
    assert "Do not use keyword matching" in system_prompt


def test_structured_router_resolves_pending_followup_with_recent_context():
    model = FakeStructuredModel(
        {
            "action": "approve",
            "refined_query": None,
            "clarification_question": None,
            "rationale": "The user approved the stored top-results offer for the active YOLO topic.",
        }
    )

    StructuredAgentRouter(model=model).resolve_pending_followup(
        message="xem kết quả mạnh nhất",
        pending_payload={
            "kind": "retrieval_query",
            "proposed_raw_topic": "YOLO variants",
            "show_top_results_allowed": True,
        },
        route_context=None,
        recent_messages=[
            {
                "role": "assistant",
                "markdown": "Trong tài liệu hiện tại, YOLO đang được nói ở mức single-stage detector.",
                "citations": [{"unit_name": "Single-stage and transformer detectors: YOLO and DETR"}],
            }
        ],
    )

    system_prompt = model.messages[0]["content"]
    user_prompt = model.messages[1]["content"]
    assert "Recent visible thread messages" in user_prompt
    assert "YOLO and DETR" in user_prompt
    assert "Only approve offered actions that exist in the pending payload" in system_prompt
    assert "action=new_request" in system_prompt


def test_structured_router_preserves_model_candidate_intent_for_clarify():
    model = FakeStructuredModel(
        {
            "intent": "clarify",
            "candidate_intent": "find_content",
            "confidence": 0.28,
            "raw_topic": None,
            "target_path": None,
            "rationale": "Missing topic.",
            "clarification_question": "Which topic should I search for?",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="Where should I review?",
        route_context=None,
    )

    assert route.intent == "clarify"
    assert route.candidate_intent == "find_content"


class FakeChatModel:
    def __init__(self, grounded_payload=None):
        self.grounded_payload = grounded_payload

    def with_structured_output(self, schema):
        if "evidence_sufficient" in schema.model_fields:
            structured = FakeStructuredModel(
                self.grounded_payload
                or {
                    "answer_markdown": "I can help you find content and plan reviews.",
                    "evidence_sufficient": True,
                    "confidence": "grounded",
                    "clarification_question": None,
                },
                owner=self,
            )
            structured.schema = schema
            return structured
        if set(schema.model_fields) == {"answer_markdown"}:
            structured = FakeStructuredModel(
                {"answer_markdown": "There are several matching units. Would you like to narrow it or see the strongest results?"},
                owner=self,
            )
            structured.schema = schema
            return structured
        return FakeStructuredModel(
            {
                "intent": "assistant_help",
                "confidence": 0.9,
                "raw_topic": None,
                "target_path": None,
                "rationale": "General help.",
            }
        )

    def invoke(self, messages):
        self.messages = messages
        return type("Response", (), {"content": "I can help you find content and plan reviews."})()


def test_structured_router_composes_assistant_help_with_llm():
    model = FakeChatModel()

    answer = StructuredAgentRouter(model=model).compose_assistant_help(
        message="hello",
        route_context=None,
    )

    assert answer == "I can help you find content and plan reviews."
    assert "For simple greetings, greet briefly" in model.messages[0]["content"]


def test_structured_router_composes_assistant_help_with_recent_context():
    model = FakeChatModel()

    StructuredAgentRouter(model=model).compose_assistant_help(
        message="bạn có nhớ nãy giờ chúng ta đang nói chủ đề gì k",
        route_context=None,
        recent_messages=[
            {"role": "user", "markdown": "Tìm cho tôi thông tin YOLO"},
            {
                "role": "assistant",
                "markdown": "Mình thấy có nội dung về YOLO trong bài CS231n Lecture 9.",
            },
        ],
    )

    assert "Recent visible thread messages" in model.messages[1]["content"]
    assert "YOLO" in model.messages[1]["content"]
    assert "When the user asks what the current topic is" in model.messages[0]["content"]


def test_structured_router_filters_reasoning_blocks_from_text_response():
    class ReasoningBlockModel(FakeChatModel):
        def invoke(self, messages):
            self.messages = messages
            return type(
                "Response",
                (),
                {
                    "content": [
                        {"type": "reasoning", "summary": []},
                        {"type": "output_text", "text": "Chúng ta đang nói về YOLO."},
                    ]
                },
            )()

    answer = StructuredAgentRouter(model=ReasoningBlockModel()).compose_assistant_help(
        message="bạn có nhớ không",
        route_context=None,
        recent_messages=[],
    )

    assert answer == "Chúng ta đang nói về YOLO."


def test_structured_router_composes_grounded_answer_with_llm():
    model = FakeChatModel()
    citations = [
        {
            "course_id": "CS231n",
            "unit_name": "Convolutional Neural Networks",
            "lecture_title": "CNNs",
            "quote": "CNN layers learn spatial feature hierarchies.",
            "learn_href": "/learn/cs231n/cnns",
        }
    ]

    answer = StructuredAgentRouter(model=model).compose_grounded_answer(
        message="Where should I review CNNs?",
        citations=citations,
    )

    assert answer.answer_markdown == "I can help you find content and plan reviews."
    assert answer.evidence_sufficient is True
    assert "Use only these retrieved learning units" in model.messages[0]["content"]
    assert "related results below" in model.messages[0]["content"]
    assert "When evidence_sufficient=true, do not end with a follow-up question" in model.messages[0]["content"]
    assert "Do not suggest variants, rankings, comparisons, or choices" in model.messages[0]["content"]
    assert "the answer language must match the user's latest message" in model.messages[0]["content"]
    assert "One-shot output pattern" in model.messages[0]["content"]
    assert "To understand this better, review this prerequisite first" in model.messages[0]["content"]
    assert "Where should I review CNNs?" in model.messages[1]["content"]


def test_structured_router_grounded_answer_can_report_insufficient_evidence():
    model = FakeChatModel(
        grounded_payload={
            "answer_markdown": "I do not have enough evidence for that topic.",
            "evidence_sufficient": False,
            "confidence": "no_source",
            "clarification_question": "Which specific transformer masking behavior do you mean?",
        }
    )

    answer = StructuredAgentRouter(model=model).compose_grounded_answer(
        message="attention mask in transformers",
        citations=[
            {
                "course_id": "CS230",
                "unit_name": "Course overview",
                "quote": "Deep learning overview.",
            }
        ],
    )

    assert answer.evidence_sufficient is False
    assert answer.confidence == "no_source"


def test_structured_router_strips_trailing_followup_when_evidence_is_sufficient():
    model = FakeChatModel(
        grounded_payload={
            "answer_markdown": "YOLO is covered in this unit.\n\nDo you want me to explain variants?",
            "evidence_sufficient": True,
            "confidence": "grounded",
            "clarification_question": None,
        }
    )

    answer = StructuredAgentRouter(model=model).compose_grounded_answer(
        message="Tìm YOLO",
        citations=[
            {
                "course_id": "CS231n",
                "unit_name": "Single-stage and transformer detectors: YOLO and DETR",
                "quote": "YOLO is a single-stage detector.",
            }
        ],
    )

    assert answer.answer_markdown == "YOLO is covered in this unit."


def test_structured_router_strips_trailing_optional_offer_when_evidence_is_sufficient():
    model = FakeChatModel(
        grounded_payload={
            "answer_markdown": "YOLO is covered in this unit.\n\nNếu bạn muốn, mình có thể tóm tắt thêm.",
            "evidence_sufficient": True,
            "confidence": "grounded",
            "clarification_question": None,
        }
    )

    answer = StructuredAgentRouter(model=model).compose_grounded_answer(
        message="Tìm YOLO",
        citations=[
            {
                "course_id": "CS231n",
                "unit_name": "Single-stage and transformer detectors: YOLO and DETR",
                "quote": "YOLO is a single-stage detector.",
            }
        ],
    )

    assert answer.answer_markdown == "YOLO is covered in this unit."


def test_structured_router_composes_retrieval_refinement_with_llm():
    model = FakeChatModel()

    answer = StructuredAgentRouter(model=model).compose_retrieval_refinement(
        message="tìm thông tin về CNN",
        raw_topic="CNN",
        result_count=30,
        route_context=None,
    )

    assert "strongest results" in answer
    assert "many title-level learning units" in model.messages[0]["content"]
    assert "Do not mention examples, versions, subtypes" in model.messages[0]["content"]
    assert "The only allowed choices are" in model.messages[0]["content"]
    assert "Result count: 30" in model.messages[1]["content"]


class GenericRateLimitedModel:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        raise RuntimeError("upstream model rate limit 429")


def test_structured_router_maps_llm_errors_to_error_codes():
    with pytest.raises(AgentRouterUnavailableError) as exc:
        StructuredAgentRouter(model=GenericRateLimitedModel()).route(message="hello", route_context=None)

    assert exc.value.error_code == "AGENT_LLM_RATE_LIMIT"
