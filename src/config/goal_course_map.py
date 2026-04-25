# src/config/goal_course_map.py
# Static mapping: onboarding goal_id → canonical course_id used by planner.
GOAL_COURSE_MAP: dict[str, str] = {
    "computer_vision": "cs231n",
    "nlp": "cs224n",
}

GOAL_LABELS: dict[str, str] = {
    "computer_vision": "Computer Vision (CS231n)",
    "nlp": "Natural Language Processing (CS224n)",
}

VALID_GOAL_IDS: frozenset[str] = frozenset(GOAL_COURSE_MAP.keys())
