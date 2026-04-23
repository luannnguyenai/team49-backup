"""Export canonical ingestion artifacts from P1/P2/P4/P5 outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.data_paths import (
    CANONICAL_ARTIFACTS_DIR,
    CANONICAL_MANIFEST_FILE,
    CANONICAL_VALIDATION_REPORT_FILE,
    COURSES_DIR,
    FINAL_ARTIFACTS_DIR,
    GPT54_EDGE_LABELS_FILE,
    P2_OUTPUT_FILE,
    P5_TRANSITIVE_PRUNED_FILE,
)


PHASE_ENUM = {
    "placement",
    "mini_quiz",
    "skip_verification",
    "bridge_check",
    "final_quiz",
    "transfer",
    "review",
}
REVIEW_STATUS_ENUM = {"not_required", "auto_accepted", "deferred", "optional", "reviewed"}
PROVENANCE_ENUM = {
    "llm_single_pass",
    "vlm_estimate",
    "vlm_grounded",
    "llm_self_critique",
    "llm_cross_check",
    "llm_consensus",
    "llm_self_repaired",
    "llm_auto_pruned",
    "llm_direction_repaired",
    "modernbert_pred",
    "rule_based",
    "human_ta_verified",
    "gpt54_audit",
}
QUESTION_INTENT_ENUM = {"conceptual", "procedural", "diagnostic", "application"}

_COVERAGE_BASE = {"dominant": 1.0, "substantial": 0.75, "partial": 0.5, "mention": 0.25}
_IMPORTANCE_BASE = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
_CONFIDENCE_MULTIPLIER = {"high": 1.0, "medium": 0.8, "low": 0.6}
_ITEM_WEIGHT = {"primary": 0.7, "secondary": 0.3, "support": 0.0}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).lower().split())


def _parse_timestamp_to_seconds(value: str | int | float | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    parts = text.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    if len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    return None


def _round4(value: float) -> float:
    return round(value, 4)


def _coverage_weight(level: str | None, confidence: str | None) -> float | None:
    if level not in _COVERAGE_BASE or confidence not in _CONFIDENCE_MULTIPLIER:
        return None
    return _round4(_COVERAGE_BASE[level] * _CONFIDENCE_MULTIPLIER[confidence])


def _importance_score(level: str | None, confidence: str | None) -> float | None:
    if level not in _IMPORTANCE_BASE or confidence not in _CONFIDENCE_MULTIPLIER:
        return None
    return _round4(_IMPORTANCE_BASE[level] * _CONFIDENCE_MULTIPLIER[confidence])


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _transcript_path_for_lecture(course_dir: Path, lecture: dict[str, Any]) -> Path | None:
    transcript_name = lecture.get("assets", {}).get("transcript")
    if not transcript_name:
        return None
    path = course_dir / "transcripts" / transcript_name
    return path if path.exists() else None


def _build_course_context(courses_dir: Path, selected_courses: list[str] | None) -> tuple[list[dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    course_rows: list[dict[str, Any]] = []
    lecture_index: dict[tuple[str, int], dict[str, Any]] = {}

    wanted = set(selected_courses or [])
    for course_dir in sorted(path for path in courses_dir.iterdir() if path.is_dir()):
        if wanted and course_dir.name not in wanted:
            continue
        syllabus_path = course_dir / "syllabus.json"
        if not syllabus_path.exists():
            continue
        syllabus = _load_json(syllabus_path)
        lectures = syllabus.get("lectures", [])
        course_rows.append(
            {
                "course_id": course_dir.name,
                "course_name": syllabus.get("course"),
                "source": syllabus.get("source"),
                "note": syllabus.get("note"),
                "reference_slides_no_video": syllabus.get("reference_slides_no_video", []),
                "lecture_count": len(lectures),
                "track_tags": [],
                "summary_embedding": None,
                "source_file": _relative(syllabus_path, courses_dir.parents[1]),
            }
        )
        for lecture in lectures:
            order = lecture.get("custom_order") or lecture.get("lecture_number")
            if order is None:
                continue
            lecture_index[(course_dir.name, int(order))] = {
                "lecture_id": lecture.get("lecture_id") or f"{course_dir.name.lower()}-lecture-{order}",
                "lecture_order": int(order),
                "lecture_title": _first_non_empty(
                    lecture.get("title"),
                    lecture.get("lecture_title"),
                    lecture.get("youtube_title"),
                    lecture.get("topic"),
                ),
                "transcript_path": _transcript_path_for_lecture(course_dir, lecture),
                "lecture_source": lecture,
            }
    return course_rows, lecture_index


def _build_concepts_rows(p2: dict[str, Any], source_file: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in p2.get("concepts_kp_global", []):
        rows.append(
            {
                "kp_id": item["global_kp_id"],
                "name": item.get("name"),
                "description": item.get("description"),
                "track_tags": item.get("track_tags", []),
                "domain_tags": item.get("domain_tags", []),
                "career_path_tags": item.get("career_path_tags", []),
                "difficulty_level": item.get("difficulty_level"),
                "difficulty_source": item.get("difficulty_source"),
                "difficulty_confidence": item.get("difficulty_confidence"),
                "importance_level": item.get("importance_level"),
                "structural_role": item.get("structural_role"),
                "importance_confidence": item.get("importance_confidence"),
                "importance_rationale": item.get("importance_rationale"),
                "importance_scope": item.get("importance_scope"),
                "importance_source": item.get("importance_source"),
                "source_course_ids": item.get("source_course_ids", []),
                "importance": _importance_score(item.get("importance_level"), item.get("importance_confidence")),
                "description_embedding": None,
                "source_file": source_file,
            }
        )
    return rows


def _build_unit_tables(
    *,
    courses_dir: Path,
    lecture_index: dict[tuple[str, int], dict[str, Any]],
    local_to_global: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    unit_rows: list[dict[str, Any]] = []
    unit_kp_candidates: dict[tuple[str, str], dict[str, Any]] = {}
    unit_index: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []

    repo_root = courses_dir.parents[1]

    for course_dir in sorted(path for path in courses_dir.iterdir() if path.is_dir()):
        sanitized_dir = course_dir / "processed_sanitized"
        if not sanitized_dir.exists():
            continue
        for p1_path in sorted(sanitized_dir.glob("L*_p1.json")):
            artifact = _load_json(p1_path)
            lecture_order = int(p1_path.stem.split("_", 1)[0].removeprefix("L"))
            lecture_meta = lecture_index.get((course_dir.name, lecture_order), {})
            section_flags = {
                row["unit_id"]: row
                for row in artifact.get("section_flags", [])
                if isinstance(row, dict) and row.get("unit_id")
            }
            for unit in artifact.get("units", []):
                unit_id = unit["unit_id"]
                content_ref = unit.get("content_ref") or {}
                row = {
                    "unit_id": unit_id,
                    "course_id": course_dir.name,
                    "lecture_id": _first_non_empty(lecture_meta.get("lecture_id"), artifact.get("lecture_id"), p1_path.stem),
                    "lecture_order": lecture_order,
                    "lecture_title": _first_non_empty(lecture_meta.get("lecture_title"), artifact.get("lecture_title")),
                    "unit_name": unit.get("name"),
                    "description": unit.get("description"),
                    "summary": unit.get("summary"),
                    "key_points": unit.get("key_points", []),
                    "content_ref": content_ref,
                    "difficulty": unit.get("difficulty"),
                    "difficulty_source": unit.get("difficulty_source"),
                    "difficulty_confidence": unit.get("difficulty_confidence"),
                    "duration_min": unit.get("duration_min"),
                    "ordering_index": unit.get("ordering_index"),
                    "section_flags": section_flags.get(unit_id),
                    "video_clip_ref": None,
                    "topic_embedding": None,
                    "source_file": _relative(p1_path, repo_root),
                    "transcript_path": str(lecture_meta.get("transcript_path")) if lecture_meta.get("transcript_path") else None,
                }
                unit_rows.append(row)
                unit_index[unit_id] = row

            for local_row in artifact.get("unit_kp_map_local", []):
                if not isinstance(local_row, dict):
                    continue
                global_kp_id = local_to_global.get(local_row.get("local_kp_id"))
                if not global_kp_id:
                    rejected.append(
                        {
                            "row_kind": "unit_kp_map",
                            "row_id": f'{local_row.get("unit_id")}::{local_row.get("local_kp_id")}',
                            "hard_fail_reason": "missing_global_kp_mapping",
                            "source_file": _relative(p1_path, repo_root),
                            "payload": local_row,
                        }
                    )
                    continue
                key = (local_row["unit_id"], global_kp_id)
                candidate = {
                    "unit_id": local_row["unit_id"],
                    "kp_id": global_kp_id,
                    "planner_role": local_row.get("planner_role"),
                    "instruction_role": local_row.get("instruction_role"),
                    "coverage_level": local_row.get("coverage_level"),
                    "coverage_confidence": local_row.get("coverage_confidence"),
                    "coverage_rationale": local_row.get("coverage_rationale"),
                    "coverage_weight": _coverage_weight(
                        local_row.get("coverage_level"),
                        local_row.get("coverage_confidence"),
                    ),
                    "source_local_kp_ids": [local_row.get("local_kp_id")],
                    "source_file": _relative(p1_path, repo_root),
                }
                existing = unit_kp_candidates.get(key)
                if existing is None or (candidate["coverage_weight"] or 0.0) > (existing["coverage_weight"] or 0.0):
                    if existing:
                        candidate["source_local_kp_ids"] = sorted(
                            set(existing["source_local_kp_ids"] + candidate["source_local_kp_ids"])
                        )
                    unit_kp_candidates[key] = candidate
                elif existing:
                    existing["source_local_kp_ids"] = sorted(
                        set(existing["source_local_kp_ids"] + candidate["source_local_kp_ids"])
                    )

    unit_kp_rows = sorted(unit_kp_candidates.values(), key=lambda row: (row["unit_id"], row["kp_id"]))
    return unit_rows, unit_kp_rows, unit_index, rejected


def _load_transcript_cache(unit_rows: list[dict[str, Any]]) -> dict[str, str]:
    cache: dict[str, str] = {}
    for row in unit_rows:
        transcript_path = row.get("transcript_path")
        if not transcript_path or transcript_path in cache:
            continue
        path = Path(transcript_path)
        cache[transcript_path] = path.read_text(encoding="utf-8") if path.exists() else ""
    return cache


def _derive_source_ref(item: dict[str, Any], artifact: dict[str, Any], unit_row: dict[str, Any], transcript_text: str) -> dict[str, Any]:
    evidence = item.get("evidence") or {}
    transcript_quotes = [quote.strip() for quote in evidence.get("transcript_quotes", []) if str(quote).strip()]
    normalized_transcript = _normalize_text(transcript_text)
    evidence_span = None
    for quote in sorted(transcript_quotes, key=len, reverse=True):
        if _normalize_text(quote) in normalized_transcript:
            evidence_span = quote
            break
    if evidence_span is None and transcript_quotes:
        evidence_span = transcript_quotes[0]

    timestamp_values = [
        _parse_timestamp_to_seconds(value)
        for value in evidence.get("timestamps", [])
        if _parse_timestamp_to_seconds(value) is not None
    ]
    timestamp_start = min(timestamp_values) if timestamp_values else None
    timestamp_end = max(timestamp_values) if timestamp_values else None

    return {
        "unit_id": unit_row["unit_id"],
        "timestamp_start": timestamp_start,
        "timestamp_end": timestamp_end,
        "evidence_span": evidence_span,
        "multimodal_signals_used": ["transcript"] if evidence_span else [],
        "video_clip_ref": None,
        "video_url": _first_non_empty(artifact.get("youtube_url"), unit_row.get("content_ref", {}).get("video_url")),
    }


def _expand_phase_rows(item_id: str, row: dict[str, Any], common: dict[str, Any]) -> list[dict[str, Any]]:
    suitability = row.get("suitability_by_phase", {})
    multipliers = row.get("phase_multiplier_by_phase", {})
    phases = sorted(set(suitability) | set(multipliers))
    output = []
    for phase in phases:
        output.append(
            {
                **common,
                "item_id": item_id,
                "phase": phase,
                "phase_multiplier": multipliers.get(phase),
                "suitability_score": suitability.get(phase),
                "selection_priority": None,
                "phase_rationale": row.get("phase_rationale"),
            }
        )
    return output


def _build_question_tables(
    *,
    courses_dir: Path,
    unit_index: dict[str, dict[str, Any]],
    transcript_cache: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    question_rows: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    phase_rows: list[dict[str, Any]] = []
    kp_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    repo_root = courses_dir.parents[1]

    for course_dir in sorted(path for path in courses_dir.iterdir() if path.is_dir()):
        p4_root = course_dir / "processed" / "P4"
        if not p4_root.exists():
            continue
        for path in sorted(p4_root.rglob("*.json")):
            artifact = _load_json(path)
            unit_id = artifact.get("unit_id")
            unit_row = unit_index.get(unit_id)
            if not unit_row:
                rejected.append(
                    {
                        "row_kind": "question_bundle",
                        "row_id": unit_id or str(path),
                        "hard_fail_reason": "unknown_unit_id",
                        "source_file": _relative(path, repo_root),
                        "payload": {"unit_id": unit_id},
                    }
                )
                continue
            transcript_text = transcript_cache.get(unit_row.get("transcript_path") or "", "")
            item_phase_map_by_id = {
                row["item_id"]: row
                for row in artifact.get("item_phase_map", [])
                if isinstance(row, dict) and row.get("item_id")
            }
            item_calibration_by_id = {
                row["item_id"]: row
                for row in artifact.get("item_calibration_bootstrap", [])
                if isinstance(row, dict) and row.get("item_id")
            }
            per_item_kp_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for kp_row in artifact.get("item_kp_map", []):
                if isinstance(kp_row, dict) and kp_row.get("item_id"):
                    per_item_kp_rows[kp_row["item_id"]].append(kp_row)

            for item in artifact.get("repaired_question_bank", []):
                if not isinstance(item, dict):
                    continue
                item_id = item["item_id"]
                source_ref = _derive_source_ref(item, artifact, unit_row, transcript_text)
                common = {
                    "course_id": unit_row["course_id"],
                    "lecture_id": unit_row["lecture_id"],
                    "unit_id": unit_row["unit_id"],
                    "source_file": _relative(path, repo_root),
                }
                question_rows.append(
                    {
                        **common,
                        "item_id": item_id,
                        "item_type": item.get("item_type"),
                        "knowledge_scope": item.get("knowledge_scope"),
                        "render_mode": item.get("render_mode"),
                        "question": item.get("question"),
                        "choices": item.get("choices"),
                        "answer_index": item.get("answer_index"),
                        "explanation": item.get("explanation"),
                        "primary_kp_id": item.get("primary_kp_id"),
                        "source_ref": source_ref,
                        "difficulty": item.get("difficulty"),
                        "question_intent": artifact.get("question_intent"),
                        "qa_gate_passed": item.get("qa_gate_passed"),
                        "review_status": item.get("review_status"),
                        "repair_history": item.get("repair_history", []),
                        "provenance": item.get("provenance"),
                        "concept_alignment_cosine": None,
                        "distractor_cosine_upper": None,
                        "distractor_cosine_lower": None,
                        "assessment_purpose": artifact.get("assessment_purpose"),
                        "grounding_mode": artifact.get("grounding_mode"),
                        "grounding_confidence": artifact.get("grounding_confidence"),
                    }
                )

                calibration = item_calibration_by_id.get(item_id, {})
                calibration_rows.append(
                    {
                        **common,
                        "item_id": item_id,
                        "calibration_method": calibration.get("calibration_method", "prior_only"),
                        "is_calibrated": calibration.get("is_calibrated", False),
                        "difficulty_prior": calibration.get("difficulty_prior"),
                        "discrimination_prior": calibration.get("discrimination_prior"),
                        "guessing_prior": calibration.get("guessing_prior"),
                        "difficulty_b": calibration.get("difficulty_b"),
                        "discrimination_a": calibration.get("discrimination_a"),
                        "guessing_c": calibration.get("guessing_c"),
                        "irt_calibration_n": calibration.get("irt_calibration_n", 0),
                        "standard_error_b": calibration.get("standard_error_b"),
                        "calibration_confidence": calibration.get("calibration_confidence"),
                        "calibration_rationale": calibration.get("calibration_rationale"),
                    }
                )

                phase_payload = item_phase_map_by_id.get(item_id, {})
                phase_rows.extend(_expand_phase_rows(item_id, phase_payload, common))

                for kp_row in per_item_kp_rows.get(item_id, []):
                    role = kp_row.get("role")
                    kp_rows.append(
                        {
                            **common,
                            "item_id": item_id,
                            "kp_id": kp_row.get("global_kp_id"),
                            "kp_role": role,
                            "weight": _ITEM_WEIGHT.get(role, 0.0),
                            "mapping_confidence": None,
                        }
                    )

    return question_rows, calibration_rows, phase_rows, kp_rows, rejected


def _build_edge_tables(
    *,
    p5: dict[str, Any],
    gpt54: dict[str, Any],
    source_file: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    p5_edge_index = {
        (row["source_kp_id"], row["target_kp_id"]): row
        for row in p5.get("clean_candidate_edges", [])
        if isinstance(row, dict)
    }
    p5_pruned_index = {
        (row["source_kp_id"], row["target_kp_id"]): row
        for row in p5.get("pruned_edges", [])
        if isinstance(row, dict)
    }

    keep_rows: list[dict[str, Any]] = []
    pruned_rows: list[dict[str, Any]] = []
    kept_pairs: set[tuple[str, str]] = set()
    pruned_pairs: set[tuple[str, str]] = set()

    for row in gpt54.get("edge_labels", []):
        pair = (row["source_kp_id"], row["target_kp_id"])
        p5_row = p5_edge_index.get(pair)
        payload = {
            "source_kp_id": row["source_kp_id"],
            "target_kp_id": row["target_kp_id"],
            "edge_scope": p5_row.get("edge_scope") if p5_row else None,
            "provenance": p5_row.get("provenance") if p5_row else "gpt54_audit",
            "confidence": row.get("best_confidence"),
            "review_status": row.get("best_review_status"),
            "rationale": row.get("best_rationale"),
            "temporal_signal": row.get("temporal_signal"),
            "source_first_seen": row.get("source_first_seen"),
            "target_first_seen": row.get("target_first_seen"),
            "p5_keep_confidence": row.get("p5_keep_confidence"),
            "p5_expected_directionality": row.get("p5_expected_directionality"),
            "p5_trace": row.get("p5_trace"),
            "edge_strength": None,
            "bidirectional_score": None,
            "source_file": source_file,
        }
        if row.get("best_verdict") == "keep":
            keep_rows.append(payload)
            kept_pairs.add(pair)
        else:
            pruned_rows.append(
                {
                    **payload,
                    "prune_reason": row.get("best_prune_reason"),
                }
            )
            pruned_pairs.add(pair)

    for pair, row in p5_pruned_index.items():
        if pair in kept_pairs or pair in pruned_pairs:
            continue
        pruned_rows.append(
            {
                "source_kp_id": row["source_kp_id"],
                "target_kp_id": row["target_kp_id"],
                "edge_scope": None,
                "provenance": row.get("provenance"),
                "confidence": None,
                "review_status": None,
                "rationale": row.get("prune_rationale"),
                "temporal_signal": None,
                "source_first_seen": None,
                "target_first_seen": None,
                "p5_keep_confidence": None,
                "p5_expected_directionality": None,
                "p5_trace": None,
                "edge_strength": None,
                "bidirectional_score": None,
                "prune_reason": row.get("prune_reason"),
                "source_file": source_file,
            }
        )
    return keep_rows, pruned_rows


def _reject_row(rejected: list[dict[str, Any]], *, row_kind: str, row_id: str, reason: str, source_file: str, payload: Any) -> None:
    rejected.append(
        {
            "row_kind": row_kind,
            "row_id": row_id,
            "hard_fail_reason": reason,
            "source_file": source_file,
            "payload": payload,
        }
    )


def _dedupe_rows(
    rows: list[dict[str, Any]],
    *,
    key_fn,
    row_kind: str,
    rejected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen = set()
    output = []
    for row in rows:
        key = key_fn(row)
        if key in seen:
            _reject_row(
                rejected,
                row_kind=row_kind,
                row_id=str(key),
                reason="duplicate_key",
                source_file=row.get("source_file", ""),
                payload=row,
            )
            continue
        seen.add(key)
        output.append(row)
    return output


def validate_canonical_tables(
    *,
    tables: dict[str, list[dict[str, Any]]],
    transcript_cache: dict[str, str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], dict[str, Any]]:
    rejected: list[dict[str, Any]] = list(tables.get("rejected_items", []))
    unit_rows = _dedupe_rows(tables["units"], key_fn=lambda row: row["unit_id"], row_kind="units", rejected=rejected)
    concept_rows = _dedupe_rows(tables["concepts_kp"], key_fn=lambda row: row["kp_id"], row_kind="concepts_kp", rejected=rejected)
    question_rows = _dedupe_rows(tables["question_bank"], key_fn=lambda row: row["item_id"], row_kind="question_bank", rejected=rejected)
    unit_kp_rows = _dedupe_rows(
        tables["unit_kp_map"],
        key_fn=lambda row: (row["unit_id"], row["kp_id"]),
        row_kind="unit_kp_map",
        rejected=rejected,
    )
    prerequisite_rows = _dedupe_rows(
        tables["prerequisite_edges"],
        key_fn=lambda row: (row["source_kp_id"], row["target_kp_id"]),
        row_kind="prerequisite_edges",
        rejected=rejected,
    )
    pruned_rows = _dedupe_rows(
        tables["pruned_edges"],
        key_fn=lambda row: (row["source_kp_id"], row["target_kp_id"]),
        row_kind="pruned_edges",
        rejected=rejected,
    )

    valid_course_ids = {row["course_id"] for row in tables["courses"]}
    valid_unit_ids = {row["unit_id"] for row in unit_rows}
    valid_kp_ids = {row["kp_id"] for row in concept_rows}
    valid_item_ids: set[str] = set()

    validated_units = []
    for row in unit_rows:
        if row["course_id"] not in valid_course_ids:
            _reject_row(rejected, row_kind="units", row_id=row["unit_id"], reason="unknown_course_id", source_file=row["source_file"], payload=row)
            continue
        content_ref = row.get("content_ref") or {}
        start_s = content_ref.get("start_s")
        end_s = content_ref.get("end_s")
        key_points = row.get("key_points") or []
        bad_keypoint = False
        if start_s is not None and end_s is not None:
            for point in key_points:
                ts = point.get("timestamp_s")
                if ts is not None and not (start_s <= ts <= end_s):
                    _reject_row(
                        rejected,
                        row_kind="units",
                        row_id=row["unit_id"],
                        reason="key_point_timestamp_out_of_bounds",
                        source_file=row["source_file"],
                        payload=point,
                    )
                    bad_keypoint = True
                    break
        if bad_keypoint:
            continue
        validated_units.append(row)
    unit_rows = validated_units
    valid_unit_ids = {row["unit_id"] for row in unit_rows}

    validated_unit_kp = []
    for row in unit_kp_rows:
        if row["unit_id"] not in valid_unit_ids:
            _reject_row(rejected, row_kind="unit_kp_map", row_id=f'{row["unit_id"]}::{row["kp_id"]}', reason="unknown_unit_id", source_file=row["source_file"], payload=row)
            continue
        if row["kp_id"] not in valid_kp_ids:
            _reject_row(rejected, row_kind="unit_kp_map", row_id=f'{row["unit_id"]}::{row["kp_id"]}', reason="unknown_kp_id", source_file=row["source_file"], payload=row)
            continue
        validated_unit_kp.append(row)
    unit_kp_rows = validated_unit_kp

    validated_questions = []
    for row in question_rows:
        item_id = row["item_id"]
        if row["unit_id"] not in valid_unit_ids:
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="unknown_unit_id", source_file=row["source_file"], payload=row)
            continue
        if row["primary_kp_id"] not in valid_kp_ids:
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="unknown_primary_kp_id", source_file=row["source_file"], payload=row)
            continue
        if row.get("question_intent") and row["question_intent"] not in QUESTION_INTENT_ENUM:
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="invalid_question_intent", source_file=row["source_file"], payload=row)
            continue
        if row.get("review_status") not in REVIEW_STATUS_ENUM:
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="invalid_review_status", source_file=row["source_file"], payload=row)
            continue
        if row.get("provenance") not in PROVENANCE_ENUM:
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="invalid_provenance", source_file=row["source_file"], payload=row)
            continue
        source_ref = row.get("source_ref")
        if not isinstance(source_ref, dict):
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="missing_source_ref", source_file=row["source_file"], payload=row)
            continue
        if "transcript" not in set(source_ref.get("multimodal_signals_used") or []):
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="missing_transcript_signal", source_file=row["source_file"], payload=row)
            continue
        evidence_span = source_ref.get("evidence_span")
        transcript_text = transcript_cache.get(unit_rows[[u["unit_id"] for u in unit_rows].index(row["unit_id"])]["transcript_path"] or "", "")
        if not evidence_span or _normalize_text(evidence_span) not in _normalize_text(transcript_text):
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="evidence_span_not_in_transcript", source_file=row["source_file"], payload=row)
            continue
        unit_row = next(unit for unit in unit_rows if unit["unit_id"] == row["unit_id"])
        content_ref = unit_row.get("content_ref") or {}
        start_s = content_ref.get("start_s")
        end_s = content_ref.get("end_s")
        timestamp_start = source_ref.get("timestamp_start")
        timestamp_end = source_ref.get("timestamp_end")
        if None in (timestamp_start, timestamp_end) or start_s is None or end_s is None:
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="missing_source_timestamps", source_file=row["source_file"], payload=row)
            continue
        if not (start_s <= timestamp_start <= end_s and start_s <= timestamp_end <= end_s):
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="source_timestamps_out_of_bounds", source_file=row["source_file"], payload=row)
            continue
        if row.get("qa_gate_passed") is False and len(row.get("repair_history") or []) >= 2:
            _reject_row(rejected, row_kind="question_bank", row_id=item_id, reason="qa_failed_after_repairs", source_file=row["source_file"], payload=row)
            continue
        valid_item_ids.add(item_id)
        validated_questions.append(row)
    question_rows = validated_questions

    calibration_rows = [row for row in tables["item_calibration"] if row["item_id"] in valid_item_ids]

    validated_phase_rows = []
    for row in tables["item_phase_map"]:
        if row["item_id"] not in valid_item_ids:
            continue
        if row.get("phase") not in PHASE_ENUM:
            _reject_row(rejected, row_kind="item_phase_map", row_id=f'{row["item_id"]}::{row.get("phase")}', reason="invalid_phase", source_file=row["source_file"], payload=row)
            continue
        validated_phase_rows.append(row)

    validated_kp_rows = []
    for row in tables["item_kp_map"]:
        if row["item_id"] not in valid_item_ids:
            continue
        if row.get("kp_id") not in valid_kp_ids:
            _reject_row(rejected, row_kind="item_kp_map", row_id=f'{row["item_id"]}::{row.get("kp_id")}', reason="unknown_kp_id", source_file=row["source_file"], payload=row)
            continue
        validated_kp_rows.append(row)

    validated_edges = []
    for row in prerequisite_rows:
        if row["source_kp_id"] not in valid_kp_ids or row["target_kp_id"] not in valid_kp_ids:
            _reject_row(rejected, row_kind="prerequisite_edges", row_id=f'{row["source_kp_id"]}->{row["target_kp_id"]}', reason="unknown_kp_id", source_file=row["source_file"], payload=row)
            continue
        if row.get("review_status") not in REVIEW_STATUS_ENUM:
            _reject_row(rejected, row_kind="prerequisite_edges", row_id=f'{row["source_kp_id"]}->{row["target_kp_id"]}', reason="invalid_review_status", source_file=row["source_file"], payload=row)
            continue
        if row.get("provenance") not in PROVENANCE_ENUM:
            _reject_row(rejected, row_kind="prerequisite_edges", row_id=f'{row["source_kp_id"]}->{row["target_kp_id"]}', reason="invalid_provenance", source_file=row["source_file"], payload=row)
            continue
        validated_edges.append(row)

    validated_pruned = []
    for row in pruned_rows:
        if row["source_kp_id"] not in valid_kp_ids or row["target_kp_id"] not in valid_kp_ids:
            _reject_row(rejected, row_kind="pruned_edges", row_id=f'{row["source_kp_id"]}->{row["target_kp_id"]}', reason="unknown_kp_id", source_file=row["source_file"], payload=row)
            continue
        if row.get("provenance") not in PROVENANCE_ENUM:
            _reject_row(rejected, row_kind="pruned_edges", row_id=f'{row["source_kp_id"]}->{row["target_kp_id"]}', reason="invalid_provenance", source_file=row["source_file"], payload=row)
            continue
        validated_pruned.append(row)

    overlap = {
        (row["source_kp_id"], row["target_kp_id"]) for row in validated_edges
    } & {(row["source_kp_id"], row["target_kp_id"]) for row in validated_pruned}
    for source_kp_id, target_kp_id in sorted(overlap):
        _reject_row(
            rejected,
            row_kind="prerequisite_edges",
            row_id=f"{source_kp_id}->{target_kp_id}",
            reason="edge_overlap_with_pruned",
            source_file="",
            payload={"source_kp_id": source_kp_id, "target_kp_id": target_kp_id},
        )
    if overlap:
        validated_edges = [
            row for row in validated_edges if (row["source_kp_id"], row["target_kp_id"]) not in overlap
        ]

    hard_counts = Counter(row["hard_fail_reason"] for row in rejected)
    report = {
        "summary": {
            "hard_failure_count": len(rejected),
            "hard_failure_reason_distribution": dict(hard_counts),
            "deferred_check_count": 4,
        },
        "hard_checks": {
            "blocking": True,
            "failures": rejected,
        },
        "deferred_checks": [
            {
                "check": "concept_alignment_cosine",
                "status": "deferred",
                "reason": "embedding batch is outside artifact-first scope",
            },
            {
                "check": "distractor_cosine_bounds",
                "status": "deferred",
                "reason": "embedding batch is outside artifact-first scope",
            },
            {
                "check": "edge_strength",
                "status": "deferred",
                "reason": "ModernBERT scoring is outside artifact-first scope",
            },
            {
                "check": "bidirectional_score",
                "status": "deferred",
                "reason": "ModernBERT scoring is outside artifact-first scope",
            },
        ],
    }

    cleaned = {
        "courses": tables["courses"],
        "concepts_kp": concept_rows,
        "units": unit_rows,
        "unit_kp_map": unit_kp_rows,
        "question_bank": question_rows,
        "item_calibration": calibration_rows,
        "item_phase_map": validated_phase_rows,
        "item_kp_map": validated_kp_rows,
        "prerequisite_edges": validated_edges,
        "pruned_edges": validated_pruned,
        "rejected_items": rejected,
    }
    return cleaned, rejected, report


def export_canonical_artifacts(
    *,
    output_dir: Path,
    courses_dir: Path,
    p2_path: Path,
    p5_path: Path,
    gpt54_path: Path,
    selected_courses: list[str] | None = None,
    allow_hard_fail: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    repo_root = courses_dir.parents[1]
    p2 = _load_json(p2_path)
    p5 = _load_json(p5_path)
    gpt54 = _load_json(gpt54_path)

    course_rows, lecture_index = _build_course_context(courses_dir, selected_courses)
    concepts_rows = _build_concepts_rows(p2, _relative(p2_path, repo_root))
    local_to_global = {
        row["local_kp_id"]: row["global_kp_id"]
        for row in p2.get("local_to_global_map", [])
        if row.get("local_kp_id") and row.get("global_kp_id")
    }

    unit_rows, unit_kp_rows, unit_index, rejected_from_units = _build_unit_tables(
        courses_dir=courses_dir,
        lecture_index=lecture_index,
        local_to_global=local_to_global,
    )
    transcript_cache = _load_transcript_cache(unit_rows)
    question_rows, calibration_rows, phase_rows, item_kp_rows, rejected_from_questions = _build_question_tables(
        courses_dir=courses_dir,
        unit_index=unit_index,
        transcript_cache=transcript_cache,
    )
    prerequisite_rows, pruned_rows = _build_edge_tables(
        p5=p5,
        gpt54=gpt54,
        source_file=_relative(gpt54_path, repo_root),
    )

    tables = {
        "courses": course_rows,
        "concepts_kp": concepts_rows,
        "units": unit_rows,
        "unit_kp_map": unit_kp_rows,
        "question_bank": question_rows,
        "item_calibration": calibration_rows,
        "item_phase_map": phase_rows,
        "item_kp_map": item_kp_rows,
        "prerequisite_edges": prerequisite_rows,
        "pruned_edges": pruned_rows,
        "rejected_items": rejected_from_units + rejected_from_questions,
    }

    cleaned, rejected, validation_report = validate_canonical_tables(
        tables=tables,
        transcript_cache=transcript_cache,
    )

    tmp_dir = output_dir.with_name(output_dir.name + ".tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    file_rows = {
        "courses": cleaned["courses"],
        "concepts_kp": cleaned["concepts_kp"],
        "units": cleaned["units"],
        "unit_kp_map": cleaned["unit_kp_map"],
        "question_bank": cleaned["question_bank"],
        "item_calibration": cleaned["item_calibration"],
        "item_phase_map": cleaned["item_phase_map"],
        "item_kp_map": cleaned["item_kp_map"],
        "prerequisite_edges": cleaned["prerequisite_edges"],
        "pruned_edges": cleaned["pruned_edges"],
        "rejected_items": cleaned["rejected_items"],
    }
    for name, rows in file_rows.items():
        _write_jsonl(tmp_dir / f"{name}.jsonl", rows)

    _write_json(tmp_dir / CANONICAL_VALIDATION_REPORT_FILE.name, validation_report)
    checksums = {
        path.name: _sha256_file(path)
        for path in sorted(tmp_dir.iterdir())
        if path.is_file()
    }
    manifest = {
        "bundle_id": output_dir.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_files": {
            "courses_dir": _relative(courses_dir, repo_root),
            "p2": _relative(p2_path, repo_root),
            "p5": _relative(p5_path, repo_root),
            "gpt54": _relative(gpt54_path, repo_root),
        },
        "pipeline_versions": {
            "p2_run_id": p2.get("run_id"),
            "p2_mode": p2.get("p2_mode"),
            "p5_stage_id": p5.get("stage_id"),
            "gpt54_stage_id": gpt54.get("stage_id"),
            "exporter": "artifact_first_v1",
        },
        "counts": {name: len(rows) for name, rows in file_rows.items()},
        "checksums": checksums,
        "notes": [
            "Canonical JSONL is treated as generated artifact and is not committed by default.",
            "Embedding-dependent and ML-dependent checks are deferred.",
        ],
    }
    _write_json(tmp_dir / CANONICAL_MANIFEST_FILE.name, manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    tmp_dir.replace(output_dir)

    if rejected and not allow_hard_fail:
        raise SystemExit(1)
    return manifest, validation_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=CANONICAL_ARTIFACTS_DIR)
    parser.add_argument("--courses-dir", type=Path, default=COURSES_DIR)
    parser.add_argument("--p2", type=Path, default=P2_OUTPUT_FILE)
    parser.add_argument("--p5", type=Path, default=P5_TRANSITIVE_PRUNED_FILE)
    parser.add_argument("--gpt54", type=Path, default=GPT54_EDGE_LABELS_FILE)
    parser.add_argument("--courses", nargs="*", default=None)
    parser.add_argument("--allow-hard-fail", action="store_true")
    args = parser.parse_args()

    manifest, validation_report = export_canonical_artifacts(
        output_dir=args.output_dir,
        courses_dir=args.courses_dir,
        p2_path=args.p2,
        p5_path=args.p5,
        gpt54_path=args.gpt54,
        selected_courses=args.courses,
        allow_hard_fail=args.allow_hard_fail,
    )
    print(json.dumps(manifest["counts"], indent=2))
    print(json.dumps(validation_report["summary"], indent=2))


if __name__ == "__main__":
    main()
