from types import SimpleNamespace
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


@pytest.mark.asyncio
async def test_lecture_context_falls_back_to_slot_unit_when_model_argument_is_bad():
    calls = []

    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            calls.append(canonical_unit_id)
            if canonical_unit_id != "slot-current":
                return None
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": None,
                "source": "unit_summaries",
                "units": [
                    {
                        "canonical_unit_id": "slot-current",
                        "course_id": "CS230",
                        "lecture_id": "lecture-02",
                        "lecture_title": "Lecture 2",
                        "unit_name": "Day & Night classification",
                        "summary": "Day/night classification design summary.",
                    }
                ],
            }

    tools = AgentToolNodes(SimpleNamespace(repo=Repo()), requirement_service=None)

    result = await tools.lecture_context(
        message="tóm tắt video này",
        slots=AgentSlots(canonical_unit_ids=["slot-current"]),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
        canonical_unit_id="lecture-02-supervised-learning",
    )

    assert calls == ["lecture-02-supervised-learning", "slot-current"]
    assert result.citations[0].canonical_unit_id == "slot-current"


@pytest.mark.asyncio
async def test_lecture_context_keeps_allowed_courses_when_current_path_scope_is_alias():
    scopes = []

    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            scopes.append(list(allowed_course_ids))
            if "CS230" not in allowed_course_ids:
                return None
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": None,
                "source": "unit_summaries",
                "units": [
                    {
                        "canonical_unit_id": canonical_unit_id,
                        "course_id": "CS230",
                        "lecture_id": "lecture-02",
                        "lecture_title": "Lecture 2",
                        "unit_name": "Neurons",
                        "summary": "Neural-network notation and embeddings.",
                    }
                ],
            }

    tools = AgentToolNodes(SimpleNamespace(repo=Repo()), requirement_service=None)

    result = await tools.lecture_context(
        message="tóm tắt video gần nhất",
        slots=AgentSlots(),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["computer_vision"],
        canonical_unit_id="unit-neurons",
    )

    assert scopes == [["computer_vision", "CS230"]]
    assert result.citations[0].quote == "Neural-network notation and embeddings."


@pytest.mark.asyncio
async def test_lecture_context_default_scope_filters_to_learned_units():
    learned_calls = []

    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": None,
                "source": "unit_summaries",
                "units": [
                    {"canonical_unit_id": "seg1", "course_id": "CS230", "unit_name": "Seg 1", "summary": "s1"},
                    {"canonical_unit_id": "seg2", "course_id": "CS230", "unit_name": "Seg 2", "summary": "s2"},
                    {"canonical_unit_id": "seg3", "course_id": "CS230", "unit_name": "Seg 3", "summary": "s3"},
                ],
            }

    class FakeUserLearningContextService:
        async def learned_canonical_unit_ids(self, user_id, course_ids):
            learned_calls.append((user_id, list(course_ids)))
            return {"seg1", "seg2"}

    tools = AgentToolNodes(
        SimpleNamespace(repo=Repo()),
        requirement_service=None,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        user_learning_context_service=FakeUserLearningContextService(),
    )

    result = await tools.lecture_context(
        message="tóm tắt video tôi mới học",
        slots=AgentSlots(),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
        canonical_unit_id="seg2",
    )

    assert learned_calls == [(UUID("00000000-0000-0000-0000-000000000001"), ["CS230"])]
    citation_ids = [c.canonical_unit_id for c in result.citations]
    assert citation_ids == ["seg1", "seg2"]
    assert result.metadata["lecture_scope"] == "learned"
    assert result.metadata["lecture_scope_applied"] is True
    assert result.metadata["lecture_scope_total_units"] == 3
    assert result.metadata["lecture_scope_learned_units"] == 2


@pytest.mark.asyncio
async def test_lecture_context_scope_all_returns_full_lecture():
    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": None,
                "source": "unit_summaries",
                "units": [
                    {"canonical_unit_id": "seg1", "course_id": "CS230", "unit_name": "Seg 1", "summary": "s1"},
                    {"canonical_unit_id": "seg2", "course_id": "CS230", "unit_name": "Seg 2", "summary": "s2"},
                    {"canonical_unit_id": "seg3", "course_id": "CS230", "unit_name": "Seg 3", "summary": "s3"},
                ],
            }

    class FakeUserLearningContextService:
        async def learned_canonical_unit_ids(self, user_id, course_ids):
            raise AssertionError("scope=all must not query learned units")

    tools = AgentToolNodes(
        SimpleNamespace(repo=Repo()),
        requirement_service=None,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        user_learning_context_service=FakeUserLearningContextService(),
    )

    result = await tools.lecture_context(
        message="tóm tắt toàn bộ lecture này",
        slots=AgentSlots(),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
        canonical_unit_id="seg2",
        scope="all",
    )

    citation_ids = [c.canonical_unit_id for c in result.citations]
    assert citation_ids == ["seg1", "seg2", "seg3"]
    assert result.metadata["lecture_scope"] == "all"
    assert result.metadata["lecture_scope_applied"] is False


@pytest.mark.asyncio
async def test_lecture_context_scope_all_invokes_aggregator_when_lecture_summary_is_missing():
    captured = []

    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": None,
                "source": "unit_summaries",
                "units": [
                    {"canonical_unit_id": "seg1", "course_id": "CS230", "unit_name": "Seg 1", "summary": "s1"},
                    {"canonical_unit_id": "seg2", "course_id": "CS230", "unit_name": "Seg 2", "summary": "s2"},
                ],
            }

    class FakeAggregator:
        async def aggregate(self, *, lecture_title, units, language_hint=None):
            captured.append({"lecture_title": lecture_title, "units": units, "language_hint": language_hint})
            return "Lecture-level synthesis from unit summaries."

    tools = AgentToolNodes(
        SimpleNamespace(repo=Repo()),
        requirement_service=None,
        lecture_summary_aggregator=FakeAggregator(),
    )

    result = await tools.lecture_context(
        message="tóm tắt toàn bộ lecture này",
        slots=AgentSlots(),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
        canonical_unit_id="seg1",
        scope="all",
    )

    assert result.metadata["lecture_aggregated_summary_status"] == "ready"
    assert result.metadata["lecture_context"]["aggregated_summary"].startswith("Lecture-level")
    assert result.metadata["lecture_context"]["source"] == "aggregated_unit_summaries"
    assert captured[0]["lecture_title"] == "Lecture 2"


@pytest.mark.asyncio
async def test_lecture_context_scope_all_does_not_invoke_aggregator_when_lecture_summary_exists():
    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": "Authoritative lecture summary from database.",
                "source": "lecture_description",
                "units": [
                    {"canonical_unit_id": "seg1", "course_id": "CS230", "unit_name": "Seg 1", "summary": "s1"},
                ],
            }

    class FakeAggregator:
        async def aggregate(self, *, lecture_title, units, language_hint=None):
            raise AssertionError("aggregator must not run when a DB lecture summary exists")

    tools = AgentToolNodes(
        SimpleNamespace(repo=Repo()),
        requirement_service=None,
        lecture_summary_aggregator=FakeAggregator(),
    )

    result = await tools.lecture_context(
        message="tóm tắt toàn bộ lecture này",
        slots=AgentSlots(),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
        canonical_unit_id="seg1",
        scope="all",
    )

    assert "lecture_aggregated_summary_status" not in result.metadata
    assert result.metadata["lecture_context"]["lecture_summary"].startswith("Authoritative")


@pytest.mark.asyncio
async def test_lecture_context_scope_learned_does_not_invoke_aggregator():
    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": None,
                "source": "unit_summaries",
                "units": [
                    {"canonical_unit_id": "seg1", "course_id": "CS230", "unit_name": "Seg 1", "summary": "s1"},
                ],
            }

    class FakeAggregator:
        async def aggregate(self, *, lecture_title, units, language_hint=None):
            raise AssertionError("aggregator must not run for scope=learned")

    class FakeUserLearningContextService:
        async def learned_canonical_unit_ids(self, user_id, course_ids):
            return {"seg1"}

    tools = AgentToolNodes(
        SimpleNamespace(repo=Repo()),
        requirement_service=None,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        user_learning_context_service=FakeUserLearningContextService(),
        lecture_summary_aggregator=FakeAggregator(),
    )

    result = await tools.lecture_context(
        message="tóm tắt video tôi mới học",
        slots=AgentSlots(),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
        canonical_unit_id="seg1",
    )

    assert "lecture_aggregated_summary_status" not in result.metadata


@pytest.mark.asyncio
async def test_lecture_context_learned_scope_falls_back_when_no_learned_units():
    class Repo:
        async def get_lecture_context_for_unit(self, canonical_unit_id, *, allowed_course_ids):
            return {
                "course_id": "CS230",
                "lecture_id": "lecture-02",
                "lecture_title": "Lecture 2",
                "lecture_summary": None,
                "source": "unit_summaries",
                "units": [
                    {"canonical_unit_id": "seg1", "course_id": "CS230", "unit_name": "Seg 1", "summary": "s1"},
                    {"canonical_unit_id": "seg2", "course_id": "CS230", "unit_name": "Seg 2", "summary": "s2"},
                ],
            }

    class FakeUserLearningContextService:
        async def learned_canonical_unit_ids(self, user_id, course_ids):
            return set()

    tools = AgentToolNodes(
        SimpleNamespace(repo=Repo()),
        requirement_service=None,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        user_learning_context_service=FakeUserLearningContextService(),
    )

    result = await tools.lecture_context(
        message="tóm tắt video tôi mới học",
        slots=AgentSlots(),
        allowed_course_ids=["CS230"],
        current_path_course_ids=["CS230"],
        canonical_unit_id="seg1",
    )

    citation_ids = [c.canonical_unit_id for c in result.citations]
    assert citation_ids == ["seg1", "seg2"]
    assert result.metadata["lecture_scope"] == "learned"
    assert result.metadata["lecture_scope_fallback"] == "no_learned_units"
    assert result.metadata["lecture_scope_applied"] is False


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
async def test_find_content_answers_broad_direct_matches_without_topic_choice_cards():
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

    assert result.kind == "find_content"
    assert [citation.canonical_unit_id for citation in result.citations] == [
        "unit-cnn-vision",
        "unit-cnn-nlp",
    ]
    assert not [action for action in result.actions if action.type == "choose_topic"]
    assert result.metadata["evidence_verdict"] == "direct_match"


@pytest.mark.asyncio
async def test_find_content_too_many_results_preserves_top_five_candidate_source_cards():
    tools = AgentToolNodes(
        FakeSearchService(
            [
                UnitSearchResult(
                    canonical_unit_id=f"unit-cnn-{index}",
                    course_id="CS231n",
                    lecture_title=f"Lecture {index}: CNNs",
                    unit_name=f"CNN result {index}",
                    summary=f"CNN summary {index}.",
                    learn_href=f"/courses/cs231n/learn/cnn-{index}",
                    score=3,
                )
                for index in range(25)
            ]
        ),
        requirement_service=None,
    )

    result = await tools.find_content(
        "Where should I review CNNs?",
        "find_content",
        AgentSlots(raw_topic="CNNs", search_queries=["CNNs"]),
        ["CS231n"],
    )

    assert result.metadata["too_many_results_offered"] is True
    assert [citation.canonical_unit_id for citation in result.citations] == [
        "unit-cnn-0",
        "unit-cnn-1",
        "unit-cnn-2",
        "unit-cnn-3",
        "unit-cnn-4",
    ]
    assert [action.canonical_unit_id for action in result.actions] == [
        "unit-cnn-0",
        "unit-cnn-1",
        "unit-cnn-2",
        "unit-cnn-3",
        "unit-cnn-4",
    ]


@pytest.mark.asyncio
async def test_find_content_searches_all_allowed_courses_with_current_path_preference():
    captured = {}

    class SearchService:
        async def search(self, request, allowed_course_ids):
            captured["request"] = request
            captured["allowed_course_ids"] = allowed_course_ids
            return UnitSearchResponse(
                results=[
                    UnitSearchResult(
                        canonical_unit_id="vision-cnn",
                        course_id="CS231n",
                        lecture_title="Lecture 5: Image Classification with CNNs",
                        unit_name="CNN foundations",
                        summary="Vision CNN content.",
                        learn_href="/courses/cs231n/learn/cnn",
                        score=5,
                        outside_current_path=True,
                    ),
                    UnitSearchResult(
                        canonical_unit_id="nlp-cnn",
                        course_id="CS224n",
                        lecture_title="Lecture 16 - ConvNets and TreeRNNs",
                        unit_name="CNN for sentence classification",
                        summary="NLP CNN content.",
                        learn_href="/courses/cs224n/learn/cnn",
                        score=4,
                    ),
                ],
                trace=RetrievalTrace(trace_id="trace-all-allowed", ranking_version="unit_title_rerank_v2"),
            )

    tools = AgentToolNodes(SearchService(), requirement_service=None)

    result = await tools.find_content(
        "Where should I review CNNs?",
        "find_content",
        AgentSlots(
            raw_topic="CNNs",
            search_queries=["CNNs"],
            search_scope="current_path",
            resolved_search_path_ids=["nlp"],
        ),
        ["CS224n", "CS231n"],
        current_path_course_ids=["CS224n"],
    )

    request = captured["request"]
    assert request.course_ids == ["CS224n", "CS231n"]
    assert request.current_path_course_ids == ["CS224n"]
    assert request.preferred_course_ids == ["CS224n"]
    assert result.warning is not None
    assert result.warning.type == "outside_current_path"
    assert [citation.canonical_unit_id for citation in result.citations] == [
        "vision-cnn",
        "nlp-cnn",
    ]
