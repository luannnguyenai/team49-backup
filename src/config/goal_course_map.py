# src/config/goal_course_map.py
# Static mapping: onboarding goal_id → list of canonical course_ids used by planner.
from __future__ import annotations

GOAL_COURSE_MAP: dict[str, list[str]] = {
    "computer_vision": ["cs231n"],
    "nlp": ["cs224n"],
    "deep_learning": ["cs230"],
}

GOAL_LABELS: dict[str, str] = {
    "computer_vision": "Computer Vision (CS231n)",
    "nlp": "Natural Language Processing (CS224n)",
    "deep_learning": "Deep Learning (CS230)",
}

VALID_GOAL_IDS: frozenset[str] = frozenset(GOAL_COURSE_MAP.keys())
