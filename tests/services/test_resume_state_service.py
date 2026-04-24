from datetime import UTC, datetime, timedelta

from src.services.resume_state_service import classify_quiz_abandon_policy, classify_resume_route


def test_classify_quiz_abandon_policy_keeps_recent_partial_quiz_resumable():
    now = datetime(2026, 4, 24, 12, tzinfo=UTC)

    assert classify_quiz_abandon_policy(last_activity=now - timedelta(hours=23), now=now) == "finish_remaining"
    assert classify_quiz_abandon_policy(last_activity=now - timedelta(hours=24), now=now) == "restart_fresh"


def test_classify_resume_route_uses_staleness_thresholds():
    now = datetime(2026, 4, 24, 12, tzinfo=UTC)

    assert classify_resume_route(last_activity=now - timedelta(hours=4), now=now) == "seamless_resume"
    assert classify_resume_route(last_activity=now - timedelta(days=3), now=now) == "welcome_back"
    assert classify_resume_route(last_activity=now - timedelta(days=14), now=now) == "quick_review_check"
    assert classify_resume_route(last_activity=now - timedelta(days=45), now=now) == "placement_lite"
