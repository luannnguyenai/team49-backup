import pytest

from src.services.replan_keyword_planner import ReplanKeywordPlanner


@pytest.mark.asyncio
async def test_faster_rcnn_keyword_plan_keeps_phrase_without_generic_expansion():
    planner = ReplanKeywordPlanner(use_llm=False)  # Use rule-based for tests
    plan = await planner.plan("Tôi biết Faster RCNN")

    assert "Faster R-CNN" in plan.search_queries
    assert "Faster RCNN" in plan.search_queries
    assert "R-CNN" in plan.do_not_expand_to
    assert "CNN" in plan.do_not_expand_to
    assert [keyword.text for keyword in plan.primary_keywords] == ["Faster R-CNN"]


@pytest.mark.asyncio
async def test_yolo_uncertain_is_not_selected_as_known_keyword():
    planner = ReplanKeywordPlanner(use_llm=False)
    plan = await planner.plan("Tôi biết Faster RCNN nhưng YOLO chưa chắc")

    assert [keyword.text for keyword in plan.primary_keywords] == ["Faster R-CNN"]
    assert [keyword.text for keyword in plan.negative_or_uncertain_keywords] == ["YOLO"]


@pytest.mark.asyncio
async def test_broad_claim_is_marked_broad_not_blocked():
    planner = ReplanKeywordPlanner(use_llm=False)
    plan = await planner.plan("Tôi biết object detection cơ bản")

    assert plan.specificity == "broad"
    assert plan.guardrail_flags == []
    assert "object detection" in plan.search_queries
