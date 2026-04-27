import logging
from typing import Any

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.canonical import ItemCalibration, QuestionBankItem
from src.models.learning import Interaction
from src.services.placement.strategies import STRATEGY_REGISTRY, PlacementStrategy

log = logging.getLogger(__name__)

# Cache for unit calibration summary (TTL 5 min — implement with Redis in production)
_CALIBRATION_SUMMARY_CACHE: dict[str, dict[str, Any]] = {}
_CALIBRATION_SUMMARY_CACHE_TTL = 300  # 5 minutes

# Ensure strategies are registered on import
from src.services.placement.strategies.legacy_selector import LegacySelectorStrategy  # noqa: F401, E402
from src.services.placement.strategies.random_uniform import RandomUniformStrategy  # noqa: F401, E402
from src.services.placement.strategies.spread_by_prior import SpreadByPriorStrategy  # noqa: F401, E402


def get_strategy(
    *,
    mode: str | None = None,
    unit_ids: list[str] | None = None,
) -> PlacementStrategy:
    """
    Get placement strategy based on mode or auto-detect via unit calibration status.

    Args:
        mode: Override mode from settings ('random_uniform' | 'spread_by_prior' | 'irt_adaptive' | 'auto').
        unit_ids: Unit IDs for auto-promotion decision (for 'auto' mode, Commit C).

    Returns:
        PlacementStrategy instance.

    Raises:
        KeyError if mode not in STRATEGY_REGISTRY.
    """
    if not STRATEGY_REGISTRY:
        raise RuntimeError("No strategies registered. Import strategies before calling get_strategy.")

    if mode is None:
        settings = Settings()
        mode = getattr(settings, "cold_start_mode", "spread_by_prior")

    if mode == "auto":
        # Commit C: auto-promotion per unit (stub; requires DB session to query)
        # Will be called from strategy selection context with unit_ids
        log.warning("'auto' mode requires unit_ids context; defaulting to spread_by_prior")
        return STRATEGY_REGISTRY.get("spread_by_prior", STRATEGY_REGISTRY["spread_by_prior"])

    strategy = STRATEGY_REGISTRY.get(mode)
    if strategy is None:
        raise KeyError(
            f"Strategy '{mode}' not found in registry. Available: {list(STRATEGY_REGISTRY.keys())}"
        )
    return strategy


async def _unit_calibration_summary(
    db: AsyncSession,
    unit_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Query calibration status per unit for auto-promotion decision (Commit C).

    Thresholds (from settings or hardcoded):
    - IRT_MIN_AVG_RESPONSES = 200 responses/item per unit
    - IRT_MIN_CALIBRATED_RATIO = 0.8 (80% items calibrated)
    - IRT_MAX_MEDIAN_SE_B = 0.3 (SE of difficulty parameter)

    Returns:
        {
            unit_id: {
                'is_calibrated_ratio': float,
                'median_se_b': float | None,
                'avg_responses_per_item': float,
                'has_active_calibration_run': bool,
                'pass_all_gates': bool
            }
        }
    """
    if not unit_ids:
        return {}

    settings = Settings()
    min_avg_responses = getattr(settings, "irt_min_avg_responses", 200)
    min_calibrated_ratio = getattr(settings, "irt_min_calibrated_ratio", 0.8)
    max_median_se_b = getattr(settings, "irt_max_median_se_b", 0.3)

    # Commit C: calibration_runs doesn't exist yet (Commit E); assume no active runs
    # Query: per unit_id, count interactions, count calibrated items, median se_b

    stmt = text("""
        WITH item_resp AS (
            SELECT canonical_item_id, COUNT(*) AS cnt
            FROM interactions
            WHERE canonical_item_id IS NOT NULL
            GROUP BY canonical_item_id
        ),
        unit_stats AS (
            SELECT
                qb.unit_id,
                COUNT(DISTINCT qb.item_id) AS total_items,
                COUNT(DISTINCT qb.item_id) FILTER (WHERE ic.is_calibrated) AS calibrated_items,
                COALESCE(AVG(item_resp.cnt), 0) AS avg_responses_per_item,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ic.standard_error_b)
                    FILTER (WHERE ic.standard_error_b IS NOT NULL) AS median_se_b
            FROM question_bank qb
            LEFT JOIN item_calibration ic ON ic.item_id = qb.item_id
            LEFT JOIN item_resp ON item_resp.canonical_item_id = qb.item_id
            WHERE qb.unit_id = ANY(:unit_ids)
            GROUP BY qb.unit_id
        )
        SELECT
            unit_id,
            total_items,
            calibrated_items,
            CASE WHEN total_items > 0
                THEN calibrated_items::float / total_items
                ELSE 0.0
            END AS is_calibrated_ratio,
            avg_responses_per_item,
            median_se_b
        FROM unit_stats
        ORDER BY unit_id
    """)

    result = await db.execute(stmt, {"unit_ids": unit_ids})
    rows = result.fetchall()

    summary = {}
    for row in rows:
        unit_id, total_items, calibrated_items, is_calibrated_ratio, avg_responses, median_se_b = row
        # Check all gates (Commit C: assume no active calibration run yet)
        pass_all_gates = (
            is_calibrated_ratio >= min_calibrated_ratio
            and avg_responses >= min_avg_responses
            and (median_se_b is None or median_se_b <= max_median_se_b)
            # Gate 4: has_active_calibration_run (Commit E adds this)
        )

        summary[unit_id] = {
            "is_calibrated_ratio": float(is_calibrated_ratio),
            "median_se_b": float(median_se_b) if median_se_b else None,
            "avg_responses_per_item": float(avg_responses),
            "has_active_calibration_run": False,  # TODO: Commit E adds calibration_runs table
            "pass_all_gates": pass_all_gates,
        }

        log.info(
            f"unit_calibration_summary: unit={unit_id} "
            f"calibrated_ratio={is_calibrated_ratio:.1%} "
            f"avg_resp={avg_responses:.0f} "
            f"median_se_b={median_se_b} "
            f"pass_gates={pass_all_gates}"
        )

    return summary
