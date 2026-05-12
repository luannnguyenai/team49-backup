from scripts.benchmark_agent_router_strategies import (
    BenchmarkCase,
    CompactRouteOutput,
    deterministic_content_route,
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
