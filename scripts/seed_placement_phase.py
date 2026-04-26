"""
Tag question_bank items that have item_calibration records for cs231n / cs224n / cs230
with phase='placement_assessment' in item_phase_map.

Idempotent: uses INSERT ... ON CONFLICT DO NOTHING.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/seed_placement_phase.py
    PYTHONPATH=. .venv/bin/python scripts/seed_placement_phase.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text  # noqa: E402

from src.database import async_session  # noqa: E402

# Courses eligible for placement assessment tagging.
PLACEMENT_COURSES = {"cs231n", "cs224n", "cs230"}

PHASE = "placement_assessment"

# Items already tagged with other phases inherit course_id/lecture_id/unit_id
# from their existing item_phase_map row.  For items not yet in any phase map,
# we pull metadata directly from question_bank.
_INSERT_SQL = text(
    """
    INSERT INTO item_phase_map
        (item_id, phase, course_id, lecture_id, unit_id,
         suitability_score, phase_multiplier, selection_priority, phase_rationale,
         created_at, updated_at)
    SELECT
        qb.item_id,
        :phase,
        qb.course_id,
        qb.lecture_id,
        qb.unit_id,
        1.0,        -- suitability_score
        1.0,        -- phase_multiplier
        NULL,       -- selection_priority
        'auto-seeded: calibrated item in placement-eligible course',
        NOW(),
        NOW()
    FROM question_bank qb
    JOIN item_calibration ic ON ic.item_id = qb.item_id
    WHERE qb.course_id = ANY(:courses)
    ON CONFLICT (item_id, phase) DO NOTHING
    RETURNING item_id
    """
)

_COUNT_SQL = text(
    """
    SELECT COUNT(*) AS n
    FROM item_phase_map
    WHERE phase = :phase
      AND course_id = ANY(:courses)
    """
)


async def seed(dry_run: bool = False) -> None:
    async with async_session() as session:
        # Count before
        row = (await session.execute(_COUNT_SQL, {"phase": PHASE, "courses": list(PLACEMENT_COURSES)})).one()
        before = row.n
        print(f"[seed_placement_phase] existing rows: {before}")

        if dry_run:
            # Simulate: count eligible items not yet tagged
            eligible = await session.execute(
                text(
                    """
                    SELECT COUNT(*) AS n
                    FROM question_bank qb
                    JOIN item_calibration ic ON ic.item_id = qb.item_id
                    WHERE qb.course_id = ANY(:courses)
                      AND NOT EXISTS (
                          SELECT 1 FROM item_phase_map ipm
                          WHERE ipm.item_id = qb.item_id AND ipm.phase = :phase
                      )
                    """
                ),
                {"courses": list(PLACEMENT_COURSES), "phase": PHASE},
            )
            n = eligible.scalar()
            print(f"[dry-run] would tag {n} items with phase='{PHASE}'")
            return

        result = await session.execute(
            _INSERT_SQL,
            {"phase": PHASE, "courses": list(PLACEMENT_COURSES)},
        )
        inserted = len(result.fetchall())
        await session.commit()

        row = (await session.execute(_COUNT_SQL, {"phase": PHASE, "courses": list(PLACEMENT_COURSES)})).one()
        after = row.n
        print(
            f"[seed_placement_phase] inserted={inserted}  total_after={after}  "
            f"(skipped_existing={after - before - inserted})"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed placement_assessment phase tags")
    parser.add_argument("--dry-run", action="store_true", help="Count eligible items without writing")
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
