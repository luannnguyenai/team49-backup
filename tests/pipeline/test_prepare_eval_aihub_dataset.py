import json

from src.scripts.pipeline.prepare_eval_aihub_dataset import (
    build_eval_sample,
    compute_window_bounds,
    extract_transcript_window,
)


def test_compute_window_bounds_applies_margin_and_clamps_to_unit_range():
    source_ref = {"timestamp_start": 166, "timestamp_end": 215}
    content_ref = {"start_s": 80, "end_s": 299}

    assert compute_window_bounds(source_ref, content_ref, margin_s=90) == (80, 299)


def test_extract_transcript_window_keeps_timestamped_segments_in_range():
    transcript = """Title: Demo
URL: https://example.test
============================================================

00:01:10
Before the window.

00:01:20
The relevant introduction.

00:02:46
Evidence starts here.

00:03:35
Evidence ends here.

00:05:06
After the window.
"""

    window = extract_transcript_window(transcript, start_s=76, end_s=305)

    assert window["start_s"] == 76
    assert window["end_s"] == 305
    assert "The relevant introduction." in window["text"]
    assert "Evidence starts here." in window["text"]
    assert "Evidence ends here." in window["text"]
    assert "Before the window." not in window["text"]
    assert "After the window." not in window["text"]


def test_build_eval_sample_uses_existing_fields_and_hides_choices_from_input():
    question = {
        "item_id": "q1",
        "course_id": "CS224n",
        "lecture_id": "lecture-19",
        "unit_id": "unit-1",
        "item_type": "concept_mcq",
        "question": "Why is this tool insufficient?",
        "choices": ["wrong", "It is slow and tiring", "other"],
        "answer_index": 1,
        "explanation": "The existing tool requires slow, exhausting control.",
        "difficulty": "easy",
        "question_intent": "conceptual",
        "knowledge_scope": "transferable",
        "assessment_purpose": "lecture_reinforcement",
        "grounding_mode": "transcript_only",
        "grounding_confidence": "high",
        "primary_kp_id": "kp-1",
        "source_ref": {
            "unit_id": "unit-1",
            "timestamp_start": 166,
            "timestamp_end": 215,
            "evidence_span": "slow and tiring",
            "multimodal_signals_used": ["transcript"],
            "video_clip_ref": None,
            "video_url": "https://example.test/video",
        },
    }
    unit = {
        "unit_id": "unit-1",
        "lecture_title": "Lecture 19",
        "lecture_order": 19,
        "unit_name": "Motivation",
        "description": "Explains why existing tools are insufficient.",
        "summary": "The unit says the tools are slow and tiring.",
        "key_points": [{"text": "Letter boards are slow.", "timestamp_s": 166}],
        "content_ref": {"start_s": 80, "end_s": 299},
        "transcript_path": "data/courses/demo/transcript.txt",
        "content_type": "core_theory",
        "salience_score": "high",
    }
    kp = {
        "kp_id": "kp-1",
        "name": "Assistive communication limits",
        "description": "Existing tools can remain slow and tiring.",
        "importance_level": "high",
        "structural_role": "supporting",
    }

    sample = build_eval_sample(
        question=question,
        unit=unit,
        kp=kp,
        transcript_window={"start_s": 80, "end_s": 299, "text": "Window text"},
        eval_tier="A_text_grounded_high_confidence",
    )

    encoded_input = json.dumps(sample["input"], ensure_ascii=False)
    assert "choices" not in sample["input"]
    assert "wrong" not in encoded_input
    assert sample["reference"]["answer_text"] == "It is slow and tiring"
    assert sample["reference"]["explanation"] == question["explanation"]
    assert sample["input"]["context"]["source_evidence_span"] == "slow and tiring"
