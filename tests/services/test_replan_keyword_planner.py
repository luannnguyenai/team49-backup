from src.services.replan_keyword_planner import ReplanKeywordPlanner


def test_faster_rcnn_keyword_plan_keeps_phrase_without_generic_expansion():
    plan = ReplanKeywordPlanner().plan("Tôi biết Faster RCNN")

    assert "Faster R-CNN" in plan.search_queries
    assert "Faster RCNN" in plan.search_queries
    assert "R-CNN" in plan.do_not_expand_to
    assert "CNN" in plan.do_not_expand_to
    assert [keyword.text for keyword in plan.primary_keywords] == ["Faster R-CNN"]


def test_yolo_uncertain_is_not_selected_as_known_keyword():
    plan = ReplanKeywordPlanner().plan("Tôi biết Faster RCNN nhưng YOLO chưa chắc")

    assert [keyword.text for keyword in plan.primary_keywords] == ["Faster R-CNN"]
    assert [keyword.text for keyword in plan.negative_or_uncertain_keywords] == ["YOLO"]


def test_broad_claim_is_marked_broad_not_blocked():
    plan = ReplanKeywordPlanner().plan("Tôi biết object detection cơ bản")

    assert plan.specificity == "broad"
    assert plan.guardrail_flags == []
    assert "object detection" in plan.search_queries
