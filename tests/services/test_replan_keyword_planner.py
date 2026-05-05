import pytest

from src.services.replan_keyword_planner import ReplanKeywordPlan, ReplanKeywordPlanner


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


@pytest.mark.asyncio
async def test_compact_claim_is_not_blocked_when_llm_marks_too_short(monkeypatch):
    planner = ReplanKeywordPlanner(use_llm=True)

    async def fake_llm_plan(claim: str) -> ReplanKeywordPlan:
        return ReplanKeywordPlan(
            primaryKeywords=[],
            searchQueries=[claim],
            specificity="specific",
            guardrailFlags=["too_short"],
        )

    monkeypatch.setattr(planner, "_plan_with_llm", fake_llm_plan)

    plan = await planner.plan("bert")

    assert plan.guardrail_flags == []
    assert [keyword.text for keyword in plan.primary_keywords] == ["bert"]
    assert plan.search_queries == ["bert"]


@pytest.mark.asyncio
async def test_one_character_claim_stays_too_short_when_llm_marks_too_short(monkeypatch):
    planner = ReplanKeywordPlanner(use_llm=True)

    async def fake_llm_plan(claim: str) -> ReplanKeywordPlan:
        return ReplanKeywordPlan(
            primaryKeywords=[],
            searchQueries=[claim],
            specificity="specific",
            guardrailFlags=["too_short"],
        )

    monkeypatch.setattr(planner, "_plan_with_llm", fake_llm_plan)

    plan = await planner.plan("r")

    assert plan.guardrail_flags == ["too_short"]
    assert plan.primary_keywords == []
