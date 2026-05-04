from src.services.replan_keyword_planner import ReplanKeywordPlan, ReplanKeyword
from src.services.replan_unit_discovery import ReplanCurrentPathUnitDiscovery, ReplanUnitCandidate


def test_current_path_discovery_excludes_out_of_path_units():
    discovery = ReplanCurrentPathUnitDiscovery()
    candidates = [
        ReplanUnitCandidate(
            canonical_unit_id="unit_faster_rcnn",
            title="Faster R-CNN",
            summary="Two-stage object detection with region proposal networks.",
            key_points=["Region Proposal Network"],
            path_order=12,
            question_counts={"easy": 3, "medium": 4, "hard": 2, "application": 1},
            in_current_path=True,
        ),
        ReplanUnitCandidate(
            canonical_unit_id="unit_outside",
            title="Faster R-CNN in another path",
            summary="Out of path content.",
            key_points=[],
            path_order=99,
            question_counts={"easy": 3, "medium": 0, "hard": 0, "application": 0},
            in_current_path=False,
        ),
    ]

    result = discovery.discover(_plan(), candidates)

    assert [unit.canonical_unit_id for unit in result.selected_units] == ["unit_faster_rcnn"]
    assert [unit.canonical_unit_id for unit in result.dropped_units] == ["unit_outside"]


def test_current_path_discovery_respects_do_not_expand_to():
    discovery = ReplanCurrentPathUnitDiscovery()
    candidates = [
        ReplanUnitCandidate(
            canonical_unit_id="unit_rcnn",
            title="R-CNN",
            summary="Generic R-CNN precursor.",
            key_points=["Selective search"],
            path_order=10,
            question_counts={"easy": 3, "medium": 2, "hard": 0, "application": 0},
            in_current_path=True,
        ),
        ReplanUnitCandidate(
            canonical_unit_id="unit_cnn",
            title="CNN foundations",
            summary="Convolutional neural networks.",
            key_points=["Convolution"],
            path_order=1,
            question_counts={"easy": 5, "medium": 2, "hard": 0, "application": 0},
            in_current_path=True,
        ),
    ]

    result = discovery.discover(_plan(), candidates)

    assert result.selected_units == []
    assert {unit.reason for unit in result.excluded_units} == {
        "Matched only a forbidden expansion keyword.",
    }


def test_current_path_discovery_drops_units_without_questions():
    discovery = ReplanCurrentPathUnitDiscovery()
    candidates = [
        ReplanUnitCandidate(
            canonical_unit_id="unit_faster_rcnn",
            title="Faster R-CNN",
            summary="Two-stage object detection.",
            key_points=[],
            path_order=12,
            question_counts={"easy": 0, "medium": 0, "hard": 0, "application": 0},
            in_current_path=True,
        ),
    ]

    result = discovery.discover(_plan(), candidates)

    assert result.selected_units == []
    assert result.dropped_units[0].reason == "No assessment questions available."


def test_current_path_discovery_filters_already_handled_units_by_default():
    discovery = ReplanCurrentPathUnitDiscovery()
    candidates = [
        ReplanUnitCandidate(
            canonical_unit_id="unit_faster_rcnn",
            title="Faster R-CNN",
            summary="Two-stage object detection.",
            key_points=[],
            path_order=12,
            question_counts={"easy": 3, "medium": 0, "hard": 0, "application": 0},
            in_current_path=True,
            already_handled=True,
        ),
    ]

    result = discovery.discover(_plan(), candidates)

    assert result.selected_units == []
    assert result.dropped_units[0].reason == "Unit is already mastered or skipped."


def _plan() -> ReplanKeywordPlan:
    return ReplanKeywordPlan(
        primaryKeywords=[
            ReplanKeyword(
                text="Faster R-CNN",
                reason="User explicitly claims Faster RCNN knowledge.",
                mustKeepPhrase=True,
            )
        ],
        searchQueries=["Faster R-CNN", "Faster RCNN"],
        doNotExpandTo=["R-CNN", "CNN"],
        specificity="specific",
    )
