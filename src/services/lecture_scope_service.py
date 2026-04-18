from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


_SYLLABUS_PATH = Path("data/CS231n/syllabus.json")
_LECTURE_ID_PATTERN = re.compile(r"lecture[-_ ]?0*(\d+)", re.IGNORECASE)


@lru_cache(maxsize=1)
def _load_syllabus() -> dict[str, dict[str, Any]]:
    with _SYLLABUS_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    lectures = payload.get("lectures", []) if isinstance(payload, dict) else []
    by_id: dict[str, dict[str, Any]] = {}
    for lecture in lectures:
        if not isinstance(lecture, dict):
            continue
        lecture_id = lecture.get("lecture_id")
        if lecture_id:
            by_id[str(lecture_id)] = lecture
    return by_id


def _extract_lecture_number(lecture_id: str | None) -> int | None:
    if not lecture_id:
        return None

    match = _LECTURE_ID_PATTERN.search(lecture_id)
    if not match:
        return None
    return int(match.group(1))


def get_lecture_scope_metadata(lecture_id: str | None) -> dict[str, Any] | None:
    if not lecture_id:
        return None

    by_id = _load_syllabus()
    if lecture_id in by_id:
        return by_id[lecture_id]

    lecture_number = _extract_lecture_number(lecture_id)
    if lecture_number is None:
        return None

    normalized_id = f"cs231n-lecture-{lecture_number}"
    return by_id.get(normalized_id)
