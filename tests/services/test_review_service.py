from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from src.services.review_service import pick_review_kp_ids


def test_pick_review_kp_ids_prioritizes_weak_and_stale_mastery():
    now = datetime(2026, 4, 24, tzinfo=UTC)
    mastery_by_kp = {
        "kp_strong_fresh": SimpleNamespace(
            mastery_mean_cached=0.9,
            updated_at=now - timedelta(days=1),
        ),
        "kp_weak": SimpleNamespace(
            mastery_mean_cached=0.42,
            updated_at=now - timedelta(days=1),
        ),
        "kp_stale": SimpleNamespace(
            mastery_mean_cached=0.88,
            updated_at=now - timedelta(days=21),
        ),
    }

    assert pick_review_kp_ids(
        ["kp_strong_fresh", "kp_weak", "kp_stale"],
        mastery_by_kp,
        now=now,
    ) == ["kp_weak", "kp_stale"]
