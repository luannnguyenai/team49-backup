import os

import pytest

from src.services.agent_router_factory import build_production_agent_router


@pytest.mark.parametrize(
    ("message", "not_intent"),
    [
        ("Giải thích skip connection", "request_replan"),
        ("Quiz eligibility của unit này tính thế nào?", "assess_knowledge"),
        ("next token prediction là gì", "ask_what_next"),
        ("cho tôi replan, nhưng đừng skip phần attention", "assess_knowledge"),
        ("Tôi muốn chuyển từ CV sang NLP.", "find_content"),
        ("Trong path NLP có bài nào về attention mask không?", "request_path_switch"),
    ],
)
@pytest.mark.skipif(
    os.getenv("RUN_AGENT_ROUTER_EVAL") != "1",
    reason="Set RUN_AGENT_ROUTER_EVAL=1 to call the configured production router model.",
)
def test_adversarial_routing_does_not_follow_keyword_traps(message, not_intent):
    route = build_production_agent_router().route(message=message, route_context=None)

    assert route.intent != not_intent
