"""
services/course_bootstrap_service.py
------------------------------------
Helpers for loading course-platform bootstrap fixtures from repository data.
These files seed the canonical contracts until database-backed ingestion lands.
"""

import json
from functools import lru_cache
from typing import Any

from src.data_paths import COURSES_FILE, OVERVIEWS_FILE


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_bootstrap_courses() -> list[dict[str, Any]]:
    return _read_json(COURSES_FILE)


@lru_cache(maxsize=1)
def load_bootstrap_overviews() -> dict[str, dict[str, Any]]:
    overview_rows = _read_json(OVERVIEWS_FILE)
    return {row["course_slug"]: row for row in overview_rows}


def get_bootstrap_course(course_slug: str) -> dict[str, Any] | None:
    for row in load_bootstrap_courses():
        if row["slug"] == course_slug:
            return row
    return None


def get_bootstrap_overview(course_slug: str) -> dict[str, Any] | None:
    return load_bootstrap_overviews().get(course_slug)
