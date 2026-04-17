"""
constants.py
------------
Centralized configuration constants for the AI Adaptive Learning Platform.
Single source of truth — import từ đây, KHÔNG khai báo lại ở service files.
"""
from src.models.content import DifficultyBucket, BloomLevel

# ---------------------------------------------------------------------------
# Question selection slots per session type
# ---------------------------------------------------------------------------

QUIZ_DIFFICULTY_SLOTS: list[tuple[DifficultyBucket, int]] = [
    (DifficultyBucket.easy,   3),
    (DifficultyBucket.medium, 4),
    (DifficultyBucket.hard,   3),
]  # Total: 10 questions per topic

MODULE_TEST_SLOTS: list[tuple[DifficultyBucket, int]] = [
    (DifficultyBucket.easy,   2),
    (DifficultyBucket.medium, 1),
    (DifficultyBucket.hard,   2),
]  # Total: 5 questions per topic

ASSESSMENT_BLOOM_SLOTS: list[tuple[list[BloomLevel], int]] = [
    ([BloomLevel.remember],                     1),
    ([BloomLevel.understand, BloomLevel.apply], 2),
    ([BloomLevel.analyze],                      2),
]  # Total: 5 questions per topic

# ---------------------------------------------------------------------------
# IRT 2PL (Item Response Theory — 2 Parameter Logistic Model)
# ---------------------------------------------------------------------------

IRT_DEFAULT_DISCRIMINATION: float = 1.0
IRT_BUCKET_DIFFICULTY: dict[str, float] = {
    "easy":   -1.0,   # σ ≈ -1 SD below mean ability
    "medium":  0.0,   # σ = 0 (average)
    "hard":    1.0,   # σ ≈ +1 SD above mean ability
}
IRT_CANDIDATE_MULTIPLIER: int = 5  # Fetch N×slots candidates, rank by info

# ---------------------------------------------------------------------------
# Mastery evaluation (BKT + EMA)
# ---------------------------------------------------------------------------

BLOOM_POINTS: dict[BloomLevel, int] = {
    BloomLevel.remember:   1,
    BloomLevel.understand: 2,
    BloomLevel.apply:      2,
    BloomLevel.analyze:    3,
}

QUIZ_EMA_ALPHA: float = 0.7  # new = old * (1 - alpha) + quiz_score * alpha

MASTERY_THRESHOLDS: dict[str, float] = {
    "novice":     25.0,   # 0–25%
    "developing": 50.0,   # 26–50%
    "proficient": 75.0,   # 51–75%
    # mastered: > 75%
}

# ---------------------------------------------------------------------------
# Session history
# ---------------------------------------------------------------------------

RECENT_ASSESSMENT_LOOKBACK: int = 2  # Last N assessment sessions excluded from quiz
