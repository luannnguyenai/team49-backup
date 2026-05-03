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


def test_evidence_quality_finds_direct_title_match_buried_below_broad_results():
    broad_results = [
        UnitSearchResult(
            canonical_unit_id=f"unit-broad-{index}",
            course_id="CS231n",
            unit_name=f"Generic object detection result {index}",
            summary="This row overlaps with broad search terms but is not the requested topic.",
            score=4,
        )
        for index in range(20)
    ]
    direct_result = UnitSearchResult(
        canonical_unit_id="unit-yolo",
        course_id="CS231n",
        unit_name="Single-stage and transformer detectors: YOLO and DETR",
        summary="YOLO is the canonical single-stage detector example.",
        score=1,
    )

    verdict = AgentEvidenceQualityService().score(
        query="YOLO",
        results=[*broad_results, direct_result],
    )

    assert verdict.label == "direct_match"
    assert verdict.selected_unit_ids == ["unit-yolo"]


def test_evidence_quality_prioritizes_explicit_acronym_over_expanded_phrase_noise():
    verdict = AgentEvidenceQualityService().score(
        query="YOLO (You Only Look Once)",
        results=[
            UnitSearchResult(
                canonical_unit_id="unit-yolo",
                course_id="CS231n",
                unit_name="Single-stage and transformer detectors: YOLO and DETR",
                summary="YOLO is the canonical single-stage detector example.",
                score=3,
            ),
            UnitSearchResult(
                canonical_unit_id="unit-look",
                course_id="CS231n",
                unit_name="Contrastive learning formulation and InfoNCE",
                summary="The method looks at positive and negative pairs only once in this summary.",
                score=2,
            ),
        ],
    )

    assert verdict.label == "direct_match"
    assert verdict.selected_unit_ids == ["unit-yolo"]
