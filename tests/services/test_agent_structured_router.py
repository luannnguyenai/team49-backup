import pytest

from src.services.agent_graph_contracts import AgentRouterUnavailableError
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
    assert "quiz eligibility questions from assessment creation" in system_prompt
    assert "short title-level BM25 queries first" in system_prompt
    assert "try retrieval before asking about the desired angle" in system_prompt


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
