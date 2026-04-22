from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.scripts import build_p2_input as build_p2_input_cli


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(body, encoding="utf-8")


def _make_p1_artifact(*, course_id: str, lecture_token: str, include_main: bool = True) -> dict:
    planner_role = "main" if include_main else "support"
    return {
        "lecture_title": f"{lecture_token} title",
        "table_of_contents": [],
        "units": [
            {
                "unit_id": f"local::{lecture_token}::seg1",
                "course_id": course_id,
                "name": "Unit 1",
                "description": "Unit desc",
                "summary": "Dense summary [ts=11s] and more [ts=42s]",
                "key_points": [],
                "content_ref": {
                    "video_url": "https://example.com/watch?v=1",
                    "start_s": 0,
                    "end_s": 120,
                },
                "difficulty": 0.3,
                "difficulty_source": "vlm_estimate",
                "difficulty_confidence": "high",
                "duration_min": 2,
                "ordering_index": 0,
                "is_template": False,
            }
        ],
        "concepts_kp_local": [
            {
                "local_kp_id": f"local::{lecture_token}::kp1",
                "name": "Backpropagation",
                "description": "Chain rule for neural nets",
                "track_tags": ["ml"],
                "domain_tags": ["optimization"],
                "career_path_tags": ["ml-engineer"],
                "difficulty_level": 0.6,
                "difficulty_source": "vlm_estimate",
                "difficulty_confidence": "medium",
                "importance_level": "critical",
                "structural_role": "gateway",
                "importance_confidence": "high",
                "importance_rationale": "Core prerequisite",
                "importance_scope": "course_global",
                "importance_source": "llm_single_pass",
                "visual_evidence": "whiteboard formula",
            }
        ],
        "unit_kp_map_local": [
            {
                "unit_id": f"local::{lecture_token}::seg1",
                "local_kp_id": f"local::{lecture_token}::kp1",
                "planner_role": planner_role,
                "instruction_role": "main",
                "coverage_level": "dominant",
                "coverage_confidence": "high",
                "coverage_rationale": "Explained at [ts=11s]",
            }
        ],
        "section_flags": [],
        "self_critique_trace": None,
    }


def test_build_p2_input_projects_lean_fields_and_uses_video_order(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS231n"
    processed_dir = course_dir / "processed_sanitized"
    videos_dir = course_dir / "videos"
    processed_dir.mkdir(parents=True)
    videos_dir.mkdir()

    _write_json(course_dir / "syllabus.json", {"course": "STALE", "lectures": ["wrong"]})
    _write_json(processed_dir / "L1_p1.json", _make_p1_artifact(course_id="CS231N", lecture_token="lecture_1"))
    _write_json(processed_dir / "L2_p1.json", _make_p1_artifact(course_id="CS231N", lecture_token="lecture_2"))

    for name in [
        "Lecture 10 - Video Understanding.mp4",
        "Lecture 2 - Linear Classifiers.mp4",
        "Lecture 1 - Introduction.mp4",
    ]:
        (videos_dir / name).write_text("", encoding="utf-8")

    output_dir = tmp_path / "out"
    result = build_p2_input_cli.build_p2_input(
        course_dirs=[course_dir],
        output_dir=output_dir,
        run_id="run-001",
        p2_mode="batch_initial",
    )

    bundle = json.loads((output_dir / "p2_input_bundle.json").read_text(encoding="utf-8"))
    assert result["summary"]["local_concepts_kp"] == 2
    assert result["summary"]["local_unit_kp_map"] == 2
    assert bundle["tag_registry"] == []

    kp_row = bundle["local_concepts_kp"][0]
    assert kp_row == {
        "local_kp_id": "local::lecture_1::kp1",
        "name": "Backpropagation",
        "description": "Chain rule for neural nets",
        "track_tags": ["ml"],
        "domain_tags": ["optimization"],
        "career_path_tags": ["ml_engineer"],
        "importance_level": "critical",
        "structural_role": "gateway",
        "difficulty_level": 0.6,
        "source_course_id": "CS231n",
        "source_lecture_id": "lecture_1",
    }

    map_row = bundle["local_unit_kp_map"][0]
    assert map_row == {
        "unit_id": "local::lecture_1::seg1",
        "local_kp_id": "local::lecture_1::kp1",
        "planner_role": "main",
        "coverage_level": "dominant",
    }

    course_meta = bundle["course_registry"]["courses"][0]
    assert course_meta["id"] == "CS231n"
    assert course_meta["name"] == "CS231n"
    assert course_meta["track"] == "cv"
    assert course_meta["lecture_order"] == ["lecture-1", "lecture-2", "lecture-10"]

    assert (output_dir / "p2_input_bundle.json").exists()
    assert (output_dir / "prompt_rendered.txt").exists()


def test_build_p2_input_includes_snapshot_catalogs_in_append_mode(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS224n"
    processed_dir = course_dir / "processed_sanitized"
    videos_dir = course_dir / "videos"
    processed_dir.mkdir(parents=True)
    videos_dir.mkdir()

    _write_json(processed_dir / "L1_p1.json", _make_p1_artifact(course_id="cs224n-2024", lecture_token="lecture01-wordvecs"))
    (videos_dir / "cs224n-2024-lecture01-wordvecs.mp4").write_text("", encoding="utf-8")

    template_file = tmp_path / "template.md"
    template_file.write_text(
        "KPS=<all_local_kps>\nMAP=<all_local_map>\nCOURSE=<course_metadata>\nTAGS=<frozen_tag_registry>\n"
        "GLOBALS=<existing_globals>\nEDGES=<existing_edges>\n",
        encoding="utf-8",
    )

    tag_registry_file = tmp_path / "tag_registry.json"
    _write_json(tag_registry_file, [{"tag": "nlp"}])

    snapshot_dir = tmp_path / "snapshots" / "snap-1"
    _write_jsonl(snapshot_dir / "concepts_kp_global.jsonl", [{"global_kp_id": "g1", "name": "Attention"}])
    _write_jsonl(snapshot_dir / "prerequisite_edges.jsonl", [{"edge_id": "e1", "source": "g0", "target": "g1"}])

    output_dir = tmp_path / "out"
    result = build_p2_input_cli.build_p2_input(
        course_dirs=[course_dir],
        output_dir=output_dir,
        run_id="run-append",
        p2_mode="append_incremental",
        snapshot_dir=snapshot_dir,
        tag_registry_file=tag_registry_file,
        template_file=template_file,
    )

    bundle = json.loads((output_dir / "p2_input_bundle.json").read_text(encoding="utf-8"))
    assert bundle["tag_registry"] == [{"tag": "nlp"}]
    assert bundle["existing_global_catalog"] == [{"global_kp_id": "g1", "name": "Attention"}]
    assert bundle["existing_edge_catalog"] == [{"edge_id": "e1", "source": "g0", "target": "g1"}]
    assert result["summary"]["status"] == "ok"

    rendered = (output_dir / "prompt_rendered.txt").read_text(encoding="utf-8")
    assert '"global_kp_id": "g1"' in rendered
    assert '"edge_id": "e1"' in rendered


def test_build_p2_input_fails_fast_on_invalid_p1_contract(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS224n"
    processed_dir = course_dir / "processed_sanitized"
    videos_dir = course_dir / "videos"
    processed_dir.mkdir(parents=True)
    videos_dir.mkdir()
    (videos_dir / "lecture-1.mp4").write_text("", encoding="utf-8")

    broken = _make_p1_artifact(course_id="cs224n-2024", lecture_token="lecture-broken", include_main=False)
    broken["units"][0]["summary"] = "Only one timestamp [ts=11s]"
    broken["unit_kp_map_local"][0]["local_kp_id"] = "local::lecture-broken::kp999"
    _write_json(processed_dir / "L1_p1.json", broken)

    with pytest.raises(ValueError) as excinfo:
        build_p2_input_cli.build_p2_input(
            course_dirs=[course_dir],
            output_dir=tmp_path / "out",
            run_id="run-bad",
            p2_mode="batch_initial",
        )

    message = str(excinfo.value)
    assert "missing planner_role=main" in message
    assert "orphan local_kp_id" in message
    assert "at least 2 timestamps" in message


def test_build_p2_input_repairs_placeholder_ids_and_normalizes_fields(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS224n"
    processed_dir = course_dir / "processed_sanitized"
    videos_dir = course_dir / "videos"
    processed_dir.mkdir(parents=True)
    videos_dir.mkdir()

    placeholder = _make_p1_artifact(course_id="<course_id>", lecture_token="<lecture_id>")
    placeholder["lecture_title"] = "Lecture 7 - Attention, Final Projects and LLM Intro"
    placeholder["concepts_kp_local"][0]["track_tags"] = ["NLP", "post-training"]
    placeholder["concepts_kp_local"][0]["domain_tags"] = ["deep-learning", "Natural Language Processing"]
    placeholder["concepts_kp_local"][0]["career_path_tags"] = ["LLM engineer"]
    placeholder["concepts_kp_local"][0]["difficulty_level"] = 2.8
    _write_json(processed_dir / "L7_p1.json", placeholder)
    (videos_dir / "cs224n-2024-lecture07-attention.mp4").write_text("", encoding="utf-8")

    output_dir = tmp_path / "out"
    build_p2_input_cli.build_p2_input(
        course_dirs=[course_dir],
        output_dir=output_dir,
        run_id="run-placeholder",
        p2_mode="batch_initial",
    )

    bundle = json.loads((output_dir / "p2_input_bundle.json").read_text(encoding="utf-8"))
    kp_row = bundle["local_concepts_kp"][0]
    map_row = bundle["local_unit_kp_map"][0]

    assert kp_row["local_kp_id"] == "local::lecture07-attention::kp1"
    assert kp_row["source_lecture_id"] == "lecture07-attention"
    assert kp_row["track_tags"] == ["nlp", "post_training"]
    assert kp_row["domain_tags"] == ["deep_learning", "natural_language_processing"]
    assert kp_row["career_path_tags"] == ["llm_engineer"]
    assert kp_row["difficulty_level"] == 0.56
    assert map_row["unit_id"] == "local::lecture07-attention::seg1"
    assert map_row["local_kp_id"] == "local::lecture07-attention::kp1"


def test_build_p2_input_dedupes_identical_local_kp_ids(tmp_path: Path) -> None:
    course_dir = tmp_path / "CS224n"
    processed_dir = course_dir / "processed_sanitized"
    videos_dir = course_dir / "videos"
    processed_dir.mkdir(parents=True)
    videos_dir.mkdir()

    artifact = _make_p1_artifact(course_id="cs224n", lecture_token="lecture16_multimodal_deep_learning")
    _write_json(processed_dir / "L16_p1.json", artifact)
    _write_json(processed_dir / "Lsup_multimodal_p1.json", artifact)
    (videos_dir / "cs224n-2024-lecture16-multimodal.mp4").write_text("", encoding="utf-8")

    output_dir = tmp_path / "out"
    result = build_p2_input_cli.build_p2_input(
        course_dirs=[course_dir],
        output_dir=output_dir,
        run_id="run-dedupe",
        p2_mode="batch_initial",
    )

    bundle = json.loads((output_dir / "p2_input_bundle.json").read_text(encoding="utf-8"))
    assert result["summary"]["local_concepts_kp"] == 1
    assert result["summary"]["local_unit_kp_map"] == 1
    assert bundle["local_concepts_kp"][0]["local_kp_id"] == "local::lecture16_multimodal_deep_learning::kp1"
