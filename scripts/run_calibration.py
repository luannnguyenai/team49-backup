#!/usr/bin/env python3
"""
IRT Calibration Job — fit 2PL/3PL parameters from response data.

Usage:
    python scripts/run_calibration.py --method 2pl --min-responses 20 --since 2026-04-20 --dry-run
    python scripts/run_calibration.py --method 3pl --min-responses 50

Note: Commit E scaffold — uses simple per-item marginal MLE (not full IRT).
For production, integrate py-irt or other advanced calibration library.
"""

import argparse
import asyncio
import logging
import math
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.models.calibration import CalibrationRun, ItemCalibrationHistory
from src.models.canonical import ItemCalibration, QuestionBankItem
from src.models.learning import Interaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description="IRT calibration job: fit parameters from response data"
    )
    parser.add_argument(
        "--method",
        choices=["2pl", "3pl"],
        default="2pl",
        help="IRT model: 2pl (logistic) or 3pl (with guessing)",
    )
    parser.add_argument(
        "--min-responses",
        type=int,
        default=20,
        help="Minimum responses per item to include in calibration",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="ISO date to filter responses (YYYY-MM-DD); default: all history",
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
        await run_calibration(
            db,
            method=args.method,
            min_responses=args.min_responses,
            since=args.since,
            dry_run=args.dry_run,
        )
    await engine.dispose()


async def run_calibration(
    db: AsyncSession,
    method: str = "2pl",
    min_responses: int = 20,
    since: str | None = None,
    dry_run: bool = False,
) -> None:
    """
    Fit IRT parameters from interaction response data.

    Args:
        db: AsyncSession
        method: "2pl" or "3pl"
        min_responses: minimum responses per item to calibrate
        since: ISO date filter (YYYY-MM-DD)
        dry_run: if True, print plan without committing
    """
    log.info(f"Starting calibration: method={method}, min_responses={min_responses}, dry_run={dry_run}")

    run_id = f"cal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    dataset_version = datetime.now(timezone.utc).isoformat()

    # Create calibration run record
    cal_run = CalibrationRun(
        run_id=run_id,
        method=method,
        dataset_version=dataset_version,
        real_response_count=0,  # Will update below
        synthetic_response_count=0,
        status="started",
    )
    db.add(cal_run)
    await db.flush()

    log.info(f"Created calibration run: {run_id}")

    # Query response data
    since_filter = ""
    if since:
        try:
            since_date = datetime.fromisoformat(since)
            since_filter = f" AND interactions.timestamp >= '{since_date.isoformat()}'"
        except ValueError:
            log.warning(f"Invalid since date: {since}; ignoring filter")

    # Per-item response aggregation query
    query_text = text(f"""
        SELECT
            interactions.canonical_item_id,
            COUNT(*) AS n_responses,
            SUM(CASE WHEN interactions.is_correct THEN 1 ELSE 0 END) AS n_correct
        FROM interactions
        WHERE interactions.canonical_item_id IS NOT NULL
        {since_filter}
        GROUP BY interactions.canonical_item_id
        HAVING COUNT(*) >= :min_responses
        ORDER BY interactions.canonical_item_id
    """)

    result = await db.execute(query_text, {"min_responses": min_responses})
    rows = result.fetchall()

    log.info(f"Found {len(rows)} items with >= {min_responses} responses")

    if not rows:
        log.warning("No items meet minimum response threshold; skipping calibration")
        cal_run.status = "failed"
        await db.commit()
        return

    # Fit parameters per item (Commit E scaffold: simple MLE)
    fitted_items = []
    for item_id, n_resp, n_correct in rows:
        if n_resp < min_responses:
            continue

        # Simple MLE: difficulty b from observed proportion
        # p = n_correct / n_resp ≈ P(theta=0)
        # For 2PL: P(0) = 1/(1+exp(-a*-b)) = 1/(1+exp(a*b))
        # Solve for b: exp(a*b) = (1-p)/p → b = ln((1-p)/p) / a
        p_obs = n_correct / n_resp
        a_est = 1.0  # Default discrimination (can tune later)

        # Avoid log(0) or log(inf)
        if p_obs <= 0.01:
            p_obs = 0.01
        if p_obs >= 0.99:
            p_obs = 0.99

        b_est = math.log((1.0 - p_obs) / p_obs) / a_est
        c_est = 0.0 if method == "2pl" else 0.25

        # Standard errors (Commit E scaffold: placeholder)
        se_b = math.sqrt(1.0 / (a_est ** 2 * n_resp * p_obs * (1.0 - p_obs)))
        se_a = math.sqrt(1.0 / (n_resp * p_obs * (1.0 - p_obs)))  # Placeholder
        se_c = 0.0 if method == "2pl" else 0.05  # Placeholder

        fitted_items.append(
            {
                "item_id": item_id,
                "difficulty_b": round(b_est, 4),
                "discrimination_a": round(a_est, 4),
                "guessing_c": round(c_est, 4),
                "standard_error_b": round(se_b, 4),
                "standard_error_a": round(se_a, 4),
                "standard_error_c": round(se_c, 4),
                "n_responses": n_resp,
            }
        )

    log.info(f"Fitted {len(fitted_items)} items")

    if dry_run:
        log.info("=== DRY-RUN: Would perform the following updates ===")
        for item_fit in fitted_items[:5]:  # Show first 5
            log.info(f"  item_id={item_fit['item_id']} b={item_fit['difficulty_b']} "
                    f"se_b={item_fit['standard_error_b']} n={item_fit['n_responses']}")
        if len(fitted_items) > 5:
            log.info(f"  ... and {len(fitted_items) - 5} more items")
        log.info(f"Total items to fit: {len(fitted_items)}")
        return

    # Write to item_calibration_history (audit trail)
    for item_fit in fitted_items:
        history = ItemCalibrationHistory(
            item_id=item_fit["item_id"],
            calibration_run_id=run_id,
            difficulty_b=item_fit["difficulty_b"],
            discrimination_a=item_fit["discrimination_a"],
            guessing_c=item_fit["guessing_c"],
            standard_error_b=item_fit["standard_error_b"],
            standard_error_a=item_fit["standard_error_a"],
            standard_error_c=item_fit["standard_error_c"],
            real_response_count=item_fit["n_responses"],
            synthetic_response_count=0,
        )
        db.add(history)

    await db.flush()
    log.info(f"Inserted {len(fitted_items)} rows into item_calibration_history")

    # Update item_calibration with fitted parameters
    for item_fit in fitted_items:
        stmt = select(ItemCalibration).where(ItemCalibration.item_id == item_fit["item_id"])
        result = await db.execute(stmt)
        ic = result.scalar_one_or_none()
        if ic:
            ic.difficulty_b = item_fit["difficulty_b"]
            ic.discrimination_a = item_fit["discrimination_a"]
            ic.guessing_c = item_fit["guessing_c"]
            ic.standard_error_b = item_fit["standard_error_b"]
            ic.standard_error_a = item_fit["standard_error_a"]
            ic.standard_error_c = item_fit["standard_error_c"]
            ic.is_calibrated = True
            ic.calibration_run_id = run_id
            ic.calibration_dataset_version = dataset_version
            ic.real_response_count = item_fit["n_responses"]
            db.add(ic)

    await db.flush()
    log.info(f"Updated {len(fitted_items)} rows in item_calibration")

    # Finalize calibration run
    cal_run.status = "passed"
    cal_run.finished_at = datetime.now(timezone.utc)
    cal_run.real_response_count = sum(f["n_responses"] for f in fitted_items)

    # Deactivate old runs and activate new run
    old_runs = await db.execute(select(CalibrationRun).where(CalibrationRun.active))
    for old_run in old_runs.scalars():
        old_run.active = False
        db.add(old_run)

    cal_run.active = True
    db.add(cal_run)
    await db.commit()

    log.info(f"Calibration complete: {len(fitted_items)} items fitted, run_id={run_id}, active=true")


if __name__ == "__main__":
    asyncio.run(main())
