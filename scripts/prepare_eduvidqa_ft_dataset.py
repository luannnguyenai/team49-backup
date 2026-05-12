#!/usr/bin/env python3
"""Build a VLM fine-tuning dataset from EduVidQA raw videos and transcripts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

YOUTUBE_ID_RE = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")
TIMESTAMP_TEXT_RE = re.compile(r"(?<!\d)(\d{1,2}:\d{1,2}(?::\d{1,2})?)(?!\d)")


@dataclass(frozen=True)
class QARow:
    row_id: str
    split: str
    video_id: str
    video_url: str
    title: str
    timestamp: str
    timestamp_seconds: float
    timestamp_source: str
    original_timestamp: str
    question: str
    answer: str
    source: str


def parse_timestamp_seconds(value: str) -> float:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("empty timestamp")
    parts = raw.split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"unsupported timestamp: {value!r}")
    try:
        numbers = [float(part.strip()) for part in parts]
    except ValueError as exc:
        raise ValueError(f"unsupported timestamp: {value!r}") from exc
    if len(numbers) == 1:
        return numbers[0]
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def parse_eduvidqa_timestamp_seconds(value: str, split: str) -> float:
    raw = str(value or "").strip()
    parts = raw.split(":")
    if split == "synthetic_train" and len(parts) == 3:
        try:
            minutes = float(parts[0].strip())
            seconds = float(parts[1].strip())
            fractional = float(parts[2].strip() or 0)
        except ValueError as exc:
            raise ValueError(f"unsupported timestamp: {value!r}") from exc
        return minutes * 60 + seconds + fractional / 100.0
    return parse_timestamp_seconds(raw)


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def extract_video_id(row: dict[str, str]) -> str | None:
    for key in ("vid_id", "video_id", "id"):
        value = (row.get(key) or "").strip()
        if YOUTUBE_ID_RE.fullmatch(value):
            return value
    text = " ".join(str(value or "") for value in row.values())
    match = YOUTUBE_ID_RE.search(text)
    return match.group(1) if match else None


def split_name_from_path(path: Path) -> str:
    return path.stem


def extract_answer_timestamp(answer: str) -> str | None:
    matches = TIMESTAMP_TEXT_RE.findall(answer or "")
    unique_matches = []
    seen = set()
    for match in matches:
        if match not in seen:
            seen.add(match)
            unique_matches.append(match)
    if len(unique_matches) == 1:
        return unique_matches[0]
    return None


def row_question(row: dict[str, str], *, timestamp: str) -> str:
    question = (row.get("final_question") or row.get("question") or "").strip()
    if timestamp:
        question = question.replace("<timestamp>", timestamp)
    return " ".join(question.split())


def row_answer(row: dict[str, str]) -> str:
    return " ".join((row.get("final_answer") or row.get("answer") or "").strip().split())


def load_qa_rows(paths: list[Path], *, recover_answer_timestamps: bool = False) -> list[QARow]:
    rows: list[QARow] = []
    for path in paths:
        split = split_name_from_path(path)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for line_number, row in enumerate(reader, start=2):
                video_id = extract_video_id(row)
                original_timestamp = (row.get("timestamp") or "").strip()
                answer = row_answer(row)
                timestamp = original_timestamp
                timestamp_source = "csv"
                if not timestamp and recover_answer_timestamps:
                    recovered_timestamp = extract_answer_timestamp(answer)
                    if recovered_timestamp:
                        timestamp = recovered_timestamp
                        timestamp_source = "answer_text_recovered"
                question = row_question(row, timestamp=timestamp)
                if not video_id or not timestamp or not question or not answer:
                    continue
                timestamp_seconds = parse_eduvidqa_timestamp_seconds(timestamp, split)
                rows.append(
                    QARow(
                        row_id=f"{split}_{line_number - 1:06d}",
                        split=split,
                        video_id=video_id,
                        video_url=(
                            row.get("vid_url")
                            or row.get("video_url")
                            or row.get("url")
                            or f"https://youtube.com/watch?v={video_id}"
                        ),
                        title=(row.get("vid_title") or row.get("title") or "").strip(),
                        timestamp=timestamp,
                        timestamp_seconds=timestamp_seconds,
                        timestamp_source=timestamp_source,
                        original_timestamp=original_timestamp,
                        question=question,
                        answer=answer,
                        source=f"{path}:{line_number}",
                    )
                )
    return rows


def load_transcript(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Transcript must be a list: {path}")
    return data


def build_transcript_context(
    transcript_rows: list[dict[str, Any]],
    *,
    center_seconds: float,
    window_seconds: float,
) -> str:
    start = max(0.0, center_seconds - window_seconds)
    end = center_seconds + window_seconds
    lines: list[str] = []
    for row in transcript_rows:
        try:
            row_start = float(row["start"])
            duration = float(row.get("duration") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        row_end = row_start + max(0.0, duration)
        if row_start > end or row_end < start:
            continue
        text = " ".join(str(row.get("text") or "").split())
        if text:
            lines.append(f"[{format_timestamp(row_start)}] {text}")
    return "\n".join(lines)


def safe_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def frame_relative_path(row: QARow, sample_index: int) -> Path:
    seconds = int(row.timestamp_seconds)
    return Path("frames") / row.split / f"{row.video_id}_{seconds:06d}_{sample_index:06d}.jpg"


def find_video_path(raw_root: Path, video_id: str) -> Path | None:
    videos_dir = raw_root / "videos"
    candidates = sorted(videos_dir.glob(f"{video_id}.*"))
    for path in candidates:
        if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}:
            return path
    return None


def extract_frame(
    *,
    video_path: Path,
    image_path: Path,
    timestamp_seconds: float,
    ffmpeg_bin: str,
    overwrite: bool,
) -> bool:
    if image_path.exists() and not overwrite:
        return False
    image_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp_seconds:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        "-y",
        str(image_path),
    ]
    subprocess.run(command, check=True)
    return True


def build_text_input(*, transcript_context: str, question: str) -> str:
    return (
        "Transcript window (-120s to +120s around the frame timestamp):\n"
        f"{transcript_context}\n\n"
        "Student question:\n"
        f"{question}"
    )


def word_count(text: str) -> int:
    return len(str(text or "").split())


def classify_quality_flags(answer: str, *, question: str) -> list[str]:
    del question
    lowered = str(answer or "").lower()
    flags: list[str] = []
    rewrite_markers = (
        "to improve the clarity",
        "improve the clarity of",
        "i will rephrase",
        "we can rephrase",
        "here is a modified version",
        "let's break it down into smaller parts",
        "to simplify and clarify",
    )
    if any(marker in lowered for marker in rewrite_markers):
        flags.append("synthetic_rewrite_style")
    if word_count(answer) <= 15:
        flags.append("short_answer")
    return flags


def build_dataset_record(
    *,
    row: QARow,
    image_path: Path,
    transcript_context: str,
    output_root: Path,
    quality_flags: list[str] | None = None,
) -> dict[str, Any]:
    image = image_path.as_posix()
    if image_path.is_absolute():
        image = image_path.relative_to(output_root).as_posix()
    text_input = build_text_input(
        transcript_context=transcript_context,
        question=row.question,
    )
    return {
        "id": row.row_id,
        "split": row.split,
        "video_id": row.video_id,
        "video_url": row.video_url,
        "title": row.title,
        "timestamp": row.timestamp,
        "timestamp_seconds": row.timestamp_seconds,
        "timestamp_source": row.timestamp_source,
        "original_timestamp": row.original_timestamp,
        "image": image,
        "text_input": text_input,
        "answer": row.answer,
        "quality_flags": quality_flags or [],
        "source": row.source,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": text_input},
                ],
            },
            {"role": "assistant", "content": row.answer},
        ],
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare EduVidQA VLM fine-tuning JSONL with timestamp frames."
    )
    parser.add_argument(
        "--input",
        nargs="+",
        type=Path,
        required=True,
        help="EduVidQA CSV files.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("data/eduvidqa/raw"),
        help="Root containing videos/ and transcripts/.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/eduvidqa/ft_context_vlm"),
        help="Output directory for frames and JSONL files.",
    )
    parser.add_argument(
        "--window-seconds",
        type=float,
        default=120.0,
        help="Transcript context radius around timestamp.",
    )
    parser.add_argument(
        "--ffmpeg-bin",
        default="ffmpeg",
        help="ffmpeg executable.",
    )
    parser.add_argument(
        "--overwrite-frames",
        action="store_true",
        help="Regenerate frames even if they already exist.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=0,
        help="Limit samples for smoke tests. 0 means all rows.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build records without extracting frames or writing JSONL.",
    )
    parser.add_argument(
        "--recover-answer-timestamps",
        action="store_true",
        help="Recover missing timestamps from answer text when exactly one timestamp is present.",
    )
    parser.add_argument(
        "--drop-quality-flags",
        nargs="*",
        default=[],
        help="Drop rows with any listed quality flags, e.g. synthetic_rewrite_style short_answer.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Apply the agreed clean EduVidQA filters: synthetic_rewrite_style and short_answer.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    raw_root = args.raw_root.resolve()
    output_root = args.output_root.resolve()
    rows = load_qa_rows(args.input, recover_answer_timestamps=args.recover_answer_timestamps)
    if args.max_samples:
        rows = rows[: args.max_samples]
    drop_quality_flags = set(args.drop_quality_flags)
    if args.clean:
        drop_quality_flags.update({"synthetic_rewrite_style", "short_answer"})

    records_by_split: dict[str, list[dict[str, Any]]] = {}
    skipped: list[dict[str, Any]] = []
    frame_count = 0

    for index, row in enumerate(rows, start=1):
        transcript_path = raw_root / "transcripts" / f"{row.video_id}.json"
        video_path = find_video_path(raw_root, row.video_id)
        if not transcript_path.exists():
            skipped.append(
                {"id": row.row_id, "reason": "missing_transcript", "video_id": row.video_id}
            )
            continue
        if video_path is None:
            skipped.append({"id": row.row_id, "reason": "missing_video", "video_id": row.video_id})
            continue

        transcript_rows = load_transcript(transcript_path)
        transcript_context = build_transcript_context(
            transcript_rows,
            center_seconds=row.timestamp_seconds,
            window_seconds=args.window_seconds,
        )
        if not transcript_context:
            skipped.append({"id": row.row_id, "reason": "empty_context", "video_id": row.video_id})
            continue

        quality_flags = classify_quality_flags(row.answer, question=row.question)
        matched_drop_flags = sorted(drop_quality_flags.intersection(quality_flags))
        if matched_drop_flags:
            skipped.append(
                {
                    "id": row.row_id,
                    "reason": "quality_filtered",
                    "video_id": row.video_id,
                    "flags": matched_drop_flags,
                }
            )
            continue

        relative_frame = frame_relative_path(row, index)
        image_path = output_root / relative_frame
        if not args.dry_run:
            try:
                generated = extract_frame(
                    video_path=video_path,
                    image_path=image_path,
                    timestamp_seconds=row.timestamp_seconds,
                    ffmpeg_bin=args.ffmpeg_bin,
                    overwrite=args.overwrite_frames,
                )
                if generated:
                    frame_count += 1
            except subprocess.CalledProcessError as exc:
                skipped.append(
                    {
                        "id": row.row_id,
                        "reason": "frame_extract_failed",
                        "video_id": row.video_id,
                        "error": str(exc),
                    }
                )
                continue

        record = build_dataset_record(
            row=row,
            image_path=relative_frame,
            transcript_context=transcript_context,
            output_root=output_root,
            quality_flags=quality_flags,
        )
        records_by_split.setdefault(row.split, []).append(record)

        if index == 1 or index % 100 == 0:
            print(f"[{index}/{len(rows)}] prepared {row.row_id}")

    all_records = [
        record for split in sorted(records_by_split) for record in records_by_split[split]
    ]
    if not args.dry_run:
        for split, records in records_by_split.items():
            write_jsonl(output_root / f"{split}.jsonl", records)
        write_jsonl(output_root / "all.jsonl", all_records)
        (output_root / "skipped.json").write_text(
            json.dumps(skipped, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = {
            "samples": len(all_records),
            "frames_generated": frame_count,
            "skipped": len(skipped),
            "splits": {split: len(records) for split, records in records_by_split.items()},
            "window_seconds": args.window_seconds,
            "recover_answer_timestamps": args.recover_answer_timestamps,
            "drop_quality_flags": sorted(drop_quality_flags),
        }
        (output_root / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "samples": len(all_records),
                "skipped": len(skipped),
                "splits": {split: len(records) for split, records in records_by_split.items()},
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_records else 1


if __name__ == "__main__":
    sys.exit(main())
