from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.schemas.replan import ReplanAssessmentUnitRequest
from src.services import replan_service
from src.services.replan_keyword_planner import ReplanKeyword, ReplanKeywordPlan


@pytest.mark.asyncio
async def test_analyze_replan_runs_guardrail_before_active_path_lookup(monkeypatch):
    async def fake_load_path_items(db, user_id_arg):
        raise AssertionError("path lookup should not run before blocking guardrails")

    class FakeKeywordPlanner:
        async def plan(self, claim):
            return ReplanKeywordPlan(
                primaryKeywords=[],
                searchQueries=[claim],
                specificity="specific",
                guardrailFlags=["skip_all"],
            )

    monkeypatch.setattr(replan_service, "_load_current_path_items", fake_load_path_items)
    monkeypatch.setattr(replan_service, "ReplanKeywordPlanner", FakeKeywordPlanner)

    response = await replan_service.analyze_replan(
        db=object(),
        user_id=uuid4(),
        claim="skip all",
    )

    assert response.status == "guardrail_blocked"
    assert response.popup.title == "Scope too broad"


@pytest.mark.asyncio
async def test_analyze_replan_returns_all_mastered_status_when_every_match_is_handled(monkeypatch):
    user_id = uuid4()
    learning_unit_id = uuid4()

    async def fake_load_path_items(db, user_id_arg):
        assert user_id_arg == user_id
        return [
            {
                "learning_unit_id": str(learning_unit_id),
                "canonical_unit_id": "unit_faster_rcnn",
            }
        ]

    async def fake_question_counts(db, canonical_unit_ids):
        return {"unit_faster_rcnn": {"easy": 1, "medium": 0, "hard": 0, "application": 0}}

    class FakeKeywordPlanner:
        async def plan(self, claim):
            return ReplanKeywordPlan(
                primaryKeywords=[
                    ReplanKeyword(
                        text="Faster R-CNN",
                        reason="User explicitly claimed Faster R-CNN knowledge.",
                        mustKeepPhrase=True,
                    )
                ],
                searchQueries=["Faster R-CNN"],
                specificity="specific",
            )

    class FakeContentRepo:
        def __init__(self, db):
            pass

        async def get_canonical_units_by_ids(self, ids):
            return {
                "unit_faster_rcnn": SimpleNamespace(
                    unit_name="Faster R-CNN",
                    summary="Two-stage object detector.",
                    key_points=["Region Proposal Network"],
                )
            }

    class FakePlacementRepo:
        def __init__(self, db):
            pass

        async def get_by_user_id(self, user_id_arg):
            return [SimpleNamespace(topic_unit_id=learning_unit_id, decision="skip")]

    monkeypatch.setattr(replan_service, "_load_current_path_items", fake_load_path_items)
    monkeypatch.setattr(replan_service, "_get_question_counts_by_difficulty", fake_question_counts)
    monkeypatch.setattr(replan_service, "ReplanKeywordPlanner", FakeKeywordPlanner)
    monkeypatch.setattr(replan_service, "CanonicalContentRepository", FakeContentRepo)
    monkeypatch.setattr(replan_service, "PlacementAssessmentRepository", FakePlacementRepo)

    response = await replan_service.analyze_replan(db=object(), user_id=user_id, claim="I know Faster R-CNN")

    assert response.status == "all_already_mastered"
    assert response.popup.kind == "all_already_mastered"
    assert "already marked as mastered" in response.popup.message


@pytest.mark.asyncio
async def test_analyze_replan_keeps_discovered_units_when_recommender_returns_empty_non_skip(monkeypatch):
    user_id = uuid4()
    learning_unit_id = uuid4()

    async def fake_load_path_items(db, user_id_arg):
        return [
            {
                "learning_unit_id": str(learning_unit_id),
                "canonical_unit_id": "unit_activation",
            }
        ]

    async def fake_question_counts(db, canonical_unit_ids):
        return {"unit_activation": {"easy": 2, "medium": 1, "hard": 0, "application": 0}}

    class FakeKeywordPlanner:
        async def plan(self, claim):
            return ReplanKeywordPlan(
                primaryKeywords=[
                    ReplanKeyword(
                        text="activation functions",
                        reason="User claimed activation function knowledge.",
                        mustKeepPhrase=True,
                    )
                ],
                searchQueries=["activation functions"],
                specificity="specific",
            )

    class FakeContentRepo:
        def __init__(self, db):
            pass

        async def get_canonical_units_by_ids(self, ids):
            return {
                "unit_activation": SimpleNamespace(
                    unit_name="Activation functions and their trade-offs",
                    summary="Activation functions and nonlinearities.",
                    key_points=["Activation functions and nonlinearities"],
                )
            }

        async def get_unit_kp_rows(self, ids):
            return []

        async def get_concepts_by_ids(self, ids):
            return {}

        async def get_prerequisite_edges_for_kps(self, ids):
            return []

    class FakePlacementRepo:
        def __init__(self, db):
            pass

        async def get_by_user_id(self, user_id_arg):
            return []

    class FakeRecommender:
        async def recommend(self, claim, available_units):
            return SimpleNamespace(recommendations=[], should_skip_all=False, skip_reason="")

    monkeypatch.setattr(replan_service, "_load_current_path_items", fake_load_path_items)
    monkeypatch.setattr(replan_service, "_get_question_counts_by_difficulty", fake_question_counts)
    monkeypatch.setattr(replan_service, "ReplanKeywordPlanner", FakeKeywordPlanner)
    monkeypatch.setattr(replan_service, "CanonicalContentRepository", FakeContentRepo)
    monkeypatch.setattr(replan_service, "PlacementAssessmentRepository", FakePlacementRepo)
    monkeypatch.setattr(replan_service, "get_unit_recommender", lambda: FakeRecommender())

    response = await replan_service.analyze_replan(
        db=object(),
        user_id=user_id,
        claim="I know activation functions",
    )

    assert response.status == "ready"
    assert [unit.canonical_unit_id for unit in response.units] == ["unit_activation"]


@pytest.mark.asyncio
async def test_analyze_replan_keeps_discovered_units_when_recommender_returns_unknown_ids(monkeypatch):
    user_id = uuid4()
    learning_unit_id = uuid4()

    async def fake_load_path_items(db, user_id_arg):
        return [
            {
                "learning_unit_id": str(learning_unit_id),
                "canonical_unit_id": "unit_activation",
            }
        ]

    async def fake_question_counts(db, canonical_unit_ids):
        return {"unit_activation": {"easy": 2, "medium": 1, "hard": 0, "application": 0}}

    class FakeKeywordPlanner:
        async def plan(self, claim):
            return ReplanKeywordPlan(
                primaryKeywords=[
                    ReplanKeyword(
                        text="activation function",
                        reason="User claimed activation function knowledge.",
                        mustKeepPhrase=True,
                    )
                ],
                searchQueries=["activation function"],
                specificity="specific",
            )

    class FakeContentRepo:
        def __init__(self, db):
            pass

        async def get_canonical_units_by_ids(self, ids):
            return {
                "unit_activation": SimpleNamespace(
                    unit_name="Activation functions and their trade-offs",
                    summary="Activation functions and nonlinearities.",
                    key_points=["Activation functions and nonlinearities"],
                )
            }

        async def get_unit_kp_rows(self, ids):
            return []

        async def get_concepts_by_ids(self, ids):
            return {}

        async def get_prerequisite_edges_for_kps(self, ids):
            return []

    class FakePlacementRepo:
        def __init__(self, db):
            pass

        async def get_by_user_id(self, user_id_arg):
            return []

    class FakeRecommender:
        async def recommend(self, claim, available_units):
            return SimpleNamespace(
                recommendations=[
                    SimpleNamespace(unit_id="activation_functions", reason="Hallucinated alias.")
                ],
                should_skip_all=False,
                skip_reason="",
            )

    monkeypatch.setattr(replan_service, "_load_current_path_items", fake_load_path_items)
    monkeypatch.setattr(replan_service, "_get_question_counts_by_difficulty", fake_question_counts)
    monkeypatch.setattr(replan_service, "ReplanKeywordPlanner", FakeKeywordPlanner)
    monkeypatch.setattr(replan_service, "CanonicalContentRepository", FakeContentRepo)
    monkeypatch.setattr(replan_service, "PlacementAssessmentRepository", FakePlacementRepo)
    monkeypatch.setattr(replan_service, "get_unit_recommender", lambda: FakeRecommender())

    response = await replan_service.analyze_replan(
        db=object(),
        user_id=user_id,
        claim="I know activation functions",
    )

    assert response.status == "ready"
    assert [unit.canonical_unit_id for unit in response.units] == ["unit_activation"]


@pytest.mark.asyncio
async def test_start_replan_assessment_returns_filtered_started_questions(monkeypatch):
    user_id = uuid4()

    class FakeContentRepo:
        def __init__(self, db):
            pass

        async def get_canonical_units_by_ids(self, ids):
            return {
                "unit_rcnn": SimpleNamespace(unit_name="R-CNN"),
            }

    async def fake_start_assessment(*args, **kwargs):
        return SimpleNamespace(
            session_id=uuid4(),
            questions=[
                SimpleNamespace(
                    id=None,
                    item_id="easy-1",
                    canonical_item_id="easy-1",
                    canonical_unit_id="unit_rcnn",
                    topic_id=None,
                    bloom_level=None,
                    difficulty_bucket=SimpleNamespace(value="easy"),
                    stem_text="Easy question",
                    option_a="A",
                    option_b="B",
                    option_c="C",
                    option_d="D",
                    time_expected_seconds=30,
                ),
                SimpleNamespace(
                    id=None,
                    item_id="hard-1",
                    canonical_item_id="hard-1",
                    canonical_unit_id="unit_rcnn",
                    topic_id=None,
                    bloom_level=None,
                    difficulty_bucket=SimpleNamespace(value="hard"),
                    stem_text="Hard question",
                    option_a="A",
                    option_b="B",
                    option_c="C",
                    option_d="D",
                    time_expected_seconds=30,
                ),
            ],
        )

    monkeypatch.setattr(replan_service, "CanonicalContentRepository", FakeContentRepo)
    monkeypatch.setattr(replan_service, "start_assessment", fake_start_assessment)

    response = await replan_service.start_replan_assessment(
        db=object(),
        user_id=user_id,
        selected_units=[
            ReplanAssessmentUnitRequest(canonicalUnitId="unit_rcnn", difficultyFilter="easy"),
        ],
    )

    assert response.total_questions == 1
    assert [question.canonical_item_id for question in response.questions] == ["easy-1"]
