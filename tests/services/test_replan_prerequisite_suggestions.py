from src.services.replan_prerequisite_suggestions import (
    ReplanPrerequisiteSuggester,
    ReplanPrerequisiteUnit,
)


def test_prerequisite_suggestions_are_current_path_only_and_filtered():
    suggester = ReplanPrerequisiteSuggester(
        prerequisite_edges={
            "unit_faster_rcnn": ["unit_fast_rcnn", "unit_outside"],
            "unit_fast_rcnn": ["unit_rcnn", "unit_mastered"],
        },
    )
    units = {
        "unit_fast_rcnn": _unit("unit_fast_rcnn", "Fast R-CNN", 11, True),
        "unit_rcnn": _unit("unit_rcnn", "R-CNN", 10, True),
        "unit_outside": _unit("unit_outside", "Outside path", 99, False),
        "unit_mastered": _unit("unit_mastered", "Already mastered", 9, True, handled=True),
    }

    suggestions = suggester.suggest(["unit_faster_rcnn"], units, max_depth=2)

    assert [suggestion.canonical_unit_id for suggestion in suggestions] == [
        "unit_fast_rcnn",
        "unit_rcnn",
    ]
    assert suggestions[0].suggested_for_canonical_unit_id == "unit_faster_rcnn"


def test_prerequisite_suggestions_are_bounded_and_deduplicated():
    suggester = ReplanPrerequisiteSuggester(
        prerequisite_edges={
            "unit_a": ["unit_shared", "unit_b", "unit_c"],
            "unit_b": ["unit_shared"],
        },
    )
    units = {
        "unit_shared": _unit("unit_shared", "Shared foundation", 1, True),
        "unit_b": _unit("unit_b", "B", 2, True),
        "unit_c": _unit("unit_c", "C", 3, True),
    }

    suggestions = suggester.suggest(["unit_a"], units, max_depth=2, max_suggestions=2)

    assert [suggestion.canonical_unit_id for suggestion in suggestions] == ["unit_shared", "unit_b"]


def _unit(
    canonical_unit_id: str,
    title: str,
    path_order: int,
    in_current_path: bool,
    handled: bool = False,
) -> ReplanPrerequisiteUnit:
    return ReplanPrerequisiteUnit(
        canonical_unit_id=canonical_unit_id,
        title=title,
        path_order=path_order,
        in_current_path=in_current_path,
        already_handled=handled,
        question_count=5,
    )
