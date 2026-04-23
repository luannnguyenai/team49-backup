from __future__ import annotations

from copy import deepcopy

from src.scripts.pipeline.export_canonical_artifacts import validate_canonical_tables


def _base_tables() -> tuple[dict, dict]:
    tables = {
        "courses": [
            {
                "course_id": "CSMini",
                "course_name": "Mini",
                "source": "fixture",
                "note": "",
                "reference_slides_no_video": [],
                "lecture_count": 1,
                "track_tags": [],
                "summary_embedding": None,
                "source_file": "fixture",
            }
        ],
        "concepts_kp": [
            {
                "kp_id": "kp_a",
                "name": "KP A",
                "description": "A",
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
                "importance": 1.0,
                "description_embedding": None,
                "source_file": "fixture",
            },
            {
                "kp_id": "kp_b",
                "name": "KP B",
                "description": "B",
                "track_tags": [],
                "domain_tags": [],
                "career_path_tags": [],
                "difficulty_level": 0.2,
                "difficulty_source": "llm_single_pass",
                "difficulty_confidence": "high",
                "importance_level": "high",
                "structural_role": "supporting",
                "importance_confidence": "high",
                "importance_rationale": "fixture",
                "importance_scope": "lecture_local",
                "importance_source": "llm_single_pass",
                "source_course_ids": ["CSMini"],
                "importance": 0.75,
                "description_embedding": None,
                "source_file": "fixture",
            },
        ],
        "units": [
            {
                "unit_id": "u1",
                "course_id": "CSMini",
                "lecture_id": "l1",
                "lecture_order": 1,
                "lecture_title": "Lecture 1",
                "unit_name": "Unit 1",
                "description": "desc",
                "summary": "summary",
                "key_points": [{"text": "k", "timestamp_s": 10, "evidence_type": "claim"}],
                "content_ref": {"video_url": "https://example.com", "start_s": 0, "end_s": 20},
                "difficulty": 0.2,
                "difficulty_source": "llm_single_pass",
                "difficulty_confidence": "high",
                "duration_min": 1.0,
                "ordering_index": 1,
                "section_flags": None,
                "video_clip_ref": None,
                "topic_embedding": None,
                "source_file": "fixture",
                "transcript_path": "fixture-transcript",
            }
        ],
        "unit_kp_map": [
            {
                "unit_id": "u1",
                "kp_id": "kp_a",
                "planner_role": "main",
                "instruction_role": "intro",
                "coverage_level": "dominant",
                "coverage_confidence": "high",
                "coverage_rationale": "fixture",
                "coverage_weight": 1.0,
                "source_local_kp_ids": ["local::kp1"],
                "source_file": "fixture",
            }
        ],
        "question_bank": [
            {
                "course_id": "CSMini",
                "lecture_id": "l1",
                "unit_id": "u1",
                "source_file": "fixture",
                "item_id": "q1",
                "item_type": "concept_mcq",
                "knowledge_scope": "transferable",
                "render_mode": "standard_mcq",
                "question": "Q?",
                "choices": ["A", "B"],
                "answer_index": 0,
                "explanation": "A",
                "primary_kp_id": "kp_a",
                "source_ref": {
                    "unit_id": "u1",
                    "timestamp_start": 10,
                    "timestamp_end": 10,
                    "evidence_span": "higher level of thought",
                    "multimodal_signals_used": ["transcript"],
                    "video_clip_ref": None,
                    "video_url": "https://example.com",
                },
                "difficulty": "easy",
                "question_intent": "conceptual",
                "qa_gate_passed": True,
                "review_status": "not_required",
                "repair_history": [],
                "provenance": "llm_single_pass",
                "concept_alignment_cosine": None,
                "distractor_cosine_upper": None,
                "distractor_cosine_lower": None,
                "assessment_purpose": "lecture_reinforcement",
                "grounding_mode": "transcript_only",
                "grounding_confidence": "high",
            }
        ],
        "item_calibration": [
            {
                "course_id": "CSMini",
                "lecture_id": "l1",
                "unit_id": "u1",
                "source_file": "fixture",
                "item_id": "q1",
                "calibration_method": "prior_only",
                "is_calibrated": False,
                "difficulty_prior": -0.4,
                "discrimination_prior": 0.9,
                "guessing_prior": 0.25,
                "difficulty_b": None,
                "discrimination_a": None,
                "guessing_c": None,
                "irt_calibration_n": 0,
                "standard_error_b": None,
            }
        ],
        "item_phase_map": [
            {
                "course_id": "CSMini",
                "lecture_id": "l1",
                "unit_id": "u1",
                "source_file": "fixture",
                "item_id": "q1",
                "phase": "placement",
                "phase_multiplier": 1.0,
                "suitability_score": "high",
                "selection_priority": None,
                "phase_rationale": "fixture",
            }
        ],
        "item_kp_map": [
            {
                "course_id": "CSMini",
                "lecture_id": "l1",
                "unit_id": "u1",
                "source_file": "fixture",
                "item_id": "q1",
                "kp_id": "kp_a",
                "kp_role": "primary",
                "weight": 0.7,
                "mapping_confidence": None,
            }
        ],
        "prerequisite_edges": [
            {
                "source_kp_id": "kp_a",
                "target_kp_id": "kp_b",
                "edge_scope": "intra_course",
                "provenance": "llm_cross_check",
                "confidence": "medium",
                "review_status": "optional",
                "rationale": "fixture",
                "temporal_signal": "same_lecture",
                "source_first_seen": None,
                "target_first_seen": None,
                "p5_keep_confidence": "medium",
                "p5_expected_directionality": "moderate",
                "p5_trace": {},
                "edge_strength": None,
                "bidirectional_score": None,
                "source_file": "fixture",
            }
        ],
        "pruned_edges": [],
        "rejected_items": [],
    }
    transcript_cache = {"fixture-transcript": "higher level of thought and scaffolding appears in transcript"}
    return tables, transcript_cache


def _hard_fail_reasons(tables: dict, transcript_cache: dict) -> set[str]:
    _, rejected, report = validate_canonical_tables(tables=tables, transcript_cache=transcript_cache)
    assert report["summary"]["hard_failure_count"] >= 1
    return {row["hard_fail_reason"] for row in rejected}


def test_validate_referential_integrity_failure() -> None:
    tables, transcript_cache = _base_tables()
    tables["question_bank"][0]["primary_kp_id"] = "missing"
    assert "unknown_primary_kp_id" in _hard_fail_reasons(tables, transcript_cache)


def test_validate_duplicate_key_failure() -> None:
    tables, transcript_cache = _base_tables()
    tables["question_bank"].append(deepcopy(tables["question_bank"][0]))
    assert "duplicate_key" in _hard_fail_reasons(tables, transcript_cache)


def test_validate_enum_failure() -> None:
    tables, transcript_cache = _base_tables()
    tables["item_phase_map"][0]["phase"] = "bad_phase"
    assert "invalid_phase" in _hard_fail_reasons(tables, transcript_cache)


def test_validate_source_ref_failure() -> None:
    tables, transcript_cache = _base_tables()
    tables["question_bank"][0]["source_ref"] = None
    assert "missing_source_ref" in _hard_fail_reasons(tables, transcript_cache)


def test_validate_evidence_span_failure() -> None:
    tables, transcript_cache = _base_tables()
    tables["question_bank"][0]["source_ref"]["evidence_span"] = "not in transcript"
    assert "evidence_span_not_in_transcript" in _hard_fail_reasons(tables, transcript_cache)


def test_validate_timestamp_bounds_failure() -> None:
    tables, transcript_cache = _base_tables()
    tables["question_bank"][0]["source_ref"]["timestamp_start"] = 99
    tables["question_bank"][0]["source_ref"]["timestamp_end"] = 99
    assert "source_timestamps_out_of_bounds" in _hard_fail_reasons(tables, transcript_cache)
