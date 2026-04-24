"""Skip/waive eligibility policy for canonical learning units."""

from __future__ import annotations


MASTERY_SKIP_LCB_THRESHOLD = 0.8
SKIP_VERIFICATION_SCORE_THRESHOLD = 80.0


def can_skip_unit(
    *,
    mastery_lcb: float | None,
    skip_quiz_score: float | None,
) -> bool:
    """Return whether a unit may be waived without forcing normal study."""
    return (
        mastery_lcb is not None
        and mastery_lcb >= MASTERY_SKIP_LCB_THRESHOLD
    ) or (
        skip_quiz_score is not None
        and skip_quiz_score >= SKIP_VERIFICATION_SCORE_THRESHOLD
    )
