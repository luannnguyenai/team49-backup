import asyncio
import json
import logging
import os
import re

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session as _async_session
from src.models.store import Chapter, Lecture, TranscriptLine

logger = logging.getLogger(__name__)


def parse_toc_file(file_path):
    """Parses the new JSON ToC structure."""
    if not os.path.exists(file_path):
        return None
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    return data


def time_to_seconds(time_str):
    """Converts HH:MM:SS or MM:SS to seconds."""
    if not time_str:
        return 0
    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return 0
    return 0


def parse_transcript_text(file_path):
    """
    Parses transcripts where timestamps are on their own lines.
    Format:
    00:00:05
    Text content...
    """
    lines_data = []
    if not os.path.exists(file_path):
        return lines_data

    with open(file_path, encoding="utf-8") as f:
        content = f.read().splitlines()

    current_time = None
    current_text = []

    for line in content:
        line = line.strip()
        if not line:
            continue

        if re.match(r"^\d{1,2}:\d{2}:\d{2}$", line):
            if current_time is not None and current_text:
                sec = time_to_seconds(current_time)
                lines_data.append({"start_time": float(sec), "content": " ".join(current_text)})
            current_time = line
            current_text = []
        elif current_time is not None:
            current_text.append(line)

    if current_time is not None and current_text:
        sec = time_to_seconds(current_time)
        lines_data.append({"start_time": float(sec), "content": " ".join(current_text)})

    for i in range(len(lines_data) - 1):
        lines_data[i]["end_time"] = lines_data[i + 1]["start_time"]
    if lines_data:
        lines_data[-1]["end_time"] = lines_data[-1]["start_time"] + 5.0

    return lines_data


def sanitize_title(title, lecture_id):
    """Standardizes titles to 'Lecture N: Topic' format."""
    match_id = re.search(r"lecture-(\d+)", lecture_id)
    n = match_id.group(1) if match_id else "?"

    title = re.sub(
        r"Stanford\s+CS231N?|Deep\s+Learning\s+for\s+Computer\s+Vision|Spring\s+2025",
        "",
        title,
        flags=re.I,
    )
    title = re.sub(rf"Lecture\s+{n}[:\-]?", "", title, flags=re.I)
    title = re.sub(r"^[|:\-\s]+", "", title)
    title = re.sub(r"\s+", " ", title).strip()

    return f"Lecture {n}: {title}"


async def ingest_lecture(
    lecture_id: str,
    toc_path: str,
    transcript_paths: list[str],
    video_rel_path: str | None = None,
    db: AsyncSession | None = None,
) -> None:
    """Ingests a lecture using the new JSON ToC and Transcript format (async)."""

    async def _run(session: AsyncSession) -> None:
        toc_data = parse_toc_file(toc_path)
        if not toc_data:
            logger.error("ToC file not found at %s", toc_path)
            return

        raw_title = toc_data.get("lecture_title", lecture_id)
        clean_title = sanitize_title(raw_title, lecture_id)

        result = await session.execute(select(Lecture).where(Lecture.id == lecture_id))
        lecture = result.scalar_one_or_none()

        if not lecture:
            lecture = Lecture(id=lecture_id, title=clean_title, video_url=video_rel_path)
            session.add(lecture)
        else:
            lecture.title = clean_title
            lecture.video_url = video_rel_path

        await session.execute(delete(Chapter).where(Chapter.lecture_id == lecture_id))
        await session.execute(delete(TranscriptLine).where(TranscriptLine.lecture_id == lecture_id))

        toc_items = toc_data.get("table_of_contents", [])
        for i, item in enumerate(toc_items):
            start_sec = time_to_seconds(item.get("timestamp", "00:00:00"))
            if i < len(toc_items) - 1:
                end_sec = time_to_seconds(toc_items[i + 1].get("timestamp"))
            else:
                end_sec = start_sec + 3600.0

            chapter = Chapter(
                lecture_id=lecture_id,
                title=item.get("topic_title", "Untitled"),
                summary=item.get("detailed_summary", ""),
                start_time=float(start_sec),
                end_time=float(end_sec),
            )
            session.add(chapter)

        for t_path in transcript_paths:
            lines = parse_transcript_text(t_path)
            for tl in lines:
                line = TranscriptLine(
                    lecture_id=lecture_id,
                    start_time=tl["start_time"],
                    end_time=tl["end_time"],
                    content=tl["content"],
                )
                session.add(line)

        await session.flush()
        logger.info("Ingested lecture: %s (%s)", lecture_id, clean_title)

    if db is not None:
        await _run(db)
    else:
        async with _async_session() as session:
            await _run(session)
            await session.commit()


if __name__ == "__main__":
    asyncio.run(ingest_lecture(
        "lecture-1",
        "data/cs231n/ToC_Summary/lecture-1.json",
        [
            "data/cs231n/transcripts/Stanford_CS231N_Deep_Learning_for_Computer_Vision__Spring_2025__Lecture_1_Introduction_transcript.txt"
        ],
        video_rel_path="cs231n/videos/Stanford CS231N Deep Learning for Computer Vision ｜ Spring 2025 ｜ Lecture 1： Introduction.mp4",
    ))
