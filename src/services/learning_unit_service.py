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
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.config import settings
from src.data_paths import CS224N_DIR, CS230_DIR, CS231N_DIR
from src.data_paths import UNITS_FILE as BOOTSTRAP_UNITS_FILE
from src.models.canonical import CanonicalUnit
from src.models.course import (
    Course,
    CourseSection,
    LearningProgressRecord,
    LearningProgressStatus,
    LearningUnit,
)
from src.schemas.course import (
    LearningUnitContentPayload,
    LearningUnitCourseSummary,
    LearningUnitResponse,
    LearningUnitSummary,
    TutorContextPayload,
)
from src.services.asset_delivery import AssetDeliveryConfigError, build_cloudfront_url
from src.services.asset_signing import build_signed_asset_url
from src.services.course_bootstrap_service import get_bootstrap_course
from src.services.legacy_lecture_adapter import (
    build_course_runtime_lecture_id,
    build_tutor_bridge_payload,
)

# ---------------------------------------------------------------------------
# Asset URL resolution (local /data signed URL vs AWS CloudFront URL)
# ---------------------------------------------------------------------------


def _resolve_course_asset_url(
    storage_key: str,
    *,
    local_disk_path: Path | None = None,
) -> str | None:
    """
    Resolve a course asset URL based on `settings.asset_storage_provider`.

    - 's3': always returns a CloudFront URL. The local disk does not need the
      file (Render image ships without `data/courses/...`). Returns None if
      CloudFront domain is not configured.
    - 'local' (default): returns a `/data/...` signed URL. If `local_disk_path`
      is provided and missing, returns None to preserve current behavior of
      hiding the video when the file is absent from disk.
    """
    if settings.asset_storage_provider == "s3":
        try:
            return build_cloudfront_url(storage_key)
        except AssetDeliveryConfigError:
            return None
    if local_disk_path is not None and not local_disk_path.exists():
        return None
    return build_signed_asset_url(storage_key)


def _resolve_transcript_available(transcript_path: str | None) -> bool:
    """
    Decide whether a transcript should be marked available.

    - 's3': trust DB metadata. If `transcript_path` is non-empty, treat as
      available (file lives in S3 / canonical store, not on the local disk
      that the Render container can see).
    - 'local': require the file to exist on disk to preserve current dev
      behavior.
    """
    if not transcript_path:
        return False
    if settings.asset_storage_provider == "s3":
        return True
    return Path(transcript_path).exists()


# ---------------------------------------------------------------------------
# Bootstrap unit data
# ---------------------------------------------------------------------------

UNITS_FILE = BOOTSTRAP_UNITS_FILE
TRANSCRIPTS_DIR = CS231N_DIR / "transcripts"
SLIDES_DIR = CS231N_DIR / "slides"
_LECTURE_NUMBER_RE = re.compile(r"(?:lecture|Lecture)[_ -]?0*(\d+)")
_LECTURE_AVAILABILITY_CACHE: dict[Path, tuple[int | None, set[int]]] = {}

# Asset manifest baked at build time from local data/courses listing.
# Used in s3 mode where the container has no mp4/pdf binary files (excluded by
# .dockerignore). The manifest maps {kind: {course_slug: {lecture_num: filename}}}.
_ASSET_MANIFEST_PATH = Path("data/asset_manifest.json")


@lru_cache(maxsize=1)
def _load_asset_manifest() -> dict:
    if not _ASSET_MANIFEST_PATH.exists():
        return {"videos": {}, "slides": {}, "transcripts": {}}
    with _ASSET_MANIFEST_PATH.open(encoding="utf-8") as h:
        return json.load(h)


def _manifest_lookup(kind: str, course_slug: str, lecture_num: int) -> str | None:
    return _load_asset_manifest().get(kind, {}).get(course_slug, {}).get(str(lecture_num))


def _manifest_available_lectures(kind: str, course_slug: str) -> set[int]:
    return {int(k) for k in _load_asset_manifest().get(kind, {}).get(course_slug, {})}


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
    if settings.asset_storage_provider == "s3":
        return _manifest_available_lectures("transcripts", course_slug)
    course_dir = _course_dir_for_slug(course_slug)
    if course_dir is None:
        return set()
    return _available_lecture_numbers(course_dir / "transcripts")


def _available_slide_lectures_for(course_slug: str) -> set[int]:
    if settings.asset_storage_provider == "s3":
        return _manifest_available_lectures("slides", course_slug)
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
    """List one video-backed lecture entry per course, ordered by lecture number."""
    units = [u for u in load_bootstrap_units() if u["course_slug"] == course_slug]
    units.sort(key=lambda u: u.get("order_index", 0))

    video_units: list[dict[str, Any]] = []
    for unit in units:
        order_index = unit.get("order_index", 0)
        video_filename = unit.get("video_filename") or _find_course_video_filename(
            course_slug,
            order_index,
        )
        if not video_filename:
            continue
        video_units.append(
            {
                "id": unit.get("id"),
                "slug": unit["slug"],
                "title": unit["title"],
                "status": unit["status"],
                "unit_type": "lecture",
                "order_index": order_index,
                "lecture_label": f"Lecture {order_index:02d}",
                "canonical_unit_id": unit.get("canonical_unit_id"),
                "is_completed": False,
            }
        )
    return video_units


async def list_course_units_db_first(
    course_slug: str,
    *,
    user_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    db_units = await _list_course_units_from_db(course_slug)
    units = db_units or list_course_units(course_slug)

    completed_unit_ids: set[uuid.UUID] = set()
    if user_id is not None:
        unit_ids = [
            parsed_unit_id
            for unit in units
            if (parsed_unit_id := _parse_unit_id(unit.get("id"))) is not None
        ]
        completed_unit_ids = await _get_completed_learning_unit_ids(user_id, unit_ids)

    return [
        {
            **unit,
            "is_completed": _parse_unit_id(unit.get("id")) in completed_unit_ids,
        }
        for unit in units
    ]


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

    # Build video URL from the filename. Provider switch:
    # - local: /data signed URL only when the file exists on disk.
    # - s3:    CloudFront URL based on storage key (no disk check).
    video_filename = unit_row.get("video_filename")
    video_url: str | None = None
    fallback_video_filename: str | None = None
    if video_filename:
        video_url = _resolve_course_asset_url(
            f"courses/CS231n/videos/{video_filename}",
            local_disk_path=CS231N_DIR / "videos" / video_filename,
        )
    if video_url is None:
        fallback_video_filename = _find_course_video_filename(
            course_slug, unit_row.get("order_index")
        )
        if fallback_video_filename:
            course_dir = _course_dir_for_slug(course_slug)
            if course_dir is not None:
                video_url = _resolve_course_asset_url(
                    f"courses/{course_dir.name}/videos/{fallback_video_filename}",
                    local_disk_path=course_dir / "videos" / fallback_video_filename,
                )

    # Check transcript and slides availability
    lecture_num = unit_row.get("order_index", 0)
    transcript_available = bool(lecture_num and lecture_num in _available_transcript_lectures())
    slides_available = bool(lecture_num and lecture_num in _available_slide_lectures())

    # Determine if tutor should be enabled
    # Tutor is enabled when the unit is ready and has video content
    runtime_lecture_id = build_course_runtime_lecture_id(
        course_slug=course_slug,
        lecture_order=unit_row.get("order_index"),
        explicit_lecture_id=unit_row.get("legacy_lecture_id"),
        video_filename=video_filename or fallback_video_filename,
    )
    tutor_enabled = (
        unit_row["status"] == "ready" and video_url is not None and runtime_lecture_id is not None
    )
    tutor_bridge = build_tutor_bridge_payload(
        tutor_enabled=tutor_enabled,
        unit_id=unit_row["id"],
        legacy_lecture_id=runtime_lecture_id,
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
            lecture_title=unit_row["title"],
            lecture_order=unit_row.get("order_index"),
            start_seconds=None,
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
                select(LearningUnit, CourseSection)
                .join(Course, LearningUnit.course_id == Course.id)
                .join(CourseSection, LearningUnit.section_id == CourseSection.id)
                .where(Course.slug == course_slug)
                .order_by(CourseSection.sort_order, LearningUnit.sort_order, LearningUnit.slug)
            )
            rows = result.all()
            lecture_units: list[dict[str, Any]] = []
            seen_section_ids: set[str] = set()
            for unit, section in rows:
                section_id = str(section.id)
                if section_id in seen_section_ids:
                    continue
                seen_section_ids.add(section_id)
                # Note: skip filesystem video filename check — production reads
                # video URL from canonical content_ref (YouTube) or S3 storage key,
                # not from local data/courses/<C>/videos/. Dockerignore strips mp4
                # so this check would always filter out all units in container.
                lecture_units.append(
                    {
                        "id": str(unit.id),
                        "slug": unit.slug,
                        "title": section.title,
                        "status": unit.status.value,
                        "unit_type": "lecture",
                        "order_index": section.sort_order,
                        "lecture_label": f"Lecture {section.sort_order:02d}",
                        "canonical_unit_id": unit.canonical_unit_id,
                    }
                )
            return lecture_units
    except Exception:
        return []


def _parse_unit_id(unit_id: Any) -> uuid.UUID | None:
    if unit_id is None:
        return None
    if isinstance(unit_id, uuid.UUID):
        return unit_id
    try:
        return uuid.UUID(str(unit_id))
    except (TypeError, ValueError):
        return None


async def _get_completed_learning_unit_ids(
    user_id: uuid.UUID,
    learning_unit_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    if not learning_unit_ids:
        return set()

    try:
        from src.database import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                select(LearningProgressRecord.learning_unit_id).where(
                    LearningProgressRecord.user_id == user_id,
                    LearningProgressRecord.learning_unit_id.in_(learning_unit_ids),
                    LearningProgressRecord.status == LearningProgressStatus.completed,
                )
            )
            return set(result.scalars().all())
    except Exception:
        return set()


def _course_dir_for_slug(course_slug: str) -> Path | None:
    if course_slug == "cs231n":
        return CS231N_DIR
    if course_slug == "cs224n":
        return CS224N_DIR
    if course_slug == "cs230":
        return CS230_DIR
    return None


def _find_course_video_filename(course_slug: str, lecture_num: int | None) -> str | None:
    if lecture_num is None:
        return None
    if settings.asset_storage_provider == "s3":
        # Container has no mp4 (stripped by .dockerignore). Use baked manifest.
        return _manifest_lookup("videos", course_slug, lecture_num)
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
                select(LearningUnit, Course, CourseSection, CanonicalUnit)
                .join(Course, LearningUnit.course_id == Course.id)
                .join(CourseSection, LearningUnit.section_id == CourseSection.id)
                .outerjoin(CanonicalUnit, LearningUnit.canonical_unit_id == CanonicalUnit.unit_id)
                .where(
                    Course.slug == course_slug,
                    LearningUnit.slug == unit_slug,
                )
            )
            row = result.first()
            if row is None:
                return None

            unit, course, section, canonical_unit = row
            content_ref = canonical_unit.content_ref if canonical_unit is not None else {}
            lecture_num = (
                int(canonical_unit.lecture_order)
                if canonical_unit is not None and canonical_unit.lecture_order is not None
                else None
            )
            video_url = None
            video_filename = _find_course_video_filename(course_slug, lecture_num)
            course_dir = _course_dir_for_slug(course_slug)
            if video_filename and course_dir is not None:
                video_url = _resolve_course_asset_url(
                    f"courses/{course_dir.name}/videos/{video_filename}",
                    local_disk_path=course_dir / "videos" / video_filename,
                )

            transcript_available = canonical_unit is not None and _resolve_transcript_available(
                canonical_unit.transcript_path
            )
            slides_available = bool(
                lecture_num and lecture_num in _available_slide_lectures_for(course_slug)
            )

            runtime_lecture_id = build_course_runtime_lecture_id(
                course_slug=course_slug,
                lecture_order=lecture_num,
                explicit_lecture_id=canonical_unit.lecture_id
                if canonical_unit is not None
                else None,
                video_filename=video_filename,
            )
            tutor_enabled = video_url is not None and runtime_lecture_id is not None

            tutor_bridge = build_tutor_bridge_payload(
                tutor_enabled=tutor_enabled,
                unit_id=str(unit.id),
                legacy_lecture_id=runtime_lecture_id,
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
                    "lecture_title": canonical_unit.lecture_title
                    if canonical_unit is not None
                    else section.title,
                    "lecture_order": lecture_num,
                    "start_seconds": content_ref.get("start_s") if content_ref else None,
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


def _format_hms(seconds: int | float | None) -> str:
    s = int(seconds or 0)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


async def get_lecture_toc(course_slug: str, lecture_order: int) -> dict | None:
    """Build a per-lecture table-of-contents from CanonicalUnit segments.

    Returns the legacy ToC payload shape consumed by LearningUnitShell:
        {
          "lecture_title": str,
          "table_of_contents": [
              {"section_number", "timestamp", "topic_title",
               "detailed_summary", "key_takeaways": [str, ...]}
          ]
        }

    Returns None if the lecture has no canonical segments.
    """
    try:
        from sqlalchemy import func

        from src.database import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                select(CanonicalUnit).where(
                    func.lower(CanonicalUnit.course_id) == course_slug.lower(),
                    CanonicalUnit.lecture_order == lecture_order,
                )
            )
            segments = list(result.scalars().all())
    except Exception:
        return None

    if not segments:
        return None

    segments.sort(
        key=lambda u: (
            (u.content_ref or {}).get("start_s") or 0,
            u.ordering_index or 0,
        )
    )

    sections: list[dict[str, Any]] = []
    for idx, seg in enumerate(segments, start=1):
        content_ref = seg.content_ref or {}
        sections.append(
            {
                "section_number": idx,
                "timestamp": _format_hms(content_ref.get("start_s")),
                "topic_title": seg.unit_name or seg.description or "",
                "detailed_summary": seg.summary or seg.description or "",
                "key_takeaways": [
                    kp.get("text", "")
                    for kp in (seg.key_points or [])
                    if isinstance(kp, dict) and kp.get("text")
                ],
            }
        )

    return {
        "lecture_title": segments[0].lecture_title or f"Lecture {lecture_order}",
        "table_of_contents": sections,
    }
