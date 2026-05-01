import pytest

from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_structured_router import StructuredAgentRouter


class FakeStructuredModel:
    def __init__(self, payload):
        self.payload = payload
        self.schema = None
        self.messages = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.messages = messages
        return self.schema(**self.payload)


def test_structured_router_returns_explicit_path_route():
    model = FakeStructuredModel(
        {
            "intent": "find_content",
            "confidence": 0.91,
            "raw_topic": "attention mask",
            "target_path": "nlp",
            "rationale": "User explicitly asked for NLP content.",
        }
    )

    route = StructuredAgentRouter(model=model).route(
        message="Trong path NLP có bài nào về attention mask không?",
        route_context=None,
    )

    assert route.intent == "find_content"
    assert route.extracted_slots.raw_topic == "attention mask"
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
    assert "where should I review" in system_prompt


class FakeChatModel:
    def with_structured_output(self, schema):
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

    assert answer == "I can help you find content and plan reviews."
    assert "Use only these retrieved learning units" in model.messages[0]["content"]
    assert "Where should I review CNNs?" in model.messages[1]["content"]


class GenericRateLimitedModel:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        raise RuntimeError("upstream model rate limit 429")


def test_structured_router_maps_llm_errors_to_error_codes():
    with pytest.raises(AgentRouterUnavailableError) as exc:
        StructuredAgentRouter(model=GenericRateLimitedModel()).route(message="hello", route_context=None)

    assert exc.value.error_code == "AGENT_LLM_RATE_LIMIT"
