"""
services/resume_state_service.py
--------------------------------
Pure policy helpers for abandon/resume flows.
"""

from datetime import datetime

SECONDS_PER_DAY = 24 * 60 * 60


def _age_seconds(*, last_activity: datetime, now: datetime) -> float:
    return max(0.0, (now - last_activity).total_seconds())


def classify_quiz_abandon_policy(*, last_activity: datetime, now: datetime) -> str:
    """Return how an abandoned quiz should resume."""
    if _age_seconds(last_activity=last_activity, now=now) < SECONDS_PER_DAY:
        return "finish_remaining"
    return "restart_fresh"


def classify_resume_route(*, last_activity: datetime, now: datetime) -> str:
    """Classify cross-session resume behavior by time since last activity."""
    age_days = _age_seconds(last_activity=last_activity, now=now) / SECONDS_PER_DAY
    if age_days < 1:
        return "seamless_resume"
    if age_days <= 7:
        return "welcome_back"
    if age_days <= 30:
        return "quick_review_check"
    return "placement_lite"
