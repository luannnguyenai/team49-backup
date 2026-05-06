from uuid import UUID

import pytest

from src.schemas.agent import (
    AgentPrerequisitePath,
    AgentPrerequisitePathEdge,
    AgentPrerequisitePathNode,
    RetrievalTrace,
    UnitSearchResponse,
    UnitSearchResult,
)
from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_tool_nodes import AgentToolNodes


class FakeSearchService:
    def __init__(self, results):
        self.results = results

    async def search(self, request, allowed_course_ids):
        return UnitSearchResponse(
            results=self.results,
            trace=RetrievalTrace(
                trace_id="trace-1",
                intent=request.intent,
                raw_query=request.query,
                selected_unit_ids=[result.canonical_unit_id for result in self.results],
                ranking_version="unit_title_search_v1",
            ),
        )


class FakePrerequisitePathService:
    def __init__(self):
        self.calls = []

    async def build(self, **kwargs):
        self.calls.append(kwargs)
        return AgentPrerequisitePath(
            targetCanonicalUnitId=kwargs["target_canonical_unit_id"],
            nodes=[
                AgentPrerequisitePathNode(
                    canonicalUnitId="unit-prereq",
                    unitName="R-CNN family",
                    role="prerequisite",
                    status="needs_review",
                ),
                AgentPrerequisitePathNode(
                    canonicalUnitId=kwargs["target_canonical_unit_id"],
                    unitName="Mask R-CNN",
                    role="target",
                    status="target",
                ),
            ],
            edges=[
                AgentPrerequisitePathEdge(
                    fromCanonicalUnitId="unit-prereq",
                    toCanonicalUnitId=kwargs["target_canonical_unit_id"],
                    reason="R-CNN family -> Mask R-CNN",
                )
            ],
        )


@pytest.mark.asyncio
async def test_find_content_adds_prerequisite_path_action_for_specific_target():
    prereq_service = FakePrerequisitePathService()
    tools = AgentToolNodes(
        FakeSearchService(
            [
                UnitSearchResult(
                    canonical_unit_id="unit-target",
                    course_id="CS231n",
                    unit_name="Instance segmentation with Mask R-CNN",
                    summary="Mask R-CNN predicts instance masks.",
                    learn_href="/learn/mask-r-cnn",
                    score=8,
                ),
                UnitSearchResult(
                    canonical_unit_id="unit-prereq",
                    course_id="CS231n",
                    unit_name="Object detection as classification plus localization and the R-CNN family",
                    summary="R-CNN uses region proposals.",
                    learn_href="/learn/rcnn",
                    score=4,
                ),
            ]
        ),
        requirement_service=None,
        prerequisite_path_service=prereq_service,
        user_id=UUID("f2a9c00c-0a62-56cc-895d-5ab78de222f8"),
    )

    result = await tools.find_content(
        "Explain Mask R-CNN",
        "explain_concept",
        AgentSlots(raw_topic="Mask R-CNN", search_queries=["Mask R-CNN"]),
        ["CS231n"],
    )

    prereq_actions = [action for action in result.actions if action.type == "review_prerequisite_path"]
    assert len(prereq_actions) == 1
    assert prereq_actions[0].canonical_unit_ids == ["unit-prereq", "unit-target"]
    assert prereq_actions[0].prerequisite_path is not None
    assert prereq_service.calls[0]["target_canonical_unit_id"] == "unit-target"
    assert prereq_service.calls[0]["user_id"] == UUID("f2a9c00c-0a62-56cc-895d-5ab78de222f8")


@pytest.mark.asyncio
async def test_find_content_does_not_run_prerequisite_path_for_broad_tied_results():
    prereq_service = FakePrerequisitePathService()
    tools = AgentToolNodes(
        FakeSearchService(
            [
                UnitSearchResult(
                    canonical_unit_id="unit-a",
                    course_id="CS231n",
                    unit_name="CNN foundations",
                    summary="CNN foundations.",
                    score=4,
                ),
                UnitSearchResult(
                    canonical_unit_id="unit-b",
                    course_id="CS224n",
                    unit_name="Kim CNN for sentence classification",
                    summary="NLP CNN.",
                    score=4,
                ),
            ]
        ),
        requirement_service=None,
        prerequisite_path_service=prereq_service,
        user_id=UUID("f2a9c00c-0a62-56cc-895d-5ab78de222f8"),
    )

    result = await tools.find_content(
        "Explain CNN",
        "explain_concept",
        AgentSlots(raw_topic="CNN", search_queries=["CNN"]),
        ["CS231n", "CS224n"],
    )

    assert not [action for action in result.actions if action.type == "review_prerequisite_path"]
    assert prereq_service.calls == []


@pytest.mark.asyncio
async def test_find_content_offers_topic_choices_for_broad_direct_matches():
    tools = AgentToolNodes(
        FakeSearchService(
            [
                UnitSearchResult(
                    canonical_unit_id="unit-cnn-vision",
                    course_id="CS231n",
                    unit_name="CNN foundations for vision",
                    summary="CNN content.",
                    score=4,
                ),
                UnitSearchResult(
                    canonical_unit_id="unit-cnn-nlp",
                    course_id="CS224n",
                    unit_name="CNNs for sentence classification",
                    summary="CNN content.",
                    score=4,
                ),
            ]
        ),
        requirement_service=None,
    )

    result = await tools.find_content(
        "Explain CNN",
        "explain_concept",
        AgentSlots(raw_topic="CNN", search_queries=["CNN"]),
        ["CS231n", "CS224n"],
    )

    assert result.kind == "clarification"
    assert "Choose one below" in result.answer_markdown
    assert [action.type for action in result.actions] == ["choose_topic", "choose_topic"]
    assert [action.canonical_unit_id for action in result.actions] == ["unit-cnn-vision", "unit-cnn-nlp"]
    assert result.metadata["topic_selection_offered"] is True
