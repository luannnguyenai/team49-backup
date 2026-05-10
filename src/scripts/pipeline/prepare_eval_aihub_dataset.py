"""Prepare an open-QA eval dataset from canonical DB rows.

The output intentionally hides MCQ choices from model input. References keep the
existing DB answer and explanation for later judge/evaluator use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.database import async_session


DEFAULT_OUTPUT_DIR = Path(
    "data/final_artifacts/cs224n_cs231n_cs230_v1/eval_aihub_dataset"
)


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp_to_seconds(value: str) -> int | None:
    text_value = value.strip()
    if not text_value:
        return None
    parts = text_value.split(":")
    if len(parts) not in {2, 3}:
        return None
    if not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _seconds_to_timestamp(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining:02d}"


def _parse_transcript_segments(transcript_text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current_timestamp: int | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        if current_timestamp is None:
            current_lines = []
            return
        segment_text = "\n".join(line for line in current_lines if line.strip()).strip()
        if segment_text:
            segments.append({"timestamp_s": current_timestamp, "text": segment_text})
        current_lines = []

    for raw_line in transcript_text.splitlines():
        line = raw_line.strip()
        timestamp = _parse_timestamp_to_seconds(line)
        if timestamp is not None:
            flush()
            current_timestamp = timestamp
            continue
        if current_timestamp is not None:
            current_lines.append(raw_line.rstrip())
    flush()
    return segments


def compute_window_bounds(
    source_ref: dict[str, Any],
    content_ref: dict[str, Any] | None,
    *,
    margin_s: int,
) -> tuple[int, int]:
    timestamp_start = _as_int(source_ref.get("timestamp_start"))
    timestamp_end = _as_int(source_ref.get("timestamp_end"))
    if timestamp_start is None or timestamp_end is None:
        raise ValueError("source_ref must include timestamp_start and timestamp_end")

    raw_start = max(0, timestamp_start - margin_s)
    raw_end = max(timestamp_end, timestamp_end + margin_s)
    content_ref = content_ref or {}
    unit_start = _as_int(content_ref.get("start_s"))
    unit_end = _as_int(content_ref.get("end_s"))
    if unit_start is not None:
        raw_start = max(unit_start, raw_start)
    if unit_end is not None:
        raw_end = min(unit_end, raw_end)
    return raw_start, raw_end


def extract_transcript_window(
    transcript_text: str,
    *,
    start_s: int,
    end_s: int,
) -> dict[str, Any]:
    selected = [
        segment
        for segment in _parse_transcript_segments(transcript_text)
        if start_s <= int(segment["timestamp_s"]) <= end_s
    ]
    lines: list[str] = []
    for segment in selected:
        lines.append(_seconds_to_timestamp(int(segment["timestamp_s"])))
        lines.append(str(segment["text"]))
        lines.append("")
    return {"start_s": start_s, "end_s": end_s, "text": "\n".join(lines).strip()}


def classify_eval_tier(question: dict[str, Any]) -> str:
    if question.get("item_type") == "code_mcq":
        return "C_exclude_or_enrich_code"
    if question.get("grounding_mode") == "transcript_and_video_clip":
        return "C_exclude_or_enrich_multimodal"
    if (
        question.get("item_type") == "concept_mcq"
        and question.get("grounding_mode") == "transcript_only"
        and question.get("grounding_confidence") == "high"
    ):
        return "A_text_grounded_high_confidence"
    return "B_text_grounded_needs_review"


def build_eval_sample(
    *,
    question: dict[str, Any],
    unit: dict[str, Any],
    kp: dict[str, Any] | None,
    transcript_window: dict[str, Any],
    eval_tier: str,
) -> dict[str, Any]:
    choices = list(question.get("choices") or [])
    answer_index = int(question["answer_index"])
    answer_text = choices[answer_index]
    source_ref = dict(question.get("source_ref") or {})

    return {
        "eval_id": question["item_id"],
        "split": "test",
        "eval_tier": eval_tier,
        "metadata": {
            "course_id": question.get("course_id"),
            "lecture_id": question.get("lecture_id"),
            "lecture_title": unit.get("lecture_title"),
            "lecture_order": unit.get("lecture_order"),
            "unit_id": question.get("unit_id"),
            "unit_name": unit.get("unit_name"),
            "item_type": question.get("item_type"),
            "difficulty": question.get("difficulty"),
            "question_intent": question.get("question_intent"),
            "knowledge_scope": question.get("knowledge_scope"),
            "assessment_purpose": question.get("assessment_purpose"),
            "grounding_mode": question.get("grounding_mode"),
            "grounding_confidence": question.get("grounding_confidence"),
            "primary_kp_id": question.get("primary_kp_id"),
            "content_type": unit.get("content_type"),
            "salience_score": unit.get("salience_score"),
        },
        "input": {
            "context": {
                "unit_description": unit.get("description"),
                "unit_summary": unit.get("summary"),
                "unit_key_points": unit.get("key_points") or [],
                "kp": {
                    "kp_id": (kp or {}).get("kp_id"),
                    "name": (kp or {}).get("name"),
                    "description": (kp or {}).get("description"),
                    "importance_level": (kp or {}).get("importance_level"),
                    "structural_role": (kp or {}).get("structural_role"),
                }
                if kp
                else None,
                "source_evidence_span": source_ref.get("evidence_span"),
                "transcript_window": transcript_window,
            },
            "question": question.get("question"),
        },
        "reference": {
            "answer_text": answer_text,
            "explanation": question.get("explanation"),
            "source_ref": source_ref,
            "answer_source": "choices[answer_index]",
        },
    }


def _row_to_records(row: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    mapping = row._mapping
    question = {
        "item_id": mapping["item_id"],
        "course_id": mapping["course_id"],
        "lecture_id": mapping["lecture_id"],
        "unit_id": mapping["unit_id"],
        "primary_kp_id": mapping["primary_kp_id"],
        "item_type": mapping["item_type"],
        "question": mapping["question"],
        "choices": mapping["choices"],
        "answer_index": mapping["answer_index"],
        "explanation": mapping["explanation"],
        "difficulty": mapping["item_difficulty"],
        "question_intent": mapping["question_intent"],
        "knowledge_scope": mapping["knowledge_scope"],
        "assessment_purpose": mapping["assessment_purpose"],
        "grounding_mode": mapping["grounding_mode"],
        "grounding_confidence": mapping["grounding_confidence"],
        "source_ref": mapping["source_ref"],
    }
    unit = {
        "unit_id": mapping["unit_id"],
        "lecture_title": mapping["lecture_title"],
        "lecture_order": mapping["lecture_order"],
        "unit_name": mapping["unit_name"],
        "description": mapping["unit_description"],
        "summary": mapping["summary"],
        "key_points": mapping["key_points"],
        "content_ref": mapping["content_ref"],
        "transcript_path": mapping["transcript_path"],
        "content_type": mapping["content_type"],
        "salience_score": mapping["salience_score"],
    }
    kp = None
    if mapping["kp_id"]:
        kp = {
            "kp_id": mapping["kp_id"],
            "name": mapping["kp_name"],
            "description": mapping["kp_description"],
            "importance_level": mapping["importance_level"],
            "structural_role": mapping["structural_role"],
        }
    return question, unit, kp


async def _fetch_rows(limit: int | None = None) -> list[Any]:
    limit_clause = "LIMIT :limit" if limit is not None else ""
    query = text(
        f"""
        SELECT
            qb.item_id,
            qb.course_id,
            qb.lecture_id,
            qb.unit_id,
            qb.primary_kp_id,
            qb.item_type,
            qb.question,
            qb.choices,
            qb.answer_index,
            qb.explanation,
            qb.difficulty AS item_difficulty,
            qb.question_intent,
            qb.knowledge_scope,
            qb.assessment_purpose,
            qb.grounding_mode,
            qb.grounding_confidence,
            qb.source_ref,
            u.lecture_title,
            u.lecture_order,
            u.unit_name,
            u.description AS unit_description,
            u.summary,
            u.key_points,
            u.content_ref,
            u.transcript_path,
            u.content_type,
            u.salience_score,
            ck.kp_id,
            ck.name AS kp_name,
            ck.description AS kp_description,
            ck.importance_level,
            ck.structural_role
        FROM question_bank qb
        JOIN units u ON u.unit_id = qb.unit_id
        LEFT JOIN concepts_kp ck ON ck.kp_id = qb.primary_kp_id
        WHERE qb.qa_gate_passed IS TRUE
          AND qb.answer_index IS NOT NULL
          AND qb.choices IS NOT NULL
          AND qb.source_ref IS NOT NULL
          AND qb.source_ref->>'timestamp_start' IS NOT NULL
          AND qb.source_ref->>'timestamp_end' IS NOT NULL
        ORDER BY qb.course_id, qb.lecture_id, qb.unit_id, qb.item_id
        {limit_clause}
        """
    )
    params = {"limit": limit} if limit is not None else {}
    async with async_session() as session:
        result = await session.execute(query, params)
        return list(result.fetchall())


def _read_transcript(repo_root: Path, transcript_path: str | None) -> str:
    if not transcript_path:
        return ""
    path = Path(transcript_path)
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


async def build_dataset(
    *,
    output_dir: Path,
    repo_root: Path,
    margin_s: int,
    limit: int | None,
) -> dict[str, Any]:
    rows = await _fetch_rows(limit=limit)
    samples: list[dict[str, Any]] = []
    transcript_cache: dict[str, str] = {}
    missing_transcripts: list[str] = []

    for row in rows:
        question, unit, kp = _row_to_records(row)
        start_s, end_s = compute_window_bounds(
            question["source_ref"],
            unit.get("content_ref"),
            margin_s=margin_s,
        )
        transcript_path = unit.get("transcript_path")
        if transcript_path not in transcript_cache:
            transcript_cache[transcript_path] = _read_transcript(repo_root, transcript_path)
        transcript_text = transcript_cache[transcript_path]
        if not transcript_text and transcript_path:
            missing_transcripts.append(transcript_path)
        transcript_window = extract_transcript_window(
            transcript_text,
            start_s=start_s,
            end_s=end_s,
        )
        samples.append(
            build_eval_sample(
                question=question,
                unit=unit,
                kp=kp,
                transcript_window=transcript_window,
                eval_tier=classify_eval_tier(question),
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "open_qa_eval.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")

    tier_counts = Counter(sample["eval_tier"] for sample in samples)
    course_counts = Counter(sample["metadata"]["course_id"] for sample in samples)
    manifest = {
        "dataset_name": "eval_aihub_dataset",
        "format": "jsonl",
        "source": "database question_bank joined with units and concepts_kp",
        "output_file": str(dataset_path),
        "sample_count": len(samples),
        "margin_s": margin_s,
        "counts_by_tier": dict(sorted(tier_counts.items())),
        "counts_by_course": dict(sorted(course_counts.items())),
        "missing_transcript_count": len(set(missing_transcripts)),
        "missing_transcripts": sorted(set(missing_transcripts)),
        "input_excludes": ["choices", "answer_index", "explanation"],
        "reference_answer_source": "choices[answer_index]",
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--margin-s", type=int, default=90)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


async def _main_async() -> None:
    args = _parse_args()
    manifest = await build_dataset(
        output_dir=args.output_dir,
        repo_root=args.repo_root,
        margin_s=args.margin_s,
        limit=args.limit,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
