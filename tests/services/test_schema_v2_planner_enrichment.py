from types import SimpleNamespace

from src.models.learning import PathAction
from src.services.recommendation_engine import (
    classify_schema_v2_unit_priority,
    find_prerequisite_gaps,
    is_mastery_evidence_backed,
)


def test_classify_schema_v2_unit_priority_prefers_canonical_fields_when_present():
    priority = classify_schema_v2_unit_priority(
        SimpleNamespace(
            active=True,
            section_flags=[],
            content_type="concept",
            salience_score="high",
            has_quiz_items=True,
            is_worth_learning=True,
            override_critical_kp=True,
        ),
        unit_kp_rows=[],
        kp_by_id={},
        quiz_item_count=0,
        action=PathAction.deep_practice,
    )

    assert priority.segment_policy == "core"
    assert priority.reason_codes == ["critical_kp", "high_salience", "quiz_available"]
    assert priority.has_quiz_items is True
    assert priority.salience_score == "high"


def test_classify_schema_v2_unit_priority_derives_from_kp_map_when_unit_fields_missing():
    priority = classify_schema_v2_unit_priority(
        SimpleNamespace(
            active=True,
            section_flags=[],
            content_type=None,
            salience_score=None,
            has_quiz_items=False,
            is_worth_learning=True,
            override_critical_kp=False,
        ),
        unit_kp_rows=[
            SimpleNamespace(
                kp_id="kp_attention",
                planner_role="main",
                coverage_level="dominant",
                coverage_weight=0.95,
            )
        ],
        kp_by_id={
            "kp_attention": SimpleNamespace(
                importance_level="critical",
                structural_role="gateway",
            )
        },
        quiz_item_count=2,
        action=PathAction.deep_practice,
    )

    assert priority.segment_policy == "core"
    assert priority.reason_codes == ["critical_kp", "high_salience", "quiz_available"]
    assert priority.has_quiz_items is True
    assert priority.salience_score == "0.95"


def test_classify_schema_v2_unit_priority_separates_reference_and_hidden_segments():
    hidden = classify_schema_v2_unit_priority(
        SimpleNamespace(
            active=True,
            section_flags=["logistics"],
            content_type="admin",
            salience_score=None,
            has_quiz_items=False,
            is_worth_learning=True,
            override_critical_kp=False,
        ),
        unit_kp_rows=[],
        kp_by_id={},
        quiz_item_count=0,
        action=PathAction.skip,
    )
    reference = classify_schema_v2_unit_priority(
        SimpleNamespace(
            active=True,
            section_flags=["reference"],
            content_type="reference",
            salience_score=None,
            has_quiz_items=False,
            is_worth_learning=False,
            override_critical_kp=False,
        ),
        unit_kp_rows=[],
        kp_by_id={},
        quiz_item_count=0,
        action=PathAction.quick_review,
    )

    assert hidden.segment_policy == "hidden"
    assert hidden.reason_codes == ["skip_by_mastery", "hidden_logistics"]
    assert reference.segment_policy == "reference"
    assert reference.reason_codes == ["quick_review", "reference_only"]


def test_find_prerequisite_gaps_walks_two_hops_and_ignores_mastered_evidence():
    gaps = find_prerequisite_gaps(
        target_kp_ids=["kp_transformers"],
        prerequisite_edges=[
            SimpleNamespace(source_kp_id="kp_attention", target_kp_id="kp_transformers", active=True),
            SimpleNamespace(source_kp_id="kp_linear_algebra", target_kp_id="kp_attention", active=True),
            SimpleNamespace(source_kp_id="kp_probability", target_kp_id="kp_linear_algebra", active=True),
            SimpleNamespace(source_kp_id="kp_python", target_kp_id="kp_probability", active=False),
        ],
        mastered_kp_ids={"kp_probability"},
        max_depth=2,
    )

    assert gaps == ["kp_attention", "kp_linear_algebra"]


def test_is_mastery_evidence_backed_requires_real_assessment_signal():
    assert is_mastery_evidence_backed(
        SimpleNamespace(n_items_observed=3, updated_by="mini_quiz", mastery_mean_cached=0.9)
    )
    assert not is_mastery_evidence_backed(
        SimpleNamespace(n_items_observed=0, updated_by="self_report", mastery_mean_cached=0.95)
    )
    assert not is_mastery_evidence_backed(
        SimpleNamespace(n_items_observed=2, updated_by="self_report", mastery_mean_cached=0.95)
    )
