"""
models/content.py
-----------------
Shared assessment/content enums retained after the legacy content tables were
removed.
"""

import enum


class BloomLevel(enum.StrEnum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"


class DifficultyBucket(enum.StrEnum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionStatus(enum.StrEnum):
    draft = "draft"
    active = "active"
    calibrated = "calibrated"
    retired = "retired"


class CorrectAnswer(enum.StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
