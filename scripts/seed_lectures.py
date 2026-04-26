"""
Seed lecture runtime tables (Lecture, Chapter, TranscriptLine) for all video-backed
course lectures used by the learning shell and in-context tutor.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data_paths import CS224N_DIR, CS231N_DIR
from src.database import async_session_factory
from src.models.store import Chapter, Lecture, TranscriptLine
from src.services.legacy_lecture_adapter import build_course_runtime_lecture_id

_LECTURE_NUMBER_RE = re.compile(r"(?:lecture|Lecture)[_ -]?0*(\d+)")
_TIMESTAMP_RE = re.compile(r"^(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})$", re.MULTILINE)


def ts_to_seconds(ts: str) -> float:
    parts = [float(p) for p in ts.strip().split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def parse_transcript(filepath: Path) -> list[dict]:
    raw = filepath.read_text(encoding="utf-8")
    matches = list(_TIMESTAMP_RE.finditer(raw))
    lines = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        content = raw[start:end].strip()
        if content:
            lines.append({"start_time": ts_to_seconds(match.group(1)), "content": content})
    return lines


def _extract_lecture_number(name: str) -> int | None:
    match = _LECTURE_NUMBER_RE.search(name)
    if not match:
        return None
    return int(match.group(1))


def _find_course_video(course_dir: Path, lecture_num: int) -> Path | None:
    video_dir = course_dir / "videos"
    if not video_dir.exists():
        return None
    candidates: list[Path] = []
    for asset in sorted(video_dir.iterdir()):
        if asset.is_file() and _extract_lecture_number(asset.name) == lecture_num:
            candidates.append(asset)
    return candidates[0] if candidates else None


def _find_course_transcript(course_dir: Path, lecture_num: int) -> Path | None:
    transcript_dir = course_dir / "transcripts"
    if not transcript_dir.exists():
        return None
    candidates: list[Path] = []
    for asset in sorted(transcript_dir.iterdir()):
        if asset.is_file() and _extract_lecture_number(asset.name) == lecture_num:
            candidates.append(asset)
    return candidates[0] if candidates else None


def _course_specs() -> list[tuple[str, Path]]:
    return [
        ("cs231n", CS231N_DIR),
        ("cs224n", CS224N_DIR),
    ]


async def _upsert_lecture_runtime(
    session: AsyncSession,
    *,
    course_slug: str,
    course_dir: Path,
    toc_file: Path,
) -> None:
    lecture_num = _extract_lecture_number(toc_file.name)
    if lecture_num is None:
        return

    toc_data = json.loads(toc_file.read_text(encoding="utf-8"))
    video_path = _find_course_video(course_dir, lecture_num)
    transcript_path = _find_course_transcript(course_dir, lecture_num)
    lecture_id = build_course_runtime_lecture_id(
        course_slug=course_slug,
        lecture_order=lecture_num,
        explicit_lecture_id=f"lecture-{lecture_num}",
        video_filename=video_path.name if video_path is not None else None,
    )
    if lecture_id is None:
        return

    result = await session.execute(select(Lecture).where(Lecture.id == lecture_id))
    lecture = result.scalar_one_or_none()
    lecture_title = toc_data.get("lecture_title", f"{course_slug.upper()} Lecture {lecture_num}")
    video_url = str(video_path) if video_path is not None else None

    if lecture is None:
        lecture = Lecture(
            id=lecture_id,
            title=lecture_title,
            description=f"{course_slug.upper()} lecture {lecture_num}",
            video_url=video_url,
            duration=None,
        )
        session.add(lecture)
    else:
        lecture.title = lecture_title
        lecture.description = f"{course_slug.upper()} lecture {lecture_num}"
        lecture.video_url = video_url

    await session.execute(delete(Chapter).where(Chapter.lecture_id == lecture_id))
    await session.execute(delete(TranscriptLine).where(TranscriptLine.lecture_id == lecture_id))

    sections = toc_data.get("table_of_contents", [])
    for index, section in enumerate(sections):
        start_sec = ts_to_seconds(section.get("timestamp", "00:00:00"))
        end_sec = (
            ts_to_seconds(sections[index + 1].get("timestamp", "00:00:00"))
            if index + 1 < len(sections)
            else start_sec + 600
        )
        session.add(
            Chapter(
                lecture_id=lecture_id,
                title=section.get("topic_title", f"Section {index + 1}"),
                summary=section.get("detailed_summary", "")[:2000],
                start_time=start_sec,
                end_time=end_sec,
            )
        )

    if transcript_path is not None:
        lines = parse_transcript(transcript_path)
        for line_index, line in enumerate(lines):
            end_time = (
                lines[line_index + 1]["start_time"]
                if line_index + 1 < len(lines)
                else line["start_time"] + 5
            )
            session.add(
                TranscriptLine(
                    lecture_id=lecture_id,
                    start_time=line["start_time"],
                    end_time=end_time,
                    content=line["content"],
                )
            )


async def seed(session: AsyncSession | None = None) -> None:
    async def _run(active_session: AsyncSession) -> None:
        for course_slug, course_dir in _course_specs():
            toc_dir = course_dir / "ToC_Summary"
            if not toc_dir.exists():
                continue
            toc_files = sorted(toc_dir.glob("lecture-*.json"))
            for toc_file in toc_files:
                await _upsert_lecture_runtime(
                    active_session,
                    course_slug=course_slug,
                    course_dir=course_dir,
                    toc_file=toc_file,
                )

    if session is not None:
        await _run(session)
        return

    async with async_session_factory() as db:
        await _run(db)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
