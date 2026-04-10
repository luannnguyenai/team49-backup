"""
services/mastery_evaluator.py
------------------------------
Pure-computation module: no I/O, no DB calls.

Responsibility:
  Given a list of QuestionResult objects for one topic, compute the
  mastery score, mastery level, bloom breakdown, weak KCs, and
  detected misconceptions.

Point weights (mirrors the assessment design):
  remember  → 1 pt
  understand → 2 pts
  apply      → 2 pts
  analyze    → 3 pts

Mastery classification:
  0  – 25  → novice
  26 – 50  → developing
  51 – 75  → proficient
  76 – 100 → mastered
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from src.models.content import BloomLevel, CorrectAnswer
from src.models.learning import MasteryLevel, SelectedAnswer


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BLOOM_POINTS: dict[BloomLevel, int] = {
    BloomLevel.remember: 1,
    BloomLevel.understand: 2,
    BloomLevel.apply: 2,
    BloomLevel.analyze: 3,
}

_BLOOM_ORDER: list[BloomLevel] = [
    BloomLevel.remember,
    BloomLevel.understand,
    BloomLevel.apply,
    BloomLevel.analyze,
]


# ---------------------------------------------------------------------------
# Data transfer objects (pure Python, no SQLAlchemy)
# ---------------------------------------------------------------------------

@dataclass
class QuestionResult:
    """Carries everything the evaluator needs about a single answered question."""

    question_id: uuid.UUID
    topic_id: uuid.UUID
    bloom_level: BloomLevel
    correct_answer: CorrectAnswer
    selected_answer: SelectedAnswer | None
    is_correct: bool
    kc_ids: list[str]           # UUID strings from Question.kc_ids JSON column
    misconception_a_id: str | None
    misconception_b_id: str | None
    misconception_c_id: str | None
    misconception_d_id: str | None


@dataclass
class TopicMasteryResult:
    """Computed mastery result for a single topic."""

    topic_id: uuid.UUID
    earned_points: int
    max_points: int
    score_percent: float            # 0.0 – 100.0
    mastery_level: MasteryLevel
    mastery_probability: float      # 0.0 – 1.0  (score_percent / 100)
    bloom_breakdown: dict[str, str] # {"remember": "1/1", "analyze": "0/2"}
    weak_kc_ids: list[str]          # KC UUIDs/slugs linked to wrong answers
    misconceptions_detected: list[str]
    bloom_max_achieved: str | None  # highest Bloom level answered correctly


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_mastery(score_percent: float) -> MasteryLevel:
    """Map a 0–100 score_percent to its MasteryLevel bucket."""
    if score_percent <= 25:
        return MasteryLevel.novice
    elif score_percent <= 50:
        return MasteryLevel.developing
    elif score_percent <= 75:
        return MasteryLevel.proficient
    else:
        return MasteryLevel.mastered


def evaluate_topic(results: list[QuestionResult]) -> TopicMasteryResult:
    """
    Compute the full mastery result for one topic.

    Args:
        results: All QuestionResult objects for a single topic_id.
                 Must not be empty.

    Returns:
        TopicMasteryResult with score, level, bloom breakdown,
        weak KC IDs, and detected misconceptions.
    """
    if not results:
        raise ValueError("evaluate_topic requires at least one QuestionResult")

    topic_id = results[0].topic_id

    # Accumulators
    bloom_correct: dict[BloomLevel, int] = {b: 0 for b in BloomLevel}
    bloom_total: dict[BloomLevel, int] = {b: 0 for b in BloomLevel}
    earned = 0
    max_pts = 0
    weak_kc_ids: set[str] = set()
    misconceptions: set[str] = set()
    bloom_max_achieved: BloomLevel | None = None

    for r in results:
        pts = BLOOM_POINTS[r.bloom_level]
        bloom_total[r.bloom_level] += 1
        max_pts += pts

        if r.is_correct:
            earned += pts
            bloom_correct[r.bloom_level] += 1
            # Track highest Bloom level answered correctly
            if bloom_max_achieved is None or (
                _BLOOM_ORDER.index(r.bloom_level)
                > _BLOOM_ORDER.index(bloom_max_achieved)
            ):
                bloom_max_achieved = r.bloom_level
        else:
            # All KCs on a wrong-answer question are considered weak
            for kc_id in r.kc_ids:
                if kc_id:
                    weak_kc_ids.add(kc_id)

            # Misconception: wrong answer option → misconception field mapping
            if r.selected_answer is not None:
                _misc_map: dict[SelectedAnswer, str | None] = {
                    SelectedAnswer.A: r.misconception_a_id,
                    SelectedAnswer.B: r.misconception_b_id,
                    SelectedAnswer.C: r.misconception_c_id,
                    SelectedAnswer.D: r.misconception_d_id,
                }
                misc_id = _misc_map.get(r.selected_answer)
                if misc_id:
                    misconceptions.add(misc_id)

    score_percent = round(earned / max_pts * 100, 1) if max_pts > 0 else 0.0
    mastery_level = classify_mastery(score_percent)

    # "correct/total" string for every Bloom level (including those with 0 questions)
    bloom_breakdown: dict[str, str] = {
        b.value: f"{bloom_correct[b]}/{bloom_total[b]}"
        for b in BloomLevel
    }

    return TopicMasteryResult(
        topic_id=topic_id,
        earned_points=earned,
        max_points=max_pts,
        score_percent=score_percent,
        mastery_level=mastery_level,
        mastery_probability=round(earned / max_pts, 4) if max_pts > 0 else 0.0,
        bloom_breakdown=bloom_breakdown,
        weak_kc_ids=list(weak_kc_ids),
        misconceptions_detected=list(misconceptions),
        bloom_max_achieved=bloom_max_achieved.value if bloom_max_achieved else None,
    )
