from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_learner_mastery_kp_repo_importable():
    from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository  # noqa


@pytest.mark.asyncio
async def test_learner_mastery_kp_repo_upsert_creates_and_updates():
    from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository

    session = AsyncMock()
    created = Mock(user_id=uuid4(), kp_id="kp_attention", theta_mu=0.15)
    created.id = uuid4()
    updated = Mock(
        id=created.id,
        theta_mu=0.42,
        theta_sigma=0.5,
        mastery_mean_cached=0.67,
        n_items_observed=7,
        updated_by="assessment_v2",
    )
    result_1 = Mock()
    result_1.scalar_one.return_value = created
    result_2 = Mock()
    result_2.scalar_one.return_value = updated
    session.execute.side_effect = [result_1, result_2]

    repo = LearnerMasteryKPRepository(session)
    user_id = uuid4()

    created_row = await repo.upsert(
        user_id=user_id,
        kp_id="kp_attention",
        theta_mu=0.15,
        theta_sigma=0.8,
        mastery_mean_cached=0.56,
        n_items_observed=4,
        updated_by="assessment_v1",
    )
    assert created_row.user_id == created.user_id
    assert created_row.kp_id == "kp_attention"
    assert created_row.theta_mu == pytest.approx(0.15)

    updated_row = await repo.upsert(
        user_id=user_id,
        kp_id="kp_attention",
        theta_mu=0.42,
        theta_sigma=0.5,
        mastery_mean_cached=0.67,
        n_items_observed=7,
        updated_by="assessment_v2",
    )
    assert updated_row.id == created.id
    assert updated_row.theta_mu == pytest.approx(0.42)
    assert updated_row.theta_sigma == pytest.approx(0.5)
    assert updated_row.mastery_mean_cached == pytest.approx(0.67)
    assert updated_row.n_items_observed == 7
    assert updated_row.updated_by == "assessment_v2"
    assert session.execute.await_count == 2
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_learner_mastery_kp_repo_bulk_get_for_user():
    from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository

    session = AsyncMock()
    row_1 = Mock(kp_id="kp_cnn", mastery_mean_cached=0.53)
    row_2 = Mock(kp_id="kp_transformer", mastery_mean_cached=0.82)
    scalar_result = Mock()
    scalar_result.all.return_value = [row_1, row_2]
    result = Mock()
    result.scalars.return_value = scalar_result
    session.execute.return_value = result

    repo = LearnerMasteryKPRepository(session)

    result = await repo.bulk_get_for_user(
        user_id=uuid4(),
        kp_ids=["kp_cnn", "kp_transformer", "kp_missing"],
    )

    assert set(result.keys()) == {"kp_cnn", "kp_transformer"}
    assert result["kp_transformer"].mastery_mean_cached == pytest.approx(0.82)
