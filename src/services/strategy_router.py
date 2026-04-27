"""
services/strategy_router.py
----------------------------
Picks the item-selection strategy based on calibration data coverage.

Coverage = items_with_difficulty_prior_not_null / total_items_in_all_unit_pools

  Coverage < 0.5  → PerUnitRandomUniformStrategy  (Mode 1 fallback)
  Coverage ≥ 0.5  → PerUnitSpreadByPriorStrategy   (Mode 2 default)
  Pool empty      → PerUnitRandomUniformStrategy    (Mode 1 fallback)
"""
from __future__ import annotations

from src.services.assessment_strategies import (
    PerUnitRandomUniformStrategy,
    PerUnitSpreadByPriorStrategy,
    UnitPools,
)


def pick_strategy(
    unit_pools: UnitPools,
) -> PerUnitRandomUniformStrategy | PerUnitSpreadByPriorStrategy:
    total = sum(len(pairs) for pairs in unit_pools.values())
    if total == 0:
        return PerUnitRandomUniformStrategy()

    with_prior = sum(
        1
        for pairs in unit_pools.values()
        for _, d in pairs
        if d is not None
    )
    coverage = with_prior / total

    if coverage >= 0.5:
        return PerUnitSpreadByPriorStrategy()
    return PerUnitRandomUniformStrategy()
