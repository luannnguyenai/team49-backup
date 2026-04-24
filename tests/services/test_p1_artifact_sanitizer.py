from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.scripts.pipeline import sanitize_p1_artifacts as sanitize_cli
from src.services.p1_artifact_sanitizer import sanitize_p1_artifacts


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_sanitize_p1_artifacts_repairs_mechanical_unit_drift(tmp_path: Path) -> None:
    input_dir = tmp_path / "processed"
    output_dir = tmp_path / "processed_sanitized"
    input_dir.mkdir()

    raw_artifact = {
        "lecture_title": "Lecture 1",
        "table_of_contents": [],
        "units": [
            {
                "unit_id": "local::lecture_1::seg1",
                "course_id": "CS231N",
                "name": "Intro",
                "description": "Desc",
                "summary": "Summary [ts=1s] [ts=2s]",
                "key_points": [],
                "content_ref": {
                    "video_url": "[https://example.com/watch?v=abc123",
                    "start_s": 5,
                    "end_s": 180,
                },
                "difficulty": 0.2,
                "difficulty_source": "vlm_estimate",
                "difficulty_confidence": "high",
                "duration_min": 3,
                "ordering_index": 0,
                "is_template](https://example.com/watch?v=abc123%22,%22start_s%22:5,%22end_s%22:180,%22is_template)": False,
            }
        ],
        "concepts_kp_local": [],
        "unit_kp_map_local": [],
        "section_flags": [],
        "self_critique_trace": None,
    }
    _write_json(input_dir / "L1_p1.json", raw_artifact)

    report = sanitize_p1_artifacts(input_dir=input_dir, output_dir=output_dir)

    assert report["summary"]["processed_files"] == 1
    assert report["summary"]["sanitized_files"] == 1
    assert report["summary"]["invalid_files"] == 0

    sanitized = json.loads((output_dir / "L1_p1.json").read_text(encoding="utf-8"))
    unit = sanitized["units"][0]
    assert unit["content_ref"]["video_url"] == "https://example.com/watch?v=abc123"
    assert unit["is_template"] is False
    assert not any(key != "is_template" and "is_template" in key for key in unit)

    issue_codes = {issue["code"] for issue in report["files"][0]["issues"]}
    assert "unit_video_url_sanitized" in issue_codes
    assert "unit_is_template_key_recovered" in issue_codes


def test_sanitize_p1_artifacts_reports_empty_json_file_as_invalid(tmp_path: Path) -> None:
    input_dir = tmp_path / "processed"
    output_dir = tmp_path / "processed_sanitized"
    input_dir.mkdir()
    (input_dir / "L5_p1.json").write_text("", encoding="utf-8")

    report = sanitize_p1_artifacts(input_dir=input_dir, output_dir=output_dir)

    assert report["summary"]["processed_files"] == 1
    assert report["summary"]["invalid_files"] == 1
    assert not (output_dir / "L5_p1.json").exists()
    assert report["files"][0]["status"] == "invalid"
    assert report["files"][0]["issues"][0]["code"] == "invalid_json"


def test_sanitize_p1_cli_fails_when_invalid_files_remain(tmp_path: Path) -> None:
    input_dir = tmp_path / "processed"
    output_dir = tmp_path / "processed_sanitized"
    input_dir.mkdir()
    (input_dir / "L5_p1.json").write_text("", encoding="utf-8")

    result = CliRunner().invoke(
        sanitize_cli.app,
        ["--input-dir", str(input_dir), "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 1
    assert "invalid_files" in result.output
