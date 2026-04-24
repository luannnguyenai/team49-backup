from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


_PLACEHOLDER_PATTERN = re.compile(r"<[^>]+>")
_LOCAL_ID_PATTERN = re.compile(r"^local::([^:]+)::")
_YOUTUBE_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})")


def _is_missing_or_placeholder(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip() or _PLACEHOLDER_PATTERN.search(value) is not None


def _normalize_youtube_url(raw_url: Any) -> str | None:
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    match = _YOUTUBE_ID_PATTERN.search(raw_url)
    if not match:
        return raw_url.strip()
    return f"https://www.youtube.com/watch?v={match.group(1)}"


def _extract_local_token(raw_id: Any) -> str | None:
    if not isinstance(raw_id, str):
        return None
    match = _LOCAL_ID_PATTERN.match(raw_id)
    if not match:
        return None
    token = match.group(1)
    if _is_missing_or_placeholder(token):
        return None
    return token


def _infer_course_id(payload: dict[str, Any], file_path: Path) -> str:
    lecture_context = payload.get("lecture_context")
    if isinstance(lecture_context, dict):
        candidate = lecture_context.get("course_id")
        if isinstance(candidate, str) and not _is_missing_or_placeholder(candidate):
            return candidate

    source_trace = payload.get("source_trace")
    if isinstance(source_trace, dict):
        for key in ("transcript_file", "p1_artifact"):
            raw_path = source_trace.get(key)
            if isinstance(raw_path, str):
                path = Path(raw_path)
                parts = path.parts
                if "data" in parts:
                    data_index = parts.index("data")
                    if data_index + 1 < len(parts):
                        candidate = parts[data_index + 1]
                        if candidate and not _is_missing_or_placeholder(candidate):
                            return candidate

    return file_path.parent.name


def _infer_lecture_id(payload: dict[str, Any], file_path: Path) -> str:
    lecture_context = payload.get("lecture_context")
    if isinstance(lecture_context, dict):
        candidate = lecture_context.get("lecture_id")
        if isinstance(candidate, str) and not _is_missing_or_placeholder(candidate):
            return candidate

    source_trace = payload.get("source_trace")
    if isinstance(source_trace, dict):
        transcript_file = source_trace.get("transcript_file")
        if isinstance(transcript_file, str) and transcript_file.strip():
            return Path(transcript_file).stem.removesuffix("_transcript")

    units = payload.get("units")
    if isinstance(units, list) and units:
        token = _extract_local_token(units[0].get("unit_id")) if isinstance(units[0], dict) else None
        if token:
            return token

    if isinstance(source_trace, dict):
        p1_artifact = source_trace.get("p1_artifact")
        if isinstance(p1_artifact, str) and p1_artifact.strip():
            return Path(p1_artifact).stem.removesuffix("_p1")

    return file_path.stem


def _repair_unit_id(raw_unit_id: Any, *, lecture_id: str) -> Any:
    if not isinstance(raw_unit_id, str):
        return raw_unit_id
    return raw_unit_id.replace("<lecture_id>", lecture_id)


def sanitize_p3a_payload(payload: dict[str, Any], *, file_path: Path) -> tuple[dict[str, Any], list[str]]:
    sanitized = deepcopy(payload)
    changes: list[str] = []

    course_id = _infer_course_id(sanitized, file_path)
    lecture_id = _infer_lecture_id(sanitized, file_path)

    lecture_context = sanitized.setdefault("lecture_context", {})
    if lecture_context.get("course_id") != course_id:
        lecture_context["course_id"] = course_id
        changes.append("lecture_context.course_id")
    if lecture_context.get("lecture_id") != lecture_id:
        lecture_context["lecture_id"] = lecture_id
        changes.append("lecture_context.lecture_id")

    normalized_lecture_url = _normalize_youtube_url(lecture_context.get("youtube_url"))
    if normalized_lecture_url is not None and lecture_context.get("youtube_url") != normalized_lecture_url:
        lecture_context["youtube_url"] = normalized_lecture_url
        changes.append("lecture_context.youtube_url")

    units = sanitized.get("units")
    if isinstance(units, list):
        for index, unit in enumerate(units):
            if not isinstance(unit, dict):
                continue
            repaired_unit_id = _repair_unit_id(unit.get("unit_id"), lecture_id=lecture_id)
            if unit.get("unit_id") != repaired_unit_id:
                unit["unit_id"] = repaired_unit_id
                changes.append(f"units[{index}].unit_id")

            if _is_missing_or_placeholder(unit.get("course_id")):
                unit["course_id"] = course_id
                changes.append(f"units[{index}].course_id")

            content_ref = unit.get("content_ref")
            if isinstance(content_ref, dict):
                normalized_video_url = _normalize_youtube_url(content_ref.get("video_url"))
                if normalized_video_url is not None and content_ref.get("video_url") != normalized_video_url:
                    content_ref["video_url"] = normalized_video_url
                    changes.append(f"units[{index}].content_ref.video_url")

    section_flags = sanitized.get("section_flags")
    if isinstance(section_flags, list):
        for index, row in enumerate(section_flags):
            if not isinstance(row, dict):
                continue
            repaired_unit_id = _repair_unit_id(row.get("unit_id"), lecture_id=lecture_id)
            if row.get("unit_id") != repaired_unit_id:
                row["unit_id"] = repaired_unit_id
                changes.append(f"section_flags[{index}].unit_id")

    unit_kp_map = sanitized.get("unit_kp_map")
    if isinstance(unit_kp_map, list):
        for index, row in enumerate(unit_kp_map):
            if not isinstance(row, dict):
                continue
            repaired_unit_id = _repair_unit_id(row.get("unit_id"), lecture_id=lecture_id)
            if row.get("unit_id") != repaired_unit_id:
                row["unit_id"] = repaired_unit_id
                changes.append(f"unit_kp_map[{index}].unit_id")

    return sanitized, changes


def sanitize_p3a_artifacts(*, input_dir: Path, output_dir: Path) -> dict[str, Any]:
    processed_files = 0
    sanitized_files = 0
    files_report: list[dict[str, Any]] = []

    for input_path in sorted(input_dir.rglob("*.json")):
        processed_files += 1
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        sanitized, changes = sanitize_p3a_payload(payload, file_path=input_path)

        output_path = output_dir / input_path.relative_to(input_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if changes:
            sanitized_files += 1
        files_report.append(
            {
                "input_path": str(input_path),
                "output_path": str(output_path),
                "changes": changes,
            }
        )

    return {
        "summary": {
            "processed_files": processed_files,
            "sanitized_files": sanitized_files,
        },
        "files": files_report,
    }
