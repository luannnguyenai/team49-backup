"""
services/course_entry_service.py
--------------------------------
Start-learning decision logic for US2.

Decision chain (evaluated in order):
1. Course not found → None (caller returns 404)
2. Course unavailable (coming_soon / metadata_partial) → course_unavailable
3. User not authenticated → auth_required (preserves course context)
4. User not onboarded → skill_test_required (routes through onboarding)
5. User has not completed skill test → skill_test_required
6. All gates pass → learning_ready
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.exceptions import ForbiddenError, NotFoundError
from src.schemas.course import StartLearningDecisionResponse
from src.services.course_bootstrap_service import get_bootstrap_course
from src.services.learning_unit_service import get_first_unit_slug

if TYPE_CHECKING:
    from src.models.user import User


async def get_start_learning_decision(
    course_slug: str,
    *,
    user: User | None = None,
) -> StartLearningDecisionResponse | None:
    """
    Evaluate the decision chain for starting a course.

    Parameters
    ----------
    course_slug : str
        The slug of the course the learner wants to start.
    user : User | None
        The authenticated user, or None for unauthenticated visitors.

    Returns
    -------
    StartLearningDecisionResponse | None
        The decision response, or None if the course does not exist.
    """
    course_row = get_bootstrap_course(course_slug)
    if course_row is None:
        return None

    # ── Gate 1: Course availability ──────────────────────────────────────
    if course_row["status"] != "ready":
        return StartLearningDecisionResponse(
            decision="redirect",
            target=f"/courses/{course_slug}",
            reason="course_unavailable",
        )

    # ── Gate 2: Authentication ───────────────────────────────────────────
    if user is None:
        return StartLearningDecisionResponse(
            decision="redirect",
            target=f"/login?next=/courses/{course_slug}/start",
            reason="auth_required",
        )

    # ── Gate 3: Onboarding ───────────────────────────────────────────────
    if not user.is_onboarded:
        return StartLearningDecisionResponse(
            decision="redirect",
            target=f"/onboarding?next=/courses/{course_slug}/start",
            reason="skill_test_required",
        )

    # ── Gate 4: Skill test completion ────────────────────────────────────
    # Check if the user has completed at least one assessment session.
    # This uses a lightweight query helper that avoids importing the full
    # assessment service at module level.
    has_completed_skill_test = await _check_skill_test_completed(user.id)
    if not has_completed_skill_test:
        return StartLearningDecisionResponse(
            decision="redirect",
            target=f"/assessment?next=/courses/{course_slug}/start",
            reason="skill_test_required",
        )

    # ── All gates pass: learning is ready ────────────────────────────────
    first_unit_slug = get_first_unit_slug(course_slug)
    learning_target = (
        f"/courses/{course_slug}/learn/{first_unit_slug}"
        if first_unit_slug
        else f"/courses/{course_slug}"
    )
    return StartLearningDecisionResponse(
        decision="redirect",
        target=learning_target,
        reason="learning_ready",
    )


async def assert_learning_access(
    course_slug: str,
    user: User | None,
) -> None:
    """
    Enforce the same course-learning gate used by the start flow.

    This guards direct API/data access so callers cannot bypass `/start`
    by guessing canonical unit or asset URLs.
    """
    course_row = get_bootstrap_course(course_slug)
    if course_row is None:
        raise NotFoundError(f"Course '{course_slug}' not found.")

    if user is None:
        raise ForbiddenError("Authentication is required to access this learning content.")

    if course_row["status"] != "ready":
        raise ForbiddenError("This course is not available for learning yet.")

    if not user.is_onboarded:
        raise ForbiddenError("Please complete onboarding before accessing this learning content.")

    has_completed_skill_test = await _check_skill_test_completed(user.id)
    if not has_completed_skill_test:
        raise ForbiddenError("Please complete the skill assessment before accessing this learning content.")


async def _check_skill_test_completed(user_id: uuid.UUID) -> bool:
    """
    Check if the user has completed at least one assessment session.

    For the bootstrap phase (no DB), this always returns False for
    unknown users. When the database is available, it queries the
    sessions table for a completed assessment.
    """
    try:
        from src.database import async_session_factory
        from sqlalchemy import select
        from src.models.learning import Session, SessionType

        async with async_session_factory() as db:
            result = await db.execute(
                select(Session.id)
                .where(
                    Session.user_id == user_id,
                    Session.session_type == SessionType.assessment,
                    Session.completed_at.isnot(None),
                )
                .limit(1)
            )
            return result.scalar_one_or_none() is not None
    except Exception:
        # During testing or bootstrap without DB, fall back to False
        return False
