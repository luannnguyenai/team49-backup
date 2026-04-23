from src.services.canonical_planner_service import classify_unit_action


def test_classify_unit_action_uses_mastery_lcb():
    assert classify_unit_action(mastery_lcb=0.85) == "skip"
    assert classify_unit_action(mastery_lcb=0.55) == "quick_review"
    assert classify_unit_action(mastery_lcb=0.25) == "deep_practice"
