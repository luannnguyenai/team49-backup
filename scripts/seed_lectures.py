"""
scripts/seed_lectures.py
------------------------
Seeds lecture data (Lecture, Chapter, TranscriptLine) from data/CS231n/ into
the PostgreSQL database using the async engine.

Usage:
    docker compose exec backend uv run python -m scripts.seed_lectures
"""

import asyncio
import glob
import json
import os
import re

from sqlalchemy import func, select

from src.database import async_session_factory
from src.models.store import Chapter, Lecture, TranscriptLine

DATA_DIR = "data/CS231n"
TOC_DIR = os.path.join(DATA_DIR, "ToC_Summary")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")
VIDEO_DIR = os.path.join(DATA_DIR, "videos")


def ts_to_seconds(ts: str) -> float:
    parts = [float(p) for p in ts.strip().split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def parse_transcript(filepath: str) -> list[dict]:
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()
    ts_pattern = re.compile(r"^(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})$", re.MULTILINE)
    matches = list(ts_pattern.finditer(raw))
    lines = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        content = raw[start:end].strip()
        if content:
            lines.append({"start_time": ts_to_seconds(match.group(1)), "content": content})
    return lines


def find_video_for_lecture(lecture_num: int) -> str | None:
    matches = glob.glob(os.path.join(VIDEO_DIR, f"*Lecture*{lecture_num}*"))
    # Filter to exact lecture number (avoid lecture 1 matching lecture 10, 11, ...)
    exact = [m for m in matches if re.search(rf"Lecture\s*{lecture_num}[^0-9]", m)]
    candidates = exact or matches
    return candidates[0] if candidates else None


def find_transcript_for_lecture(lecture_num: int) -> str | None:
    for pattern in [f"*Lecture_{lecture_num}*", f"*Lecture{lecture_num}*"]:
        matches = glob.glob(os.path.join(TRANSCRIPT_DIR, pattern))
        if matches:
            return matches[0]
    return None


async def seed() -> None:
    async with async_session_factory() as db:
        existing = await db.scalar(select(func.count()).select_from(Lecture))
        if existing and existing > 0:
            print(f"Database already has {existing} lectures. Skipping seed.")
            return

        toc_files = sorted(glob.glob(os.path.join(TOC_DIR, "lecture-*.json")))
        print(f"Found {len(toc_files)} ToC files")

        for toc_file in toc_files:
            basename = os.path.basename(toc_file)
            num_match = re.search(r"lecture-(\d+)", basename)
            if not num_match:
                continue
            lecture_num = int(num_match.group(1))

            with open(toc_file, encoding="utf-8") as f:
                toc_data = json.load(f)

            lecture_id = f"cs231n-lecture-{lecture_num}"
            title = toc_data.get("lecture_title", f"Lecture {lecture_num}")
            video_path = find_video_for_lecture(lecture_num)

            db.add(Lecture(
                id=lecture_id,
                title=title,
                description=f"CS231N Spring 2025 - Lecture {lecture_num}",
                video_url=video_path,
                duration=None,
            ))
            await db.flush()
            print(f"  + Lecture: {lecture_id} - {title[:60]}...")

            sections = toc_data.get("table_of_contents", [])
            for i, section in enumerate(sections):
                start_sec = ts_to_seconds(section.get("timestamp", "00:00:00"))
                end_sec = (
                    ts_to_seconds(sections[i + 1].get("timestamp", "00:00:00"))
                    if i + 1 < len(sections)
                    else start_sec + 600
                )
                db.add(Chapter(
                    lecture_id=lecture_id,
                    title=section.get("topic_title", f"Section {i + 1}"),
                    summary=section.get("detailed_summary", "")[:500],
                    start_time=start_sec,
                    end_time=end_sec,
                ))

            transcript_file = find_transcript_for_lecture(lecture_num)
            if transcript_file:
                lines = parse_transcript(transcript_file)
                for j, line in enumerate(lines):
                    end_time = lines[j + 1]["start_time"] if j + 1 < len(lines) else line["start_time"] + 5
                    db.add(TranscriptLine(
                        lecture_id=lecture_id,
                        start_time=line["start_time"],
                        end_time=end_time,
                        content=line["content"],
                    ))
                print(f"    + {len(lines)} transcript lines")
            else:
                print("    (no transcript found)")

        await db.commit()
        total = await db.scalar(select(func.count()).select_from(Lecture))
        print(f"\n✓ Seed complete! {total} lectures in database.")


if __name__ == "__main__":
    asyncio.run(seed())
