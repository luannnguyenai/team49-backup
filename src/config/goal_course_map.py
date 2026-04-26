# src/config/goal_course_map.py
# Static mapping: onboarding goal_id → list of canonical course_ids used by planner.
from __future__ import annotations

GOAL_COURSE_MAP: dict[str, list[str]] = {
    "computer_vision": ["cs231n"],
    "nlp": ["cs224n"],
    "deep_learning": ["cs230"],
}

# Human-readable labels shown in goal selection UI (no course code in title).
GOAL_LABELS: dict[str, str] = {
    "computer_vision": "Computer Vision",
    "nlp": "Natural Language Processing",
    "deep_learning": "Deep Learning",
}

# Short descriptions shown on goal cards in the onboarding wizard.
GOAL_DESCRIPTIONS: dict[str, str] = {
    "computer_vision": "Học cách máy tính 'nhìn' và hiểu ảnh",
    "nlp": "Dạy máy hiểu và sinh ngôn ngữ",
    "deep_learning": "Nền tảng deep learning, neural networks, optimization",
}

# Course code badges shown below the goal title on each card.
GOAL_COURSE_BADGES: dict[str, list[str]] = {
    "computer_vision": ["CS231n"],
    "nlp": ["CS224n"],
    "deep_learning": ["CS230"],
}

VALID_GOAL_IDS: frozenset[str] = frozenset(GOAL_COURSE_MAP.keys())
