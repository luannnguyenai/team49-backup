import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.services.placement.strategies import STRATEGY_REGISTRY, PlacementStrategy

log = logging.getLogger(__name__)

# Ensure strategies are registered on import
from src.services.placement.strategies.legacy_selector import LegacySelectorStrategy  # noqa: F401, E402


def get_strategy(
    *,
    mode: str | None = None,
    unit_ids: list[str] | None = None,
) -> PlacementStrategy:
    """
    Get placement strategy based on mode or auto-detect via unit calibration status.

    Args:
        mode: Override mode from settings ('random_uniform' | 'spread_by_prior' | 'irt_adaptive' | 'auto').
        unit_ids: Unit IDs for auto-promotion decision (unused in Commit A, populated in Commit C).

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
        # Commit C: implement auto-promotion; default to spread_by_prior for now
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
    Stub for now; fully implemented in Commit C.

    Returns:
        { unit_id: { is_calibrated_ratio, median_se_b, avg_responses_per_item, has_active_calibration_run } }
    """
    return {}
