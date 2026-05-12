from scripts.benchmark_agent_router_strategies import (
    BenchmarkCase,
    CompactRouteOutput,
    build_compact_router_messages,
    default_strategy_names,
    deterministic_content_fast_path,
    deterministic_content_route,
    needs_compact_model,
    route_quality,
)


def test_deterministic_content_route_extracts_named_topic():
    case = BenchmarkCase(
        name="mask_rcnn_detail",
        message="cho tôi thông tin cụ thể hơn về Mask R-CNN",
        expected_intent="find_content",
        expected_topic_contains="Mask R-CNN",
    )

    result = deterministic_content_route(case)

    assert result.intent == "find_content"
    assert result.topic == "Mask R-CNN"
    assert result.confidence >= 0.8


def test_deterministic_content_route_uses_active_topic_for_short_followup():
    case = BenchmarkCase(
        name="short_followup",
        message="kiến trúc chi tiết hơn",
        active_topic="Mask R-CNN",
        expected_intent="find_content",
        expected_topic_contains="Mask R-CNN",
    )

    result = deterministic_content_route(case)

    assert result.intent == "find_content"
    assert result.topic == "Mask R-CNN kiến trúc chi tiết hơn"


def test_content_fast_path_leaves_control_actions_for_compact_router():
    case = BenchmarkCase(
        name="request_replan",
        message="tôi đã biết CNN rồi, tối ưu lại lộ trình cho tôi",
        expected_intent="request_replan",
    )

    result = deterministic_content_fast_path(case)

    assert result is None


def test_default_strategies_use_fast_model_router_two_baseline():
    strategies = default_strategy_names()

    assert "baseline_fast_model" in strategies
    assert "baseline_0_8b" in strategies
    assert "compact_all" in strategies
    assert "compact_labeled_all" in strategies
    assert "compact_decision_table_all" in strategies
    assert "compact_fewshot_all" in strategies
    assert "deterministic" not in strategies
    assert needs_compact_model(strategies) is True


def test_labeled_compact_prompt_defines_control_actions():
    case = BenchmarkCase(
        name="request_replan",
        message="tôi đã biết CNN rồi, tối ưu lại lộ trình cho tôi",
        expected_intent="request_replan",
    )

    messages = build_compact_router_messages(case, labeled=True)

    system_prompt = messages[0]["content"]
    assert "request_replan" in system_prompt
    assert "request_path_switch" in system_prompt
    assert "assess_knowledge" in system_prompt


def test_decision_table_prompt_prioritizes_control_actions():
    case = BenchmarkCase(
        name="path_switch",
        message="chuyển tôi sang lộ trình NLP",
        expected_intent="request_path_switch",
    )

    messages = build_compact_router_messages(case, variant="decision_table")

    system_prompt = messages[0]["content"]
    assert "Priority order" in system_prompt
    assert "request_path_switch" in system_prompt
    assert "Do not classify path changes as navigate_to_unit" in system_prompt


def test_fewshot_prompt_contains_expected_json_examples():
    case = BenchmarkCase(
        name="assessment",
        message="quiz me on object detection",
        expected_intent="assess_knowledge",
    )

    messages = build_compact_router_messages(case, variant="fewshot")

    system_prompt = messages[0]["content"]
    assert '{"intent":"assess_knowledge"' in system_prompt
    assert '{"intent":"request_replan"' in system_prompt


def test_route_quality_scores_expected_intent_and_topic():
    case = BenchmarkCase(
        name="quality",
        message="Explain Mask R-CNN",
        expected_intent="find_content",
        expected_topic_contains="Mask R-CNN",
    )
    output = CompactRouteOutput(
        intent="find_content",
        topic="Mask R-CNN",
        confidence=0.9,
        clarify=None,
    )

    quality = route_quality(case, output)

    assert quality["intent_ok"] is True
    assert quality["topic_ok"] is True
    assert quality["score"] == 1.0
