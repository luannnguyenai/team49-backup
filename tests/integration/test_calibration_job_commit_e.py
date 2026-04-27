"""Integration tests for Commit E calibration job E2E pipeline."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import math

from src.models.calibration import CalibrationRun, ItemCalibrationHistory
from src.models.canonical import ItemCalibration, QuestionBankItem
from src.models.learning import Interaction, Session
from src.services.learning.interaction_service import record_interaction


@pytest.mark.asyncio
async def test_calibration_run_creation_and_status(db_session: AsyncSession):
    """Test creating a calibration run record."""
    run_id = f"cal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run = CalibrationRun(
        run_id=run_id,
        method="2pl",
        dataset_version=datetime.now(timezone.utc).isoformat(),
        real_response_count=0,
        synthetic_response_count=0,
        status="started",
    )
    db_session.add(run)
    await db_session.flush()

    # Verify created
    stmt = select(CalibrationRun).where(CalibrationRun.run_id == run_id)
    result = await db_session.execute(stmt)
    fetched = result.scalar_one_or_none()

    assert fetched is not None
    assert fetched.run_id == run_id
    assert fetched.method == "2pl"
    assert fetched.status == "started"
    assert fetched.active is False


@pytest.mark.asyncio
async def test_item_calibration_history_insertion(db_session: AsyncSession):
    """Test inserting calibration history records."""
    # Get or create a placement item
    stmt = select(QuestionBankItem).where(
        QuestionBankItem.phase == "placement"
    ).limit(1)
    result = await db_session.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        pytest.skip("No placement items in DB")

    run_id = f"cal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Create calibration run
    run = CalibrationRun(
        run_id=run_id,
        method="2pl",
        dataset_version=datetime.now(timezone.utc).isoformat(),
        real_response_count=100,
        synthetic_response_count=0,
        status="passed",
    )
    db_session.add(run)
    await db_session.flush()

    # Create history record
    history = ItemCalibrationHistory(
        item_id=item.item_id,
        calibration_run_id=run_id,
        difficulty_b=0.5,
        discrimination_a=1.2,
        guessing_c=0.25,
        standard_error_b=0.1,
        standard_error_a=0.15,
        standard_error_c=0.05,
        real_response_count=100,
        synthetic_response_count=0,
    )
    db_session.add(history)
    await db_session.flush()

    # Verify history record
    stmt = select(ItemCalibrationHistory).where(
        ItemCalibrationHistory.item_id == item.item_id,
        ItemCalibrationHistory.calibration_run_id == run_id,
    )
    result = await db_session.execute(stmt)
    fetched = result.scalar_one_or_none()

    assert fetched is not None
    assert fetched.difficulty_b == 0.5
    assert fetched.discrimination_a == 1.2
    assert fetched.real_response_count == 100


@pytest.mark.asyncio
async def test_item_calibration_update_from_history(db_session: AsyncSession):
    """Test updating item_calibration with parameters from history."""
    # Get or create a placement item
    stmt = select(QuestionBankItem).where(
        QuestionBankItem.phase == "placement"
    ).limit(1)
    result = await db_session.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        pytest.skip("No placement items in DB")

    # Get or create item_calibration
    stmt = select(ItemCalibration).where(ItemCalibration.item_id == item.item_id)
    result = await db_session.execute(stmt)
    ic = result.scalar_one_or_none()

    if not ic:
        ic = ItemCalibration(
            item_id=item.item_id,
            is_calibrated=False,
        )
        db_session.add(ic)
        await db_session.flush()

    run_id = f"cal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Create run and history
    run = CalibrationRun(
        run_id=run_id,
        method="2pl",
        dataset_version=datetime.now(timezone.utc).isoformat(),
        real_response_count=100,
        synthetic_response_count=0,
        status="passed",
    )
    db_session.add(run)
    await db_session.flush()

    # Update item_calibration with fitted parameters
    ic.difficulty_b = 0.5
    ic.discrimination_a = 1.2
    ic.guessing_c = 0.0
    ic.standard_error_b = 0.1
    ic.standard_error_a = 0.15
    ic.standard_error_c = 0.0
    ic.is_calibrated = True
    ic.calibration_run_id = run_id
    ic.calibration_dataset_version = run.dataset_version
    ic.real_response_count = 100
    ic.synthetic_response_count = 0
    db_session.add(ic)
    await db_session.flush()

    # Verify updated
    stmt = select(ItemCalibration).where(ItemCalibration.item_id == item.item_id)
    result = await db_session.execute(stmt)
    fetched = result.scalar_one_or_none()

    assert fetched is not None
    assert fetched.is_calibrated is True
    assert fetched.difficulty_b == 0.5
    assert fetched.discrimination_a == 1.2
    assert fetched.calibration_run_id == run_id


@pytest.mark.asyncio
async def test_calibration_run_activation_deactivation(db_session: AsyncSession):
    """Test managing active/inactive status of calibration runs."""
    run1_id = f"cal_run1_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run2_id = f"cal_run2_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Create first run (inactive)
    run1 = CalibrationRun(
        run_id=run1_id,
        method="2pl",
        dataset_version="v1",
        real_response_count=100,
        synthetic_response_count=0,
        status="passed",
        active=False,
    )
    db_session.add(run1)
    await db_session.flush()

    # Create and activate second run
    run2 = CalibrationRun(
        run_id=run2_id,
        method="2pl",
        dataset_version="v2",
        real_response_count=150,
        synthetic_response_count=0,
        status="passed",
        active=True,
    )
    db_session.add(run2)
    await db_session.commit()

    # Deactivate run2, reactivate run1
    stmt = select(CalibrationRun).where(CalibrationRun.run_id == run2_id)
    result = await db_session.execute(stmt)
    run2_fetch = result.scalar_one()
    run2_fetch.active = False
    db_session.add(run2_fetch)

    stmt = select(CalibrationRun).where(CalibrationRun.run_id == run1_id)
    result = await db_session.execute(stmt)
    run1_fetch = result.scalar_one()
    run1_fetch.active = True
    db_session.add(run1_fetch)

    await db_session.commit()

    # Verify final state
    stmt = select(CalibrationRun).where(CalibrationRun.active)
    result = await db_session.execute(stmt)
    active_runs = result.scalars().all()

    assert len(active_runs) == 1
    assert active_runs[0].run_id == run1_id


@pytest.mark.asyncio
async def test_mle_difficulty_calculation():
    """Test MLE difficulty calculation logic."""
    # Test formula: b = ln((1-p)/p) / a
    test_cases = [
        (50, 100, 0.5, 1.0, 0.0),      # p=0.5 → b=0
        (70, 100, 0.7, 1.0, -0.8473),  # p=0.7 → b≈-0.847
        (30, 100, 0.3, 1.0, 0.8473),   # p=0.3 → b≈0.847
    ]

    for n_correct, n_resp, p_expected, a, b_expected in test_cases:
        p_obs = n_correct / n_resp
        assert abs(p_obs - p_expected) < 0.001

        b_est = math.log((1.0 - p_obs) / p_obs) / a
        assert abs(b_est - b_expected) < 0.001


@pytest.mark.asyncio
async def test_calibration_run_with_different_methods(db_session: AsyncSession):
    """Test calibration runs with different IRT methods."""
    for method in ["1pl", "2pl", "3pl", "mirt"]:
        run_id = f"cal_method_{method}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        run = CalibrationRun(
            run_id=run_id,
            method=method,
            dataset_version="test",
            real_response_count=100,
            synthetic_response_count=0,
            status="passed",
        )
        db_session.add(run)

    await db_session.commit()

    # Verify all methods stored
    for method in ["1pl", "2pl", "3pl", "mirt"]:
        stmt = select(CalibrationRun).where(CalibrationRun.method == method)
        result = await db_session.execute(stmt)
        runs = result.scalars().all()
        assert any(r.method == method for r in runs)
