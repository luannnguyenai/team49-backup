from __future__ import annotations

import json
from pathlib import Path

from src.scripts.pipeline.export_canonical_artifacts import export_canonical_artifacts


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    courses_dir = tmp_path / "data" / "courses"
    course_dir = courses_dir / "CSMini"
    (course_dir / "processed_sanitized").mkdir(parents=True, exist_ok=True)
    (course_dir / "processed" / "P4" / "L1").mkdir(parents=True, exist_ok=True)
    (course_dir / "transcripts").mkdir(parents=True, exist_ok=True)

    transcript_path = course_dir / "transcripts" / "mini-lecture-1_transcript.txt"
    transcript_path.write_text(
        "\n".join(
            [
                "Title: Mini Lecture",
                "URL: https://example.com/watch?v=mini",
                "00:00:10",
                "language can support higher level of thought and scaffolding",
                "00:00:20",
                "one hot vectors are orthogonal and have dot product zero",
            ]
        ),
        encoding="utf-8",
    )

    _write_json(
        course_dir / "syllabus.json",
        {
            "course": "CSMini",
            "source": "fixture",
            "note": "fixture note",
            "reference_slides_no_video": [],
            "lectures": [
                {
                    "lecture_id": "mini-lecture-1",
                    "lecture_number": 1,
                    "title": "Mini Lecture 1",
                    "custom_order": 1,
                    "assets": {
                        "transcript": "mini-lecture-1_transcript.txt",
                        "video": "mini-lecture-1.mp4",
                    },
                }
            ],
        },
    )

    _write_json(
        course_dir / "processed_sanitized" / "L1_p1.json",
        {
            "lecture_title": "Mini Lecture 1",
            "lecture_id": "mini-lecture-1",
            "units": [
                {
                    "unit_id": "local::mini::seg1",
                    "course_id": "mini-raw",
                    "name": "Unit 1",
                    "description": "Intro concept",
                    "summary": "Summary one [ts=10s]",
                    "key_points": [{"text": "Key one", "timestamp_s": 10, "evidence_type": "claim"}],
                    "content_ref": {"video_url": "https://example.com/watch?v=mini", "start_s": 0, "end_s": 15},
                    "difficulty": 0.2,
                    "difficulty_source": "llm_single_pass",
                    "difficulty_confidence": "high",
                    "duration_min": 1.0,
                    "ordering_index": 1,
                    "is_template": False,
                },
                {
                    "unit_id": "local::mini::seg2",
                    "course_id": "mini-raw",
                    "name": "Unit 2",
                    "description": "Follow-up concept",
                    "summary": "Summary two [ts=20s]",
                    "key_points": [{"text": "Key two", "timestamp_s": 20, "evidence_type": "claim"}],
                    "content_ref": {"video_url": "https://example.com/watch?v=mini", "start_s": 16, "end_s": 30},
                    "difficulty": 0.4,
                    "difficulty_source": "llm_single_pass",
                    "difficulty_confidence": "medium",
                    "duration_min": 1.0,
                    "ordering_index": 2,
                    "is_template": False,
                },
            ],
            "section_flags": [
                {"unit_id": "local::mini::seg1", "importance_flag": "high"},
                {"unit_id": "local::mini::seg2", "importance_flag": "high"},
            ],
            "unit_kp_map_local": [
                {
                    "unit_id": "local::mini::seg1",
                    "local_kp_id": "local::mini::kp1",
                    "planner_role": "main",
                    "instruction_role": "intro",
                    "coverage_level": "dominant",
                    "coverage_confidence": "high",
                    "coverage_rationale": "Core of the unit [ts=10s].",
                },
                {
                    "unit_id": "local::mini::seg2",
                    "local_kp_id": "local::mini::kp2",
                    "planner_role": "main",
                    "instruction_role": "main",
                    "coverage_level": "substantial",
                    "coverage_confidence": "medium",
                    "coverage_rationale": "Main follow-up [ts=20s].",
                },
            ],
        },
    )

    _write_json(
        course_dir / "processed" / "P4" / "L1" / "mini-seg1-p4.json",
        {
            "unit_id": "local::mini::seg1",
            "youtube_url": "https://example.com/watch?v=mini",
            "assessment_purpose": "lecture_reinforcement",
            "grounding_mode": "transcript_only",
            "grounding_confidence": "high",
            "needs_video_clip": False,
            "question_intent": "conceptual",
            "target_item_count": 1,
            "review_summary": "fixture",
            "repaired_question_bank": [
                {
                    "item_id": "mini-q1",
                    "item_type": "concept_mcq",
                    "knowledge_scope": "transferable",
                    "render_mode": "standard_mcq",
                    "question": "Why is language more than communication?",
                    "choices": ["It supports thought", "It removes memory", "It is only grammar", "It is just sound"],
                    "answer_index": 0,
                    "explanation": "Language can support thought.",
                    "primary_kp_id": "kp_language_scaffolding",
                    "difficulty": "easy",
                    "evidence": {
                        "source": "transcript",
                        "transcript_quotes": ["higher level of thought and scaffolding"],
                        "timestamps": ["00:00:10"],
                    },
                    "qa_gate_passed": True,
                    "review_status": "not_required",
                    "repair_history": [],
                    "provenance": "llm_single_pass",
                }
            ],
            "item_kp_map": [{"item_id": "mini-q1", "global_kp_id": "kp_language_scaffolding", "role": "primary"}],
            "item_calibration_bootstrap": [
                {
                    "item_id": "mini-q1",
                    "is_calibrated": False,
                    "calibration_method": "prior_only",
                    "difficulty_prior": -0.4,
                    "discrimination_prior": 0.9,
                    "guessing_prior": 0.25,
                }
            ],
            "item_phase_map": [
                {
                    "item_id": "mini-q1",
                    "primary_phase": "placement",
                    "secondary_phases": ["review"],
                    "suitability_by_phase": {"placement": "high", "review": "medium"},
                    "phase_multiplier_by_phase": {"placement": 1.0, "review": 0.7},
                    "phase_rationale": "fixture",
                }
            ],
        },
    )

    p2_path = tmp_path / "p2.json"
    _write_json(
        p2_path,
        {
            "run_id": "p2_fixture",
            "p2_mode": "batch_initial",
            "concepts_kp_global": [
                {
                    "global_kp_id": "kp_language_scaffolding",
                    "name": "Language scaffolding",
                    "description": "Language supports thought.",
                    "track_tags": [],
                    "domain_tags": [],
                    "career_path_tags": [],
                    "difficulty_level": 0.2,
                    "difficulty_source": "llm_single_pass",
                    "difficulty_confidence": "high",
                    "importance_level": "critical",
                    "structural_role": "gateway",
                    "importance_confidence": "high",
                    "importance_rationale": "fixture",
                    "importance_scope": "lecture_local",
                    "importance_source": "llm_single_pass",
                    "source_course_ids": ["CSMini"],
                },
                {
                    "global_kp_id": "kp_one_hot_limitations",
                    "name": "One-hot limitations",
                    "description": "One-hot vectors are orthogonal.",
                    "track_tags": [],
                    "domain_tags": [],
                    "career_path_tags": [],
                    "difficulty_level": 0.3,
                    "difficulty_source": "llm_single_pass",
                    "difficulty_confidence": "high",
                    "importance_level": "high",
                    "structural_role": "supporting",
                    "importance_confidence": "medium",
                    "importance_rationale": "fixture",
                    "importance_scope": "lecture_local",
                    "importance_source": "llm_single_pass",
                    "source_course_ids": ["CSMini"],
                },
            ],
            "local_to_global_map": [
                {"local_kp_id": "local::mini::kp1", "global_kp_id": "kp_language_scaffolding"},
                {"local_kp_id": "local::mini::kp2", "global_kp_id": "kp_one_hot_limitations"},
            ],
            "unit_kp_map_global": [
                {"unit_id": "local::mini::seg1", "global_kp_id": "kp_language_scaffolding", "planner_role": "main", "coverage_level": "dominant"},
                {"unit_id": "local::mini::seg2", "global_kp_id": "kp_one_hot_limitations", "planner_role": "main", "coverage_level": "substantial"},
            ],
        },
    )

    p5_path = tmp_path / "p5.json"
    _write_json(
        p5_path,
        {
            "run_id": "p5_fixture",
            "stage_id": "p5",
            "clean_candidate_edges": [
                {
                    "source_kp_id": "kp_language_scaffolding",
                    "target_kp_id": "kp_one_hot_limitations",
                    "edge_scope": "intra_course",
                    "provenance": "llm_cross_check",
                    "keep_confidence": "medium",
                    "keep_rationale": "fixture keep",
                    "expected_directionality": "moderate",
                    "review_status": "optional",
                    "ready_for_modernbert": True,
                }
            ],
            "pruned_edges": [],
            "adjudication_trace": [],
        },
    )

    gpt54_path = tmp_path / "gpt54.json"
    _write_json(
        gpt54_path,
        {
            "run_id": "p5_fixture",
            "stage_id": "edge_audit_best_effort",
            "summary": {"edge_count": 1},
            "edge_labels": [
                {
                    "source_kp_id": "kp_language_scaffolding",
                    "source_name": "Language scaffolding",
                    "source_description": "Language supports thought.",
                    "target_kp_id": "kp_one_hot_limitations",
                    "target_name": "One-hot limitations",
                    "target_description": "One-hot vectors are orthogonal.",
                    "source_first_seen": {"unit_id": "local::mini::seg1", "course_id": "CSMini", "lecture_order": 1, "unit_name": "Unit 1"},
                    "target_first_seen": {"unit_id": "local::mini::seg2", "course_id": "CSMini", "lecture_order": 1, "unit_name": "Unit 2"},
                    "temporal_signal": "same_lecture",
                    "baseline_gpt54_verdict": "keep",
                    "baseline_gpt54_confidence": "medium",
                    "baseline_gpt54_rationale": "fixture",
                    "best_verdict": "keep",
                    "best_confidence": "medium",
                    "best_rationale": "fixture",
                    "best_review_status": "optional",
                    "best_prune_reason": None,
                    "p5_keep_confidence": "medium",
                    "p5_expected_directionality": "moderate",
                    "p5_trace": {},
                }
            ],
        },
    )

    output_dir = tmp_path / "canonical"
    return courses_dir, p2_path, p5_path, gpt54_path, output_dir


def test_export_canonical_artifacts_smoke(tmp_path: Path) -> None:
    courses_dir, p2_path, p5_path, gpt54_path, output_dir = _build_fixture(tmp_path)

    manifest, report = export_canonical_artifacts(
        output_dir=output_dir,
        courses_dir=courses_dir,
        p2_path=p2_path,
        p5_path=p5_path,
        gpt54_path=gpt54_path,
        selected_courses=["CSMini"],
    )

    assert manifest["counts"]["courses"] == 1
    assert manifest["counts"]["concepts_kp"] == 2
    assert manifest["counts"]["units"] == 2
    assert manifest["counts"]["unit_kp_map"] == 2
    assert manifest["counts"]["question_bank"] == 1
    assert manifest["counts"]["prerequisite_edges"] == 1
    assert manifest["counts"]["rejected_items"] == 0
    assert report["summary"]["hard_failure_count"] == 0

    expected_files = {
        "courses.jsonl",
        "concepts_kp.jsonl",
        "units.jsonl",
        "unit_kp_map.jsonl",
        "question_bank.jsonl",
        "item_calibration.jsonl",
        "item_phase_map.jsonl",
        "item_kp_map.jsonl",
        "prerequisite_edges.jsonl",
        "pruned_edges.jsonl",
        "rejected_items.jsonl",
        "manifest.json",
        "validation_report.json",
    }
    assert expected_files.issubset({path.name for path in output_dir.iterdir()})
