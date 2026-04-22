"""Build Prompt 3 input artifacts from complete P1/P2 outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.p3_input_sanitizer import sanitize_p3a_payload


_LOCAL_ID_PATTERN = re.compile(r"^local::([^:]+)::")
_YOUTUBE_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})")
_TIMESTAMP_LINE_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})$")


@dataclass(frozen=True)
class TranscriptEntry:
    second: int
    text: str


@dataclass(frozen=True)
class TranscriptDocument:
    path: Path
    youtube_url: str | None
    video_id: str | None
    entries: list[TranscriptEntry]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_local_token(raw_id: str | None) -> str | None:
    if not raw_id:
        return None
    match = _LOCAL_ID_PATTERN.match(raw_id)
    if not match:
        return None
    return match.group(1)


def _normalize_youtube_url(raw_url: str | None) -> str | None:
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    match = _YOUTUBE_ID_PATTERN.search(raw_url)
    if not match:
        return raw_url.strip()
    return f"https://www.youtube.com/watch?v={match.group(1)}"


def _extract_youtube_id(raw_url: str | None) -> str | None:
    normalized = _normalize_youtube_url(raw_url)
    if normalized is None:
        return None
    match = _YOUTUBE_ID_PATTERN.search(normalized)
    if not match:
        return None
    return match.group(1)


def _parse_transcript(path: Path) -> TranscriptDocument:
    youtube_url: str | None = None
    video_id: str | None = None
    entries: list[TranscriptEntry] = []

    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("URL:"):
            youtube_url = _normalize_youtube_url(line.partition(":")[2].strip())
        elif line.startswith("Video ID:"):
            value = line.partition(":")[2].strip()
            video_id = value or None
        else:
            match = _TIMESTAMP_LINE_PATTERN.match(line)
            if match:
                second = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
                text_lines: list[str] = []
                index += 1
                while index < len(lines):
                    candidate = lines[index].strip()
                    if not candidate:
                        index += 1
                        break
                    if _TIMESTAMP_LINE_PATTERN.match(candidate):
                        index -= 1
                        break
                    text_lines.append(candidate)
                    index += 1
                entries.append(TranscriptEntry(second=second, text=" ".join(text_lines).strip()))
        index += 1

    if youtube_url is not None and video_id is None:
        video_id = _extract_youtube_id(youtube_url)

    return TranscriptDocument(
        path=path,
        youtube_url=youtube_url,
        video_id=video_id,
        entries=entries,
    )


def _build_transcript_index(course_dir: Path) -> dict[str, TranscriptDocument]:
    transcript_dir = course_dir / "transcripts"
    index: dict[str, TranscriptDocument] = {}
    if not transcript_dir.exists():
        return index

    for path in sorted(transcript_dir.glob("*_transcript.txt")):
        document = _parse_transcript(path)
        if document.video_id:
            index[document.video_id] = document
    return index


def _format_seconds(second: int) -> str:
    hours = second // 3600
    minutes = (second % 3600) // 60
    seconds = second % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _extract_transcript_slice(document: TranscriptDocument | None, *, start_s: int, end_s: int) -> str:
    if document is None:
        return ""
    lines = [
        f"{_format_seconds(entry.second)}\n{entry.text}"
        for entry in document.entries
        if start_s <= entry.second <= end_s and entry.text
    ]
    return "\n\n".join(lines)


def _slugify_filename(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", raw.casefold()).strip("-")


def _derive_lecture_id(artifact: dict[str, Any], source_file: Path) -> str:
    lecture_id = artifact.get("lecture_id")
    if isinstance(lecture_id, str) and lecture_id.strip():
        return lecture_id.strip()

    units = artifact.get("units")
    if isinstance(units, list) and units:
        token = _extract_local_token(units[0].get("unit_id")) if isinstance(units[0], dict) else None
        if token:
            return token

    return source_file.stem.removesuffix("_p1")


def _build_local_to_global_map(p2_output: dict[str, Any]) -> dict[str, str]:
    return {
        row["local_kp_id"]: row["global_kp_id"]
        for row in p2_output.get("local_to_global_map", [])
        if isinstance(row, dict) and "local_kp_id" in row and "global_kp_id" in row
    }


def _build_global_kp_index(p2_output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["global_kp_id"]: row
        for row in p2_output.get("concepts_kp_global", [])
        if isinstance(row, dict) and "global_kp_id" in row
    }


def _globalize_unit_kp_map(
    unit_kp_map_local: list[dict[str, Any]],
    *,
    local_to_global: dict[str, str],
) -> list[dict[str, Any]]:
    global_rows: list[dict[str, Any]] = []
    for row in unit_kp_map_local:
        local_kp_id = row.get("local_kp_id")
        global_kp_id = local_to_global.get(local_kp_id)
        if not global_kp_id:
            continue
        global_rows.append(
            {
                "unit_id": row.get("unit_id"),
                "global_kp_id": global_kp_id,
                "planner_role": row.get("planner_role"),
                "coverage_level": row.get("coverage_level"),
            }
        )
    return global_rows


def _relevant_kp_catalog(
    unit_kp_map_global: list[dict[str, Any]],
    *,
    global_kp_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered_ids: list[str] = []
    for row in unit_kp_map_global:
        global_kp_id = row.get("global_kp_id")
        if isinstance(global_kp_id, str) and global_kp_id not in ordered_ids:
            ordered_ids.append(global_kp_id)
    return [global_kp_index[global_kp_id] for global_kp_id in ordered_ids if global_kp_id in global_kp_index]


def _difficulty_window(value: Any) -> list[float] | None:
    if not isinstance(value, int | float):
        return None
    score = float(value)
    lower = round(max(0.0, score - 0.15), 2)
    upper = round(min(1.0, score + 0.15), 2)
    return [lower, upper]


def _load_learning_salience_index(course_dir: Path, source_file: Path) -> dict[str, dict[str, Any]]:
    processed_p3_path = course_dir / "processed" / "P3" / f"{source_file.stem.removesuffix('_p1')}.json"
    if not processed_p3_path.exists():
        return {}

    artifact = _load_json(processed_p3_path)
    rows = artifact.get("learning_salience", [])
    if not isinstance(rows, list):
        return {}

    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        unit_id = row.get("unit_id")
        if isinstance(unit_id, str) and unit_id.strip():
            index[unit_id] = row
    return index


def _looks_code_oriented(unit: dict[str, Any], transcript_slice: str) -> bool:
    haystacks = [
        unit.get("name"),
        unit.get("description"),
        unit.get("summary"),
        transcript_slice,
    ]
    keywords = (
        "code",
        "python",
        "pytorch",
        "tensor",
        "implementation",
        "function",
        "class ",
        "def ",
        "import ",
        "torch.",
    )
    for raw in haystacks:
        if not isinstance(raw, str):
            continue
        lowered = raw.casefold()
        if any(keyword in lowered for keyword in keywords):
            return True
    return False


def build_p3_inputs(
    *,
    course_dirs: list[Path],
    p2_output_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    p2_output = _load_json(p2_output_path)
    local_to_global = _build_local_to_global_map(p2_output)
    global_kp_index = _build_global_kp_index(p2_output)

    lecture_count = 0
    p3a_count = 0
    p3b_count = 0
    p3c_count = 0

    for course_dir in course_dirs:
        transcript_index = _build_transcript_index(course_dir)
        processed_dir = course_dir / "processed_sanitized"
        if not processed_dir.exists():
            continue

        for source_file in sorted(processed_dir.glob("*_p1.json")):
            artifact = _load_json(source_file)
            units = [row for row in artifact.get("units", []) if isinstance(row, dict)]
            if not units:
                continue

            lecture_count += 1
            lecture_id = _derive_lecture_id(artifact, source_file)
            youtube_url = _normalize_youtube_url(units[0].get("content_ref", {}).get("video_url"))
            transcript_doc = transcript_index.get(_extract_youtube_id(youtube_url))

            unit_kp_map_local = [
                row for row in artifact.get("unit_kp_map_local", []) if isinstance(row, dict)
            ]
            unit_kp_map_global = _globalize_unit_kp_map(unit_kp_map_local, local_to_global=local_to_global)
            kp_catalog = _relevant_kp_catalog(unit_kp_map_global, global_kp_index=global_kp_index)
            learning_salience_index = _load_learning_salience_index(course_dir, source_file)

            lecture_context = {
                "course_id": course_dir.name,
                "lecture_id": lecture_id,
                "lecture_title": artifact.get("lecture_title"),
                "youtube_url": youtube_url,
            }
            source_trace = {
                "p1_artifact": str(source_file),
                "p2_output": str(p2_output_path),
                "transcript_file": str(transcript_doc.path) if transcript_doc else None,
            }

            p3a_payload = {
                "lecture_context": lecture_context,
                "table_of_contents": artifact.get("table_of_contents", []),
                "units": units,
                "section_flags": artifact.get("section_flags", []),
                "unit_kp_map": unit_kp_map_global,
                "kp_catalog": kp_catalog,
                "course_config": {
                    "included_content_types": [
                        "core_theory",
                        "worked_example",
                        "application_case",
                        "motivation",
                    ]
                },
                "source_trace": source_trace,
            }
            p3a_payload, _ = sanitize_p3a_payload(p3a_payload, file_path=output_dir / "p3a" / course_dir.name / source_file.name)
            _dump_json(output_dir / "p3a" / course_dir.name / source_file.name, p3a_payload)
            p3a_count += 1

            p3b_payload = {
                "lecture_context": lecture_context,
                "units": units,
                "learning_salience": None,
                "buffer_s": 3,
                "storage_bucket": "ingestion-clips",
                "storage_path_template": "clips/<course_id>/<lecture_id>/<unit_id>.mp4",
                "source_trace": source_trace,
            }
            _dump_json(output_dir / "p3b" / course_dir.name / source_file.name, p3b_payload)
            p3b_count += 1

            unit_map_by_id: dict[str, list[dict[str, Any]]] = {}
            for row in unit_kp_map_global:
                unit_id = row.get("unit_id")
                if isinstance(unit_id, str):
                    unit_map_by_id.setdefault(unit_id, []).append(row)

            for unit in units:
                unit_id = unit.get("unit_id")
                if not isinstance(unit_id, str):
                    continue
                unit_rows = unit_map_by_id.get(unit_id, [])
                unit_catalog = _relevant_kp_catalog(unit_rows, global_kp_index=global_kp_index)
                content_ref = unit.get("content_ref", {})
                transcript_slice = _extract_transcript_slice(
                    transcript_doc,
                    start_s=int(content_ref.get("start_s", 0)),
                    end_s=int(content_ref.get("end_s", 0)),
                )
                salience_row = learning_salience_index.get(unit_id, {})
                allow_code_mcq = _looks_code_oriented(unit, transcript_slice)
                target_kp_ids = salience_row.get("target_kp_ids")
                if not isinstance(target_kp_ids, list):
                    target_kp_ids = []

                p3c_payload = {
                    "lecture_context": lecture_context,
                    "unit": unit,
                    "unit_summary_for_generation": unit.get("summary"),
                    "target_kp_ids": target_kp_ids,
                    "assessment_purpose": "lecture_reinforcement",
                    "youtube_url": youtube_url,
                    "video_clip_url": youtube_url,
                    "transcript_slice": transcript_slice,
                    "unit_kp_map_rows": unit_rows,
                    "kp_catalog": unit_catalog,
                    "question_intent": salience_row.get("question_intent"),
                    "target_item_count": salience_row.get("expected_item_count"),
                    "target_difficulty_range": _difficulty_window(unit.get("difficulty")),
                    "allow_code_mcq": allow_code_mcq,
                    "allowed_item_types": ["concept_mcq", "code_mcq"] if allow_code_mcq else ["concept_mcq"],
                    "forbidden_question_patterns": [],
                    "code_evidence": [],
                    "source_trace": source_trace,
                }
                unit_filename = _slugify_filename(unit_id).replace("local-", "local--")
                _dump_json(output_dir / "p3c" / course_dir.name / source_file.stem / f"{unit_filename}.json", p3c_payload)
                p3c_count += 1

    return {
        "summary": {
            "lectures": lecture_count,
            "p3a_files": p3a_count,
            "p3b_files": p3b_count,
            "p3c_files": p3c_count,
        }
    }


def main(*, course_dirs: list[Path], p2_output_path: Path, output_dir: Path) -> None:
    report = build_p3_inputs(course_dirs=course_dirs, p2_output_path=p2_output_path, output_dir=output_dir)
    print(json.dumps(report["summary"], ensure_ascii=False))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Prompt 3 input artifacts from P1/P2 outputs.")
    parser.add_argument("--course-dir", action="append", required=True, dest="course_dirs")
    parser.add_argument("--p2-output", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    main(
        course_dirs=[Path(raw) for raw in args.course_dirs],
        p2_output_path=Path(args.p2_output),
        output_dir=Path(args.output_dir),
    )
