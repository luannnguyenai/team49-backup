from src.services.agent_graph_router import DeterministicAgentRouter


def test_deterministic_router_treats_skip_connection_as_concept():
    route = DeterministicAgentRouter().route("Giải thích skip connection", route_context=None)

    assert route.intent == "explain_concept"


def test_deterministic_router_does_not_create_assessment_for_quiz_eligibility():
    route = DeterministicAgentRouter().route("Quiz eligibility của unit này tính thế nào?", None)

    assert route.intent == "general_course_question"


def test_deterministic_router_path_switch_is_separate_intent():
    route = DeterministicAgentRouter().route("Tôi muốn chuyển từ CV sang NLP.", None)

    assert route.intent == "request_path_switch"
    assert route.extracted_slots.target_path == "nlp"
