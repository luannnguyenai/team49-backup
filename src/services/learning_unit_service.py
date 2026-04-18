"""
services/learning_unit_service.py
---------------------------------
Learning-unit payloads for the canonical lecture experience.

US3: Maps legacy lecture data (from `store.py` Lecture model and data/CS231n/)
to the canonical `LearningUnitResponse` shape defined by the course-platform
contract.

The mapping uses bootstrap JSON (`data/course_bootstrap/units.json`) to
connect unit slugs to legacy lecture IDs and video files.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.schemas.course import (
    LearningUnitContentPayload,
    LearningUnitCourseSummary,
    LearningUnitResponse,
    LearningUnitSummary,
    TutorContextPayload,
)
from src.services.course_bootstrap_service import get_bootstrap_course

# ---------------------------------------------------------------------------
# Bootstrap unit data
# ---------------------------------------------------------------------------

UNITS_FILE = Path("data/course_bootstrap/units.json")


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_bootstrap_units() -> list[dict[str, Any]]:
    """Load the learning units bootstrap data."""
    if not UNITS_FILE.exists():
        return []
    return _read_json(UNITS_FILE)


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


def get_unit_by_legacy_lecture_id(lecture_id: str) -> dict[str, Any] | None:
    """Find a learning unit by its legacy lecture ID."""
    for unit in load_bootstrap_units():
        if unit.get("legacy_lecture_id") == lecture_id:
            return unit
    return None


def list_course_units(course_slug: str) -> list[dict[str, Any]]:
    """List all learning units for a course, ordered by order_index."""
    units = [u for u in load_bootstrap_units() if u["course_slug"] == course_slug]
    units.sort(key=lambda u: u.get("order_index", 0))
    return units


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
        # The video files are served from the /data static mount
        video_path = Path(f"data/CS231n/videos/{video_filename}")
        if video_path.exists():
            video_url = f"/data/CS231n/videos/{video_filename}"

    # Check transcript and slides availability
    lecture_num = unit_row.get("order_index", 0)
    transcript_dir = Path("data/CS231n/transcripts")
    slides_dir = Path("data/CS231n/slides")
    transcript_available = transcript_dir.exists() and any(transcript_dir.iterdir()) if transcript_dir.exists() else False
    slides_available = slides_dir.exists() and any(slides_dir.iterdir()) if slides_dir.exists() else False

    # Determine if tutor should be enabled
    # Tutor is enabled when the unit is ready and has video content
    tutor_enabled = unit_row["status"] == "ready" and video_url is not None
    context_binding_id = f"ctx_{unit_row['id']}" if tutor_enabled else None

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
            enabled=tutor_enabled,
            mode="in_context" if tutor_enabled else "disabled",
            context_binding_id=context_binding_id,
        ),
    )
