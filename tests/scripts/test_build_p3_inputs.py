from __future__ import annotations

import json
from pathlib import Path

from src.scripts.pipeline import build_p3_inputs as build_p3_inputs_cli


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_p1_artifact() -> dict:
    return {
        "lecture_title": "Lecture 7 - Attention",
        "table_of_contents": [
            {"section_index": 1, "title": "Intro", "start_s": 0, "end_s": 30},
            {"section_index": 2, "title": "Attention", "start_s": 31, "end_s": 90},
        ],
        "units": [
            {
                "unit_id": "local::lecture07-attention::seg1",
                "course_id": "CS224n",
                "name": "Intro to Attention",
                "description": "Motivates attention.",
                "summary": "Intro [ts=5s] and bottleneck [ts=20s]",
                "key_points": [],
                "content_ref": {
                    "video_url": "https://www.youtube.com/watch?v=abc123&list=demo&index=7",
                    "start_s": 5,
                    "end_s": 25,
                },
                "difficulty": 0.5,
                "difficulty_source": "llm_single_pass",
                "difficulty_confidence": "medium",
                "duration_min": 1,
                "ordering_index": 0,
                "is_template": False,
            },
            {
                "unit_id": "local::lecture07-attention::seg2",
                "course_id": "CS224n",
                "name": "Cross Attention",
                "description": "Explains cross attention.",
                "summary": "Cross attention [ts=40s] weighted sum [ts=70s]",
                "key_points": [],
                "content_ref": {
                    "video_url": "https://www.youtube.com/watch?v=abc123&list=demo&index=7",
                    "start_s": 40,
                    "end_s": 80,
                },
                "difficulty": 0.7,
                "difficulty_source": "llm_single_pass",
                "difficulty_confidence": "medium",
                "duration_min": 1,
                "ordering_index": 1,
                "is_template": False,
            },
        ],
        "concepts_kp_local": [
            {
                "local_kp_id": "local::lecture07-attention::kp1",
                "name": "Seq2seq bottleneck",
                "description": "Fixed context vector bottleneck.",
            },
            {
                "local_kp_id": "local::lecture07-attention::kp2",
                "name": "Cross attention",
                "description": "Weighted sum over encoder states.",
            },
        ],
        "unit_kp_map_local": [
            {
                "unit_id": "local::lecture07-attention::seg1",
                "local_kp_id": "local::lecture07-attention::kp1",
                "planner_role": "main",
                "instruction_role": "main",
                "coverage_level": "dominant",
                "coverage_confidence": "high",
                "coverage_rationale": "[ts=10s]",
            },
            {
                "unit_id": "local::lecture07-attention::seg2",
                "local_kp_id": "local::lecture07-attention::kp1",
                "planner_role": "prereq",
                "instruction_role": "review",
                "coverage_level": "substantial",
                "coverage_confidence": "high",
                "coverage_rationale": "[ts=42s]",
            },
            {
                "unit_id": "local::lecture07-attention::seg2",
                "local_kp_id": "local::lecture07-attention::kp2",
                "planner_role": "main",
                "instruction_role": "main",
                "coverage_level": "dominant",
                "coverage_confidence": "high",
                "coverage_rationale": "[ts=50s]",
            },
        ],
        "section_flags": [
            {
                "unit_id": "local::lecture07-attention::seg1",
                "importance_flag": "high",
                "review_worthiness": "medium",
                "item_generation_worthiness": "high",
                "formula_heavy": False,
                "demo_heavy": False,
                "rationale": "important",
            },
            {
                "unit_id": "local::lecture07-attention::seg2",
                "importance_flag": "high",
                "review_worthiness": "high",
                "item_generation_worthiness": "high",
                "formula_heavy": True,
                "demo_heavy": False,
                "rationale": "formula",
            },
        ],
        "self_critique_trace": None,
    }


def _make_placeholder_p1_artifact() -> dict:
    artifact = _make_p1_artifact()
    artifact["units"][0]["unit_id"] = "local::<lecture_id>::seg1"
    artifact["units"][0]["course_id"] = "<course_id>"
    artifact["units"][0]["content_ref"]["video_url"] = "https://www.youtube.com/watch?v=abc123&list=demo&index=7"
    artifact["section_flags"][0]["unit_id"] = "local::<lecture_id>::seg1"
    artifact["unit_kp_map_local"][0]["unit_id"] = "local::<lecture_id>::seg1"
    return artifact


def _make_p2_output() -> dict:
    return {
        "run_id": "demo",
        "p2_mode": "batch_initial",
        "concepts_kp_global": [
            {
                "global_kp_id": "kp_seq2seq_bottleneck",
                "name": "Seq2seq bottleneck",
                "description": "Fixed context vector bottleneck.",
                "track_tags": ["nlp"],
                "domain_tags": ["sequence_models"],
                "career_path_tags": ["nlp_engineer"],
                "difficulty_level": 0.5,
                "difficulty_source": "llm_single_pass",
                "difficulty_confidence": "high",
                "importance_level": "high",
                "structural_role": "gateway",
                "importance_confidence": "high",
                "importance_rationale": "Unlocks attention",
                "importance_scope": "course_global",
                "importance_source": "llm_single_pass",
                "source_course_ids": ["CS224n"],
                "merged_from_local_ids": ["local::lecture07-attention::kp1"],
            },
            {
                "global_kp_id": "kp_cross_attention",
                "name": "Cross attention",
                "description": "Weighted sum over encoder states.",
                "track_tags": ["nlp"],
                "domain_tags": ["attention"],
                "career_path_tags": ["nlp_engineer"],
                "difficulty_level": 0.7,
                "difficulty_source": "llm_single_pass",
                "difficulty_confidence": "high",
                "importance_level": "critical",
                "structural_role": "gateway",
                "importance_confidence": "high",
                "importance_rationale": "Core attention mechanism",
                "importance_scope": "course_global",
                "importance_source": "llm_single_pass",
                "source_course_ids": ["CS224n"],
                "merged_from_local_ids": ["local::lecture07-attention::kp2"],
            },
        ],
        "local_to_global_map": [
            {
                "local_kp_id": "local::lecture07-attention::kp1",
                "global_kp_id": "kp_seq2seq_bottleneck",
                "match_confidence": "high",
                "match_rationale": "same",
            },
            {
                "local_kp_id": "local::lecture07-attention::kp2",
                "global_kp_id": "kp_cross_attention",
                "match_confidence": "high",
                "match_rationale": "same",
            },
        ],
        "unit_kp_map_global": [
            {
                "unit_id": "local::lecture07-attention::seg1",
                "global_kp_id": "kp_seq2seq_bottleneck",
                "planner_role": "main",
                "coverage_level": "dominant",
            },
            {
                "unit_id": "local::lecture07-attention::seg2",
                "global_kp_id": "kp_seq2seq_bottleneck",
                "planner_role": "prereq",
                "coverage_level": "substantial",
            },
            {
                "unit_id": "local::lecture07-attention::seg2",
                "global_kp_id": "kp_cross_attention",
                "planner_role": "main",
                "coverage_level": "dominant",
            },
        ],
        "candidate_prerequisite_edges": [],
        "consensus_trace": [],
    }


def _make_p3_output() -> dict:
    return {
        "output_filename": "p3a__cs224n__lecture07_attention.json",
        "run_id": "run_cs224n_lecture07_attention",
        "stage_id": "p3a",
        "course_id": "CS224n",
        "lecture_id": "lecture07-attention",
        "learning_salience": [
            {
                "unit_id": "local::lecture07-attention::seg1",
                "is_worth_learning": True,
                "salience_score": "medium",
                "rationale": "Attention bottleneck setup.",
                "target_kp_ids": ["kp_seq2seq_bottleneck"],
                "question_intent": "conceptual",
                "content_type": "core_theory",
                "content_type_confidence": "high",
                "override_critical_kp": False,
                "expected_item_count": 2,
                "salience_confidence": "high",
                "provenance": "llm_single_pass",
            },
            {
                "unit_id": "local::lecture07-attention::seg2",
                "is_worth_learning": True,
                "salience_score": "high",
                "rationale": "Cross attention mechanics.",
                "target_kp_ids": ["kp_cross_attention"],
                "question_intent": "procedural",
                "content_type": "core_theory",
                "content_type_confidence": "high",
                "override_critical_kp": False,
                "expected_item_count": 4,
                "salience_confidence": "high",
                "provenance": "llm_single_pass",
            },
        ],
    }


def test_build_p3_inputs_creates_p3a_p3b_and_p3c_files(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS224n"
    processed_dir = course_dir / "processed_sanitized"
    transcript_dir = course_dir / "transcripts"
    processed_dir.mkdir(parents=True)
    transcript_dir.mkdir(parents=True)

    _write_json(processed_dir / "L7_p1.json", _make_p1_artifact())
    (transcript_dir / "lecture07_transcript.txt").write_text(
        "\n".join(
            [
                "Title: Lecture 7",
                "URL: https://www.youtube.com/watch?v=abc123",
                "Video ID: abc123",
                "============================================================",
                "",
                "00:00:05",
                "Intro to attention starts here.",
                "",
                "00:00:20",
                "The bottleneck appears here.",
                "",
                "00:00:45",
                "Cross attention uses weighted sums.",
                "",
                "00:01:05",
                "Attention scores are normalized.",
            ]
        ),
        encoding="utf-8",
    )

    p2_output = tmp_path / "p2_output.json"
    _write_json(p2_output, _make_p2_output())

    output_dir = tmp_path / "p3_inputs"
    report = build_p3_inputs_cli.build_p3_inputs(
        course_dirs=[course_dir],
        p2_output_path=p2_output,
        output_dir=output_dir,
    )

    assert report["summary"] == {"lectures": 1, "p3a_files": 1, "p3b_files": 1, "p3c_files": 2}

    p3a_file = output_dir / "p3a" / "CS224n" / "L7_p1.json"
    p3b_file = output_dir / "p3b" / "CS224n" / "L7_p1.json"
    p3c_unit1 = output_dir / "p3c" / "CS224n" / "L7_p1" / "local--lecture07-attention-seg1.json"
    p3c_unit2 = output_dir / "p3c" / "CS224n" / "L7_p1" / "local--lecture07-attention-seg2.json"

    assert p3a_file.exists()
    assert p3b_file.exists()
    assert p3c_unit1.exists()
    assert p3c_unit2.exists()

    p3a = json.loads(p3a_file.read_text(encoding="utf-8"))
    assert p3a["lecture_context"]["lecture_id"] == "lecture07-attention"
    assert p3a["lecture_context"]["youtube_url"] == "https://www.youtube.com/watch?v=abc123"
    assert {row["global_kp_id"] for row in p3a["kp_catalog"]} == {"kp_seq2seq_bottleneck", "kp_cross_attention"}
    assert p3a["course_config"]["included_content_types"] == [
        "core_theory",
        "worked_example",
        "application_case",
        "motivation",
    ]

    p3b = json.loads(p3b_file.read_text(encoding="utf-8"))
    assert p3b["learning_salience"] is None
    assert p3b["buffer_s"] == 3
    assert p3b["storage_path_template"] == "clips/<course_id>/<lecture_id>/<unit_id>.mp4"

    p3c = json.loads(p3c_unit2.read_text(encoding="utf-8"))
    assert p3c["video_clip_url"] == "https://www.youtube.com/watch?v=abc123"
    assert p3c["question_intent"] is None
    assert p3c["target_item_count"] is None
    assert p3c["target_kp_ids"] == []
    assert p3c["assessment_purpose"] == "lecture_reinforcement"
    assert p3c["youtube_url"] == "https://www.youtube.com/watch?v=abc123"
    assert p3c["allowed_item_types"] == ["concept_mcq"]
    assert p3c["allow_code_mcq"] is False
    assert p3c["code_evidence"] == []
    assert p3c["target_difficulty_range"] == [0.55, 0.85]
    assert "00:00:45" in p3c["transcript_slice"]
    assert "Cross attention uses weighted sums." in p3c["transcript_slice"]
    assert {row["global_kp_id"] for row in p3c["unit_kp_map_rows"]} == {"kp_seq2seq_bottleneck", "kp_cross_attention"}


def test_build_p3_inputs_sanitizes_p3a_placeholder_metadata(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS224n"
    processed_dir = course_dir / "processed_sanitized"
    transcript_dir = course_dir / "transcripts"
    processed_dir.mkdir(parents=True)
    transcript_dir.mkdir(parents=True)

    _write_json(processed_dir / "L7_p1.json", _make_placeholder_p1_artifact())
    (transcript_dir / "cs224n-2024-lecture07-attention_transcript.txt").write_text(
        "\n".join(
            [
                "Title: Lecture 7",
                "URL: https://www.youtube.com/watch?v=abc123",
                "Video ID: abc123",
                "============================================================",
                "",
                "00:00:05",
                "Intro to attention starts here.",
            ]
        ),
        encoding="utf-8",
    )

    p2_output = tmp_path / "p2_output.json"
    _write_json(p2_output, _make_p2_output())

    output_dir = tmp_path / "p3_inputs"
    build_p3_inputs_cli.build_p3_inputs(
        course_dirs=[course_dir],
        p2_output_path=p2_output,
        output_dir=output_dir,
    )

    p3a = json.loads((output_dir / "p3a" / "CS224n" / "L7_p1.json").read_text(encoding="utf-8"))
    assert p3a["lecture_context"]["lecture_id"] == "cs224n-2024-lecture07-attention"
    assert p3a["units"][0]["unit_id"] == "local::cs224n-2024-lecture07-attention::seg1"
    assert p3a["units"][0]["course_id"] == "CS224n"
    assert p3a["units"][0]["content_ref"]["video_url"] == "https://www.youtube.com/watch?v=abc123"
    assert p3a["section_flags"][0]["unit_id"] == "local::cs224n-2024-lecture07-attention::seg1"
    assert p3a["unit_kp_map"][0]["unit_id"] == "local::cs224n-2024-lecture07-attention::seg1"


def test_build_p3_inputs_hydrates_p3c_from_processed_p3(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS224n"
    processed_dir = course_dir / "processed_sanitized"
    transcript_dir = course_dir / "transcripts"
    processed_p3_dir = course_dir / "processed" / "P3"
    processed_dir.mkdir(parents=True)
    transcript_dir.mkdir(parents=True)
    processed_p3_dir.mkdir(parents=True)

    artifact = _make_p1_artifact()
    artifact["units"][1]["name"] = "PyTorch attention implementation"
    artifact["units"][1]["summary"] = "PyTorch tensor code [ts=40s] weighted sum [ts=70s]"
    _write_json(processed_dir / "L7_p1.json", artifact)
    _write_json(processed_p3_dir / "L7.json", _make_p3_output())
    (transcript_dir / "lecture07_transcript.txt").write_text(
        "\n".join(
            [
                "Title: Lecture 7",
                "URL: https://www.youtube.com/watch?v=abc123",
                "Video ID: abc123",
                "============================================================",
                "",
                "00:00:45",
                "Cross attention uses weighted sums.",
                "",
                "00:01:05",
                "In PyTorch we implement this with tensor operations.",
            ]
        ),
        encoding="utf-8",
    )

    p2_output = tmp_path / "p2_output.json"
    _write_json(p2_output, _make_p2_output())

    output_dir = tmp_path / "p3_inputs"
    build_p3_inputs_cli.build_p3_inputs(
        course_dirs=[course_dir],
        p2_output_path=p2_output,
        output_dir=output_dir,
    )

    p3c = json.loads(
        (output_dir / "p3c" / "CS224n" / "L7_p1" / "local--lecture07-attention-seg2.json").read_text(
            encoding="utf-8"
        )
    )
    assert p3c["question_intent"] == "procedural"
    assert p3c["target_item_count"] == 4
    assert p3c["target_kp_ids"] == ["kp_cross_attention"]
    assert p3c["assessment_purpose"] == "lecture_reinforcement"
    assert p3c["unit_summary_for_generation"] == "PyTorch tensor code [ts=40s] weighted sum [ts=70s]"
    assert p3c["youtube_url"] == "https://www.youtube.com/watch?v=abc123"
    assert p3c["allow_code_mcq"] is True
    assert p3c["allowed_item_types"] == ["concept_mcq", "code_mcq"]
    assert p3c["forbidden_question_patterns"] == []
    assert p3c["code_evidence"] == []
