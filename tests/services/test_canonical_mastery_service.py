from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.services.canonical_mastery_service import (
    ItemScoringParameters,
    calculate_mastery_update,
    decay_mastery_for_read,
    estimate_mastery_lcb,
    estimate_mastery_lcb_on_read,
    estimate_mastery_mean,
    estimate_mastery_mean_on_read,
    next_theta_mu,
    update_kp_mastery_from_item,
)


def test_estimate_mastery_mean_increases_with_theta():
    assert estimate_mastery_mean(theta_mu=1.0, theta_sigma=0.5) > estimate_mastery_mean(
        theta_mu=-1.0,
        theta_sigma=0.5,
    )


def test_estimate_mastery_lcb_is_conservative_vs_mean():
    mean = estimate_mastery_mean(theta_mu=1.0, theta_sigma=0.5)
    lcb = estimate_mastery_lcb(theta_mu=1.0, theta_sigma=0.5)

    assert 0.0 <= lcb <= mean <= 1.0


def test_calculate_mastery_update_uses_item_priors_for_evidence_strength():
    hard_item = ItemScoringParameters(difficulty=1.2, discrimination=1.4, guessing=0.2)
    easy_item = ItemScoringParameters(difficulty=-1.2, discrimination=1.4, guessing=0.2)

    hard_correct = calculate_mastery_update(
        theta_mu=0.0,
        theta_sigma=1.0,
        is_correct=True,
        item_weight=0.7,
        item_parameters=hard_item,
    )
    easy_correct = calculate_mastery_update(
        theta_mu=0.0,
        theta_sigma=1.0,
        is_correct=True,
        item_weight=0.7,
        item_parameters=easy_item,
    )
    easy_wrong = calculate_mastery_update(
        theta_mu=0.0,
        theta_sigma=1.0,
        is_correct=False,
        item_weight=0.7,
        item_parameters=easy_item,
    )

    assert hard_correct.theta_mu > easy_correct.theta_mu
    assert easy_wrong.theta_mu < -0.2
    assert hard_correct.theta_sigma < 1.0
    assert easy_wrong.mastery_mean_cached == pytest.approx(
        estimate_mastery_mean(easy_wrong.theta_mu, easy_wrong.theta_sigma)
    )


def test_next_theta_mu_rewards_correct_answer():
    assert next_theta_mu(current_theta=0.0, is_correct=True, item_weight=0.7) > 0.0
    assert next_theta_mu(current_theta=0.0, is_correct=False, item_weight=0.7) < 0.0


def test_decay_mastery_for_read_inflates_uncertainty_without_overwriting_raw_state():
    now = datetime(2026, 4, 24, tzinfo=UTC)

    fresh_mu, fresh_sigma = decay_mastery_for_read(
        theta_mu=1.0,
        theta_sigma=0.4,
        last_updated=now - timedelta(hours=12),
        now=now,
    )
    stale_mu, stale_sigma = decay_mastery_for_read(
        theta_mu=1.0,
        theta_sigma=0.4,
        last_updated=now - timedelta(days=21),
        now=now,
    )

    assert fresh_mu == 1.0
    assert fresh_sigma == 0.4
    assert stale_mu == 1.0
    assert stale_sigma > fresh_sigma
    assert estimate_mastery_mean(stale_mu, stale_sigma) < estimate_mastery_mean(fresh_mu, fresh_sigma)


def test_estimate_mastery_mean_on_read_uses_updated_at_staleness():
    now = datetime(2026, 4, 24, tzinfo=UTC)
    mastery = Mock(theta_mu=1.0, theta_sigma=0.4, updated_at=now - timedelta(days=21))

    assert estimate_mastery_mean_on_read(mastery, now=now) < estimate_mastery_mean(
        theta_mu=1.0,
        theta_sigma=0.4,
    )


def test_estimate_mastery_lcb_on_read_combines_staleness_and_conservative_bound():
    now = datetime(2026, 4, 24, tzinfo=UTC)
    mastery = Mock(theta_mu=1.0, theta_sigma=0.4, updated_at=now - timedelta(days=21))

    assert estimate_mastery_lcb_on_read(mastery, now=now) < estimate_mastery_mean_on_read(
        mastery,
        now=now,
    )


@pytest.mark.asyncio
async def test_update_kp_mastery_from_item_updates_each_kp(monkeypatch):
    session = AsyncMock()
    mapping = Mock(kp_id="kp_attention", weight=0.7)
    mapping_result = Mock()
    mapping_result.scalars.return_value.all.return_value = [mapping]
    calibration = Mock(
        is_calibrated=False,
        difficulty_prior=1.0,
        discrimination_prior=1.2,
        guessing_prior=0.2,
    )
    calibration_result = Mock()
    calibration_result.scalar_one_or_none.return_value = calibration
    session.execute.side_effect = [mapping_result, calibration_result]

    upserts = []

    class FakeRepo:
        def __init__(self, db):
            self.db = db

        async def get_by_user_kp(self, user_id, kp_id):
            return None

        async def upsert(self, user_id, kp_id, **mastery_data):
            upserts.append((user_id, kp_id, mastery_data))

    monkeypatch.setattr("src.services.canonical_mastery_service.LearnerMasteryKPRepository", FakeRepo)
    user_id = uuid4()

    updated = await update_kp_mastery_from_item(
        session,
        user_id=user_id,
        canonical_item_id="item-1",
        is_correct=True,
    )

    assert updated == ["kp_attention"]
    assert upserts[0][0] == user_id
    assert upserts[0][1] == "kp_attention"
    assert upserts[0][2]["n_items_observed"] == 1
    assert upserts[0][2]["updated_by"] == "canonical_assessor_2pl_lite_prior"
