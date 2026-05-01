from src.schemas.agent import UnitSearchResult
from src.services.agent_evidence_quality import AgentEvidenceQualityService


def test_evidence_quality_marks_title_coverage_as_direct_match():
    verdict = AgentEvidenceQualityService().score(
        query="attention mask",
        results=[
            UnitSearchResult(
                canonical_unit_id="unit-attention-mask",
                course_id="CS224n",
                unit_name="Attention masks in transformers",
                summary="Padding and causal masks.",
                score=2,
            )
        ],
    )

    assert verdict.label == "direct_match"
    assert verdict.requires_grounded_answer is True
    assert verdict.selected_unit_ids == ["unit-attention-mask"]
    assert "title_or_lecture_match" in verdict.reason_codes


def test_evidence_quality_marks_summary_only_overlap_as_related_match():
    verdict = AgentEvidenceQualityService().score(
        query="cnn object detection",
        results=[
            UnitSearchResult(
                canonical_unit_id="unit-related",
                course_id="CS231n",
                unit_name="Visual recognition project examples",
                summary="Mentions CNNs and detection datasets at a high level.",
                score=1,
            )
        ],
    )

    assert verdict.label == "related_match"
    assert verdict.requires_grounded_answer is False
    assert "summary_partial_match" in verdict.reason_codes


def test_evidence_quality_marks_low_coverage_as_weak_match():
    verdict = AgentEvidenceQualityService().score(
        query="attention mask transformer",
        results=[
            UnitSearchResult(
                canonical_unit_id="unit-overview",
                course_id="CS230",
                unit_name="Course overview",
                summary="General deep learning overview.",
                score=1,
            )
        ],
    )

    assert verdict.label == "weak_match"
    assert verdict.requires_grounded_answer is False
