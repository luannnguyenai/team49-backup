"""
services/course_entry_service.py
--------------------------------
Course entry decisions. This starts with availability gating and preserves
room for auth and onboarding gates in later tasks.
"""

from src.schemas.course import StartLearningDecisionResponse
from src.services.course_bootstrap_service import get_bootstrap_course


async def get_start_learning_decision(course_slug: str) -> StartLearningDecisionResponse | None:
    course_row = get_bootstrap_course(course_slug)
    if course_row is None:
        return None

    if course_row["status"] != "ready":
        return StartLearningDecisionResponse(
            decision="redirect",
            target=f"/courses/{course_slug}",
            reason="course_unavailable",
        )

    return StartLearningDecisionResponse(
        decision="redirect",
        target=f"/login?next=/courses/{course_slug}/start",
        reason="auth_required",
    )
