#!/usr/bin/env python3
"""
Rollback IRT Calibration — revert a calibration run to a prior state.

Usage:
    python scripts/rollback_calibration.py --to-run-id cal_20260427_120000 --dry-run
    python scripts/rollback_calibration.py --to-run-id cal_20260427_120000

Restores item_calibration parameters from item_calibration_history for the target run,
deactivates the current active run, and reactivates the target run.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.models.calibration import CalibrationRun, ItemCalibrationHistory
from src.models.canonical import ItemCalibration

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description="Rollback IRT calibration to a prior run"
    )
    parser.add_argument(
        "--to-run-id",
        type=str,
        required=True,
        help="Target calibration run ID to restore",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without committing DB changes",
    )

    args = parser.parse_args()

    # Setup DB
    settings = Settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        await rollback_calibration(
            db,
            to_run_id=args.to_run_id,
            dry_run=args.dry_run,
        )
    await engine.dispose()


async def rollback_calibration(
    db: AsyncSession,
    to_run_id: str,
    dry_run: bool = False,
) -> None:
    """
    Rollback item_calibration parameters from item_calibration_history.

    Args:
        db: AsyncSession
        to_run_id: Target calibration run ID
        dry_run: if True, print plan without committing
    """
    log.info(f"Starting rollback: to_run_id={to_run_id}, dry_run={dry_run}")

    # Fetch target run
    stmt = select(CalibrationRun).where(CalibrationRun.run_id == to_run_id)
    result = await db.execute(stmt)
    target_run = result.scalar_one_or_none()

    if not target_run:
        log.error(f"Target run not found: {to_run_id}")
        sys.exit(1)

    # Fetch history for target run
    stmt = select(ItemCalibrationHistory).where(
        ItemCalibrationHistory.calibration_run_id == to_run_id
    )
    result = await db.execute(stmt)
    history_rows = result.scalars().all()

    if not history_rows:
        log.warning(f"No history found for run {to_run_id}")
        return

    log.info(f"Found {len(history_rows)} history entries for run {to_run_id}")

    # Fetch current active run
    stmt = select(CalibrationRun).where(CalibrationRun.active)
    result = await db.execute(stmt)
    current_run = result.scalar_one_or_none()

    if not current_run:
        log.warning("No active run found; skipping deactivation")
        current_run = None

    if dry_run:
        log.info("=== DRY-RUN: Would perform the following updates ===")
        log.info(f"Restore {len(history_rows)} items from run {to_run_id}")
        for h in history_rows[:5]:
            log.info(f"  item_id={h.item_id} b={h.difficulty_b} a={h.discrimination_a}")
        if len(history_rows) > 5:
            log.info(f"  ... and {len(history_rows) - 5} more items")
        if current_run:
            log.info(f"Deactivate run {current_run.run_id}")
        log.info(f"Activate run {to_run_id}")
        return

    # Restore parameters from history to item_calibration
    for history in history_rows:
        stmt = select(ItemCalibration).where(
            ItemCalibration.item_id == history.item_id
        )
        result = await db.execute(stmt)
        ic = result.scalar_one_or_none()

        if ic:
            ic.difficulty_b = history.difficulty_b
            ic.discrimination_a = history.discrimination_a
            ic.guessing_c = history.guessing_c
            ic.standard_error_b = history.standard_error_b
            ic.standard_error_a = history.standard_error_a
            ic.standard_error_c = history.standard_error_c
            ic.is_calibrated = True
            ic.calibration_run_id = history.calibration_run_id
            ic.calibration_dataset_version = target_run.dataset_version
            ic.real_response_count = history.real_response_count
            ic.synthetic_response_count = history.synthetic_response_count
            db.add(ic)

    await db.flush()
    log.info(f"Restored {len(history_rows)} items from history")

    # Manage run status
    if current_run:
        current_run.active = False
        db.add(current_run)

    target_run.active = True
    db.add(target_run)

    await db.commit()

    log.info(f"Rollback complete: restored run {to_run_id}, active=true")


if __name__ == "__main__":
    asyncio.run(main())
