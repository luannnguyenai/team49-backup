"""
Seed lecture runtime tables (Lecture, Chapter, TranscriptLine) for all video-backed
course lectures used by the learning shell and in-context tutor.
"""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data_paths import CS224N_DIR, CS231N_DIR
from src.database import async_session_factory
from src.models.canonical import CanonicalUnit
from src.models.store import Chapter, Lecture, TranscriptLine
from src.services.legacy_lecture_adapter import build_course_runtime_lecture_id

_LECTURE_NUMBER_RE = re.compile(r"(?:lecture|Lecture)[_ -]?0*(\d+)")
_TIMESTAMP_RE = re.compile(r"^(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})$", re.MULTILINE)


@dataclass(frozen=True)
class RuntimeChapterSpec:
    title: str
    summary: str
    start_time: float
    end_time: float


@dataclass(frozen=True)
class RuntimeLectureSpec:
    course_slug: str
    course_dir: Path
    lecture_order: int
    lecture_id: str
    lecture_title: str
    video_url: str | None
    transcript_path: Path | None
    chapters: tuple[RuntimeChapterSpec, ...]


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


def _normalize_course_slug(course_id: str | None) -> str | None:
    if not course_id:
        return None
    return course_id.strip().lower()


def _content_start_seconds(unit: CanonicalUnit) -> float:
    content_ref = unit.content_ref or {}
    start_value = content_ref.get("start_s")
    if isinstance(start_value, (int, float)):
        return float(start_value)
    return 0.0


def _content_end_seconds(unit: CanonicalUnit) -> float | None:
    content_ref = unit.content_ref or {}
    end_value = content_ref.get("end_s")
    if isinstance(end_value, (int, float)):
        return float(end_value)
    return None


def _resolve_transcript_path(
    course_dir: Path,
    lecture_order: int,
    transcript_path: str | None,
) -> Path | None:
    if transcript_path:
        candidate = Path(transcript_path)
        if candidate.exists():
            return candidate
    return _find_course_transcript(course_dir, lecture_order)


def _build_runtime_chapters(units: list[CanonicalUnit]) -> tuple[RuntimeChapterSpec, ...]:
    chapters: list[RuntimeChapterSpec] = []
    ordered_units = sorted(
        units,
        key=lambda unit: (
            _content_start_seconds(unit),
            unit.ordering_index or 0,
            unit.unit_id,
        ),
    )
    for index, unit in enumerate(ordered_units):
        start_sec = _content_start_seconds(unit)
        next_start = (
            _content_start_seconds(ordered_units[index + 1])
            if index + 1 < len(ordered_units)
            else None
        )
        end_sec = next_start or _content_end_seconds(unit) or (start_sec + 600.0)
        chapters.append(
            RuntimeChapterSpec(
                title=unit.unit_name or unit.description or f"Section {index + 1}",
                summary=(unit.summary or unit.description or "")[:2000],
                start_time=start_sec,
                end_time=end_sec,
            )
        )
    return tuple(chapters)


def _build_runtime_lecture_specs(units: list[CanonicalUnit]) -> list[RuntimeLectureSpec]:
    course_dirs = dict(_course_specs())
    grouped: dict[tuple[str, int], list[CanonicalUnit]] = defaultdict(list)
    for unit in units:
        course_slug = _normalize_course_slug(unit.course_id)
        if course_slug not in course_dirs:
            continue
        if unit.lecture_order is None:
            continue
        grouped[(course_slug, int(unit.lecture_order))].append(unit)

    specs: list[RuntimeLectureSpec] = []
    for (course_slug, lecture_order), grouped_units in sorted(grouped.items()):
        course_dir = course_dirs[course_slug]
        ordered_units = sorted(
            grouped_units,
            key=lambda unit: (
                _content_start_seconds(unit),
                unit.ordering_index or 0,
                unit.unit_id,
            ),
        )
        primary_unit = ordered_units[0]
        transcript_path = _resolve_transcript_path(
            course_dir,
            lecture_order,
            next((unit.transcript_path for unit in ordered_units if unit.transcript_path), None),
        )
        video_path = _find_course_video(course_dir, lecture_order)
        content_ref = primary_unit.content_ref or {}
        video_url = str(video_path) if video_path is not None else content_ref.get("video_url")
        lecture_id = build_course_runtime_lecture_id(
            course_slug=course_slug,
            lecture_order=lecture_order,
            explicit_lecture_id=next((unit.lecture_id for unit in ordered_units if unit.lecture_id), None),
            video_filename=video_path.name if video_path is not None else None,
        )
        if lecture_id is None:
            continue
        lecture_title = primary_unit.lecture_title or f"{course_slug.upper()} Lecture {lecture_order}"
        specs.append(
            RuntimeLectureSpec(
                course_slug=course_slug,
                course_dir=course_dir,
                lecture_order=lecture_order,
                lecture_id=lecture_id,
                lecture_title=lecture_title,
                video_url=video_url,
                transcript_path=transcript_path,
                chapters=_build_runtime_chapters(ordered_units),
            )
        )
    return specs


async def _load_runtime_lecture_specs(session: AsyncSession) -> list[RuntimeLectureSpec]:
    supported_courses = [course_slug for course_slug, _ in _course_specs()]
    result = await session.execute(
        select(CanonicalUnit).where(
            func.lower(CanonicalUnit.course_id).in_(supported_courses),
            CanonicalUnit.lecture_order.is_not(None),
        )
    )
    return _build_runtime_lecture_specs(list(result.scalars().all()))


async def _upsert_lecture_runtime(
    session: AsyncSession,
    *,
    spec: RuntimeLectureSpec,
) -> None:
    result = await session.execute(select(Lecture).where(Lecture.id == spec.lecture_id))
    lecture = result.scalar_one_or_none()

    if lecture is None:
        lecture = Lecture(
            id=spec.lecture_id,
            title=spec.lecture_title,
            description=f"{spec.course_slug.upper()} lecture {spec.lecture_order}",
            video_url=spec.video_url,
            duration=None,
        )
        session.add(lecture)
    else:
        lecture.title = spec.lecture_title
        lecture.description = f"{spec.course_slug.upper()} lecture {spec.lecture_order}"
        lecture.video_url = spec.video_url

    await session.execute(delete(Chapter).where(Chapter.lecture_id == spec.lecture_id))
    await session.execute(delete(TranscriptLine).where(TranscriptLine.lecture_id == spec.lecture_id))

    for chapter in spec.chapters:
        session.add(
            Chapter(
                lecture_id=spec.lecture_id,
                title=chapter.title,
                summary=chapter.summary,
                start_time=chapter.start_time,
                end_time=chapter.end_time,
            )
        )

    if spec.transcript_path is not None:
        lines = parse_transcript(spec.transcript_path)
        for line_index, line in enumerate(lines):
            end_time = (
                lines[line_index + 1]["start_time"]
                if line_index + 1 < len(lines)
                else line["start_time"] + 5
            )
            session.add(
                TranscriptLine(
                    lecture_id=spec.lecture_id,
                    start_time=line["start_time"],
                    end_time=end_time,
                    content=line["content"],
                )
            )


async def seed(session: AsyncSession | None = None) -> None:
    async def _run(active_session: AsyncSession) -> None:
        specs = await _load_runtime_lecture_specs(active_session)
        for spec in specs:
            await _upsert_lecture_runtime(active_session, spec=spec)

    if session is not None:
        await _run(session)
        return

    async with async_session_factory() as db:
        await _run(db)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
