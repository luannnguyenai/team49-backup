from types import SimpleNamespace

from src.services.assessment_service import (
    _assessment_depth_policy,
    _filter_unit_pools_for_depth,
)


def _item(item_id: str, *, difficulty: str, intent: str):
    return SimpleNamespace(item_id=item_id, difficulty=difficulty, question_intent=intent)


def test_quick_depth_caps_low_and_excludes_application_intent():
    policy = _assessment_depth_policy("quick")

    assert policy.max_questions == 15
    assert policy.questions_per_unit == 2

    pools = {
        "u1": [
            (_item("easy-concept", difficulty="easy", intent="conceptual"), None),
            (_item("medium-app", difficulty="medium", intent="application"), None),
            (_item("hard-concept", difficulty="hard", intent="conceptual"), None),
        ]
    }

    filtered = _filter_unit_pools_for_depth(pools, policy)

    assert [item.item_id for item, _ in filtered["u1"]] == ["easy-concept"]


def test_deep_depth_allows_application_and_caps_at_50():
    policy = _assessment_depth_policy("deep")

    assert policy.max_questions == 50
    assert policy.questions_per_unit == 5

    pools = {
        "u1": [
            (_item("hard-app", difficulty="hard", intent="application"), None),
        ]
    }

    filtered = _filter_unit_pools_for_depth(pools, policy)

    assert [item.item_id for item, _ in filtered["u1"]] == ["hard-app"]


def test_quick_depth_does_not_fallback_to_application_when_no_easy_medium_conceptual():
    policy = _assessment_depth_policy("quick")
    pools = {
        "u1": [
            (_item("medium-app", difficulty="medium", intent="application"), None),
        ]
    }

    filtered = _filter_unit_pools_for_depth(pools, policy)

    assert filtered["u1"] == []
