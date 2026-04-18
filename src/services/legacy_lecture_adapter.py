"""
services/legacy_lecture_adapter.py
----------------------------------
Transitional boundary between the canonical course-first domain and the
legacy CS231n lecture/tutor stack.

Rules:
- Public-facing product contracts stay canonical (`Course -> LearningUnit`).
- Legacy lecture IDs are derived only for adapter use cases (video/tutor).
- New course-platform services should depend on this module instead of
  importing legacy assumptions directly.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any


def normalize_legacy_lecture_id(
    raw_lecture_id: str | None,
    order_index: int | None,
) -> str | None:
    """Normalize transitional lecture IDs to the DB format used by the tutor stack."""
    if raw_lecture_id:
        normalized = raw_lecture_id.replace("_", "-")
        normalized = re.sub(r"lecture-(0+)(\d+)", r"lecture-\2", normalized)
        return normalized

    if order_index:
        return f"cs231n-lecture-{order_index}"

    return None


def _load_bootstrap_units() -> list[dict[str, Any]]:
    with Path("data/course_bootstrap/units.json").open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def get_unit_by_legacy_lecture_id(lecture_id: str) -> dict[str, Any] | None:
    """Resolve the canonical bootstrap unit that maps to a legacy lecture ID."""
    for unit in _load_bootstrap_units():
        normalized = normalize_legacy_lecture_id(
            unit.get("legacy_lecture_id"),
            unit.get("order_index"),
        )
        if normalized == lecture_id:
            return unit
    return None


def build_tutor_bridge_payload(
    *,
    tutor_enabled: bool,
    unit_id: str,
    legacy_lecture_id: str | None,
) -> dict[str, Any]:
    """Build the transitional tutor payload that bridges canonical units to legacy lectures."""
    return {
        "enabled": tutor_enabled,
        "mode": "in_context" if tutor_enabled else "disabled",
        "context_binding_id": f"ctx_{unit_id}" if tutor_enabled else None,
        "legacy_lecture_id": legacy_lecture_id if tutor_enabled else None,
    }
