"""
services/learning_unit_service.py
---------------------------------
Learning-unit payloads for the canonical lecture experience.

US3: Maps legacy lecture data (from `store.py` Lecture model and data/courses/CS231n/)
to the canonical `LearningUnitResponse` shape defined by the course-platform
contract.

The mapping uses bootstrap JSON (`data/bootstrap/units.json`) to
connect unit slugs to legacy lecture IDs and video files.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

from sqlalchemy import select

from src.data_paths import CS231N_DIR, UNITS_FILE as BOOTSTRAP_UNITS_FILE
from src.data_paths import CS224N_DIR
from src.models.canonical import CanonicalUnit
from src.models.course import Course, LearningUnit
from src.schemas.course import (
    LearningUnitContentPayload,
    LearningUnitCourseSummary,
    LearningUnitResponse,
    LearningUnitSummary,
    TutorContextPayload,
)
from src.services.asset_signing import build_signed_asset_url
from src.services.legacy_lecture_adapter import (
    build_tutor_bridge_payload,
    normalize_legacy_lecture_id,
)
from src.services.course_bootstrap_service import get_bootstrap_course

# ---------------------------------------------------------------------------
# Bootstrap unit data
# ---------------------------------------------------------------------------

UNITS_FILE = BOOTSTRAP_UNITS_FILE
TRANSCRIPTS_DIR = CS231N_DIR / "transcripts"
SLIDES_DIR = CS231N_DIR / "slides"
_LECTURE_NUMBER_RE = re.compile(r"(?:lecture|Lecture)[_ -]?0*(\d+)")
_LECTURE_AVAILABILITY_CACHE: dict[Path, tuple[int | None, set[int]]] = {}


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_bootstrap_units() -> list[dict[str, Any]]:
    """Load the learning units bootstrap data."""
    if not UNITS_FILE.exists():
        return []
    return _read_json(UNITS_FILE)


def _extract_available_lecture_numbers(directory: Path) -> set[int]:
    if not directory.exists():
        return set()

    numbers: set[int] = set()
    for asset in directory.iterdir():
        if not asset.is_file():
            continue
        match = _LECTURE_NUMBER_RE.search(asset.name)
        if match:
            numbers.add(int(match.group(1)))
    return numbers


def _directory_mtime_ns(directory: Path) -> int | None:
    if not directory.exists():
        return None
    return directory.stat().st_mtime_ns


def _available_lecture_numbers(directory: Path) -> set[int]:
    current_mtime = _directory_mtime_ns(directory)
    cached = _LECTURE_AVAILABILITY_CACHE.get(directory)
    if cached is not None and cached[0] == current_mtime:
        return set(cached[1])

    numbers = _extract_available_lecture_numbers(directory)
    _LECTURE_AVAILABILITY_CACHE[directory] = (current_mtime, numbers)
    return set(numbers)


def _available_transcript_lectures() -> set[int]:
    return _available_lecture_numbers(TRANSCRIPTS_DIR)


def _available_slide_lectures() -> set[int]:
    return _available_lecture_numbers(SLIDES_DIR)


def _available_transcript_lectures_for(course_slug: str) -> set[int]:
    course_dir = _course_dir_for_slug(course_slug)
    if course_dir is None:
        return set()
    return _available_lecture_numbers(course_dir / "transcripts")


def _available_slide_lectures_for(course_slug: str) -> set[int]:
    course_dir = _course_dir_for_slug(course_slug)
    if course_dir is None:
        return set()
    return _available_lecture_numbers(course_dir / "slides")


def get_bootstrap_unit(course_slug: str, unit_slug: str) -> dict[str, Any] | None:
    """Find a unit by course slug and unit slug."""
    for unit in load_bootstrap_units():
        if unit["course_slug"] == course_slug and unit["slug"] == unit_slug:
            return unit
    return None


def get_first_unit_slug(course_slug: str) -> str | None:
    """Get the slug of the first learning unit for a course."""
    units = [u for u in load_bootstrap_units() if u["course_slug"] == course_slug]
    if not units:
        return None
    units.sort(key=lambda u: u.get("order_index", 0))
    return units[0]["slug"]


def list_course_units(course_slug: str) -> list[dict[str, Any]]:
    """List all learning units for a course, ordered by order_index."""
    units = [u for u in load_bootstrap_units() if u["course_slug"] == course_slug]
    units.sort(key=lambda u: u.get("order_index", 0))
    return units


async def list_course_units_db_first(course_slug: str) -> list[dict[str, Any]]:
    db_units = await _list_course_units_from_db(course_slug)
    if db_units:
        return db_units
    return list_course_units(course_slug)


# ---------------------------------------------------------------------------
# Main service function
# ---------------------------------------------------------------------------


async def get_learning_unit_payload(
    course_slug: str,
    unit_slug: str,
) -> LearningUnitResponse | None:
    """
    Build the full learning unit payload for the canonical lecture experience.

    Resolves course info from bootstrap courses, unit info from bootstrap units,
    and constructs the video URL from the data directory.
    """
    db_payload = await _get_learning_unit_payload_from_db(course_slug, unit_slug)
    if db_payload is not None and (
        db_payload["content"].get("video_url") is not None
        or get_bootstrap_unit(course_slug, unit_slug) is None
    ):
        return LearningUnitResponse.model_validate(db_payload)

    course_row = get_bootstrap_course(course_slug)
    if course_row is None:
        return None

    unit_row = get_bootstrap_unit(course_slug, unit_slug)
    if unit_row is None:
        return None

    # Build video URL from the filename
    video_filename = unit_row.get("video_filename")
    video_url: str | None = None
    if video_filename:
        # Protected course assets are exposed via short-lived signed URLs.
        video_path = CS231N_DIR / "videos" / video_filename
        if video_path.exists():
            video_url = build_signed_asset_url(f"courses/CS231n/videos/{video_filename}")
    if video_url is None:
        fallback_video_filename = _find_course_video_filename(course_slug, unit_row.get("order_index"))
        if fallback_video_filename:
            course_dir = _course_dir_for_slug(course_slug)
            if course_dir is not None:
                video_url = build_signed_asset_url(
                    f"courses/{course_dir.name}/videos/{fallback_video_filename}"
                )

    # Check transcript and slides availability
    lecture_num = unit_row.get("order_index", 0)
    transcript_available = bool(lecture_num and lecture_num in _available_transcript_lectures())
    slides_available = bool(lecture_num and lecture_num in _available_slide_lectures())

    # Determine if tutor should be enabled
    # Tutor is enabled when the unit is ready and has video content
    tutor_enabled = unit_row["status"] == "ready" and video_url is not None
    legacy_lecture_id = normalize_legacy_lecture_id(
        unit_row.get("legacy_lecture_id"),
        unit_row.get("order_index"),
    )
    tutor_bridge = build_tutor_bridge_payload(
        tutor_enabled=tutor_enabled,
        unit_id=unit_row["id"],
        legacy_lecture_id=legacy_lecture_id,
    )

    return LearningUnitResponse(
        course=LearningUnitCourseSummary(
            slug=course_row["slug"],
            title=course_row["title"],
        ),
        unit=LearningUnitSummary(
            id=unit_row["id"],
            slug=unit_row["slug"],
            title=unit_row["title"],
            unit_type=unit_row["unit_type"],
            status=unit_row["status"],
            entry_mode=unit_row["entry_mode"],
        ),
        content=LearningUnitContentPayload(
            body_markdown=unit_row.get("body_markdown"),
            video_url=video_url,
            transcript_available=transcript_available,
            slides_available=slides_available,
        ),
        tutor=TutorContextPayload(
            enabled=tutor_bridge["enabled"],
            mode=tutor_bridge["mode"],
            context_binding_id=tutor_bridge["context_binding_id"],
            legacy_lecture_id=tutor_bridge["legacy_lecture_id"],
        ),
    )


async def _list_course_units_from_db(course_slug: str) -> list[dict[str, Any]]:
    try:
        from src.database import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                select(LearningUnit)
                .join(Course, LearningUnit.course_id == Course.id)
                .where(Course.slug == course_slug)
                .order_by(LearningUnit.sort_order, LearningUnit.slug)
            )
            units = result.scalars().all()
            return [
                {
                    "slug": unit.slug,
                    "title": unit.title,
                    "status": unit.status.value,
                    "unit_type": unit.unit_type.value,
                    "order_index": unit.sort_order,
                }
                for unit in units
            ]
    except Exception:
        return []


def _course_dir_for_slug(course_slug: str) -> Path | None:
    if course_slug == "cs231n":
        return CS231N_DIR
    if course_slug == "cs224n":
        return CS224N_DIR
    return None


def _find_course_video_filename(course_slug: str, lecture_num: int | None) -> str | None:
    if lecture_num is None:
        return None
    course_dir = _course_dir_for_slug(course_slug)
    if course_dir is None:
        return None
    video_dir = course_dir / "videos"
    if not video_dir.exists():
        return None
    for asset in sorted(video_dir.iterdir()):
        if not asset.is_file():
            continue
        match = _LECTURE_NUMBER_RE.search(asset.name)
        if match and int(match.group(1)) == lecture_num:
            return asset.name
    return None


async def _get_learning_unit_payload_from_db(course_slug: str, unit_slug: str) -> dict | None:
    try:
        from src.database import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                select(LearningUnit, Course, CanonicalUnit)
                .join(Course, LearningUnit.course_id == Course.id)
                .outerjoin(CanonicalUnit, LearningUnit.canonical_unit_id == CanonicalUnit.unit_id)
                .where(
                    Course.slug == course_slug,
                    LearningUnit.slug == unit_slug,
                )
            )
            row = result.first()
            if row is None:
                return None

            unit, course, canonical_unit = row
            lecture_num = (
                int(canonical_unit.lecture_order)
                if canonical_unit is not None and canonical_unit.lecture_order is not None
                else None
            )
            video_url = None
            video_filename = _find_course_video_filename(course_slug, lecture_num)
            course_dir = _course_dir_for_slug(course_slug)
            if video_filename and course_dir is not None:
                video_url = build_signed_asset_url(f"courses/{course_dir.name}/videos/{video_filename}")

            transcript_available = bool(
                canonical_unit is not None
                and canonical_unit.transcript_path
                and Path(canonical_unit.transcript_path).exists()
            )
            slides_available = bool(
                lecture_num and lecture_num in _available_slide_lectures_for(course_slug)
            )

            legacy_lecture_id = None
            tutor_enabled = False
            if course_slug == "cs231n":
                legacy_lecture_id = normalize_legacy_lecture_id(None, lecture_num)
                tutor_enabled = video_url is not None and legacy_lecture_id is not None

            tutor_bridge = build_tutor_bridge_payload(
                tutor_enabled=tutor_enabled,
                unit_id=str(unit.id),
                legacy_lecture_id=legacy_lecture_id,
            )

            return {
                "course": {
                    "slug": course.slug,
                    "title": course.title,
                },
                "unit": {
                    "id": str(unit.id),
                    "slug": unit.slug,
                    "title": unit.title,
                    "unit_type": unit.unit_type.value,
                    "status": unit.status.value,
                    "entry_mode": unit.entry_mode.value,
                },
                "content": {
                    "body_markdown": unit.content_body,
                    "video_url": video_url,
                    "transcript_available": transcript_available,
                    "slides_available": slides_available,
                },
                "tutor": tutor_bridge,
            }
    except Exception:
        return None
