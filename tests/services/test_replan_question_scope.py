from src.services.replan_question_scope import (
    ReplanQuestion,
    ReplanQuestionScopeBuilder,
    ReplanScopeUnit,
)


def test_question_scope_prefers_question_linked_knowledge_points():
    builder = ReplanQuestionScopeBuilder()
    unit = _unit(key_points=["Canonical fallback"])
    questions = [
        ReplanQuestion(unit_id="unit_faster_rcnn", difficulty="easy", knowledge_points=["RPN"]),
        ReplanQuestion(unit_id="unit_faster_rcnn", difficulty="medium", knowledge_points=["Anchor boxes"]),
    ]

    scope = builder.build([unit], questions, unit_kp_map={"unit_faster_rcnn": ["Mapped KP"]})

    assert scope[0].knowledge_points == ["RPN", "Anchor boxes"]
    assert scope[0].question_counts == {"easy": 1, "medium": 1, "hard": 0, "application": 0}


def test_question_scope_falls_back_to_unit_kp_map_then_canonical_key_points():
    builder = ReplanQuestionScopeBuilder()
    unit = _unit(key_points=["Canonical fallback"])

    mapped_scope = builder.build([unit], [], unit_kp_map={"unit_faster_rcnn": ["Mapped KP"]})
    canonical_scope = builder.build([unit], [], unit_kp_map={})

    assert mapped_scope[0].knowledge_points == ["Mapped KP"]
    assert canonical_scope[0].knowledge_points == ["Canonical fallback"]


def _unit(key_points: list[str]) -> ReplanScopeUnit:
    return ReplanScopeUnit(
        canonical_unit_id="unit_faster_rcnn",
        title="Faster R-CNN",
        source="matched_from_description",
        key_points=key_points,
    )
