from __future__ import annotations

import json
from pathlib import Path

from src.services.p3_input_sanitizer import sanitize_p3a_artifacts


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_sanitize_p3a_artifacts_repairs_placeholder_ids_and_urls(tmp_path: Path) -> None:
    input_dir = tmp_path / "p3a"
    payload = {
        "lecture_context": {
            "course_id": "CS231n",
            "lecture_id": "<lecture_id>",
            "lecture_title": "Lecture 13: Generative Models (part 1)",
            "youtube_url": "https://www.youtube.com/watch?v=zbHXQRUNlH0&list=demo&index=13",
        },
        "table_of_contents": [],
        "units": [
            {
                "unit_id": "local::<lecture_id>::seg1",
                "course_id": "<course_id>",
                "name": "Intro",
                "content_ref": {
                    "video_url": "https://www.youtube.com/watch?v=zbHXQRUNlH0&list=demo&index=13",
                    "start_s": 5,
                    "end_s": 42,
                },
            }
        ],
        "section_flags": [
            {
                "unit_id": "local::<lecture_id>::seg1",
                "importance_flag": "medium",
            }
        ],
        "unit_kp_map": [
            {
                "unit_id": "local::<lecture_id>::seg1",
                "global_kp_id": "kp_demo",
                "planner_role": "main",
                "coverage_level": "dominant",
            }
        ],
        "kp_catalog": [],
        "course_config": {"included_content_types": ["core_theory"]},
        "source_trace": {
            "p1_artifact": "data/CS231n/processed_sanitized/L13_p1.json",
            "p2_output": "data/p2_output_rationale_repaired.json",
            "transcript_file": "data/CS231n/transcripts/cs231n-2025-lecture13-generative-models-1_transcript.txt",
        },
    }
    _write_json(input_dir / "CS231n" / "L13_p1.json", payload)

    report = sanitize_p3a_artifacts(input_dir=input_dir, output_dir=input_dir)

    assert report["summary"]["processed_files"] == 1
    assert report["summary"]["sanitized_files"] == 1

    repaired = json.loads((input_dir / "CS231n" / "L13_p1.json").read_text(encoding="utf-8"))
    assert repaired["lecture_context"]["lecture_id"] == "cs231n-2025-lecture13-generative-models-1"
    assert repaired["lecture_context"]["youtube_url"] == "https://www.youtube.com/watch?v=zbHXQRUNlH0"
    assert repaired["units"][0]["unit_id"] == "local::cs231n-2025-lecture13-generative-models-1::seg1"
    assert repaired["units"][0]["course_id"] == "CS231n"
    assert repaired["units"][0]["content_ref"]["video_url"] == "https://www.youtube.com/watch?v=zbHXQRUNlH0"
    assert repaired["section_flags"][0]["unit_id"] == "local::cs231n-2025-lecture13-generative-models-1::seg1"
    assert repaired["unit_kp_map"][0]["unit_id"] == "local::cs231n-2025-lecture13-generative-models-1::seg1"
