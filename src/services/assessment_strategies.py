"""
services/assessment_strategies.py
----------------------------------
Per-unit item selection strategies for placement assessment.

Mode 1 — PerUnitRandomUniformStrategy: random uniform k items per unit pool.
Mode 2 — PerUnitSpreadByPriorStrategy: spread across difficulty_prior quantile
          bins (migrated from placement_assessment_service._bucket_select_5).

Both strategies:
  - Take unit_pools: dict mapping canonical_unit_id → list[(QuestionBankItem, difficulty_prior|None)]
  - Return a flat list of QuestionBankItems (interleaved round-robin across units for UX)
  - Edge case pool < k: take all available items (no fail, no skip)
  - Edge case pool = 0: skip that unit, log INFO warning
"""
from __future__ import annotations

import logging
import random
from collections import defaultdict

from src.models.canonical import QuestionBankItem

log = logging.getLogger(__name__)

# Type alias for unit pools
UnitPools = dict[str, list[tuple[QuestionBankItem, float | None]]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bucket_select_k(
    pairs: list[tuple[QuestionBankItem, float | None]],
    k: int,
) -> list[QuestionBankItem]:
    """
    Select k items with 1-easy / 2-medium / 2-hard distribution (for k=5).
    Falls back to fill from remaining pool when any bucket is thin.
    """
    easy = [p for p in pairs if p[1] is not None and p[1] <= -0.5]
    medium = [p for p in pairs if p[1] is None or (-0.5 < p[1] <= 0.5)]
    hard = [p for p in pairs if p[1] is not None and p[1] > 0.5]

    selected: list[tuple[QuestionBankItem, float | None]] = []
    selected += easy[:1]
    selected += medium[:2]
    selected += hard[:2]

    # Fill gaps if any bucket was thin
    selected_ids = {p[0].item_id for p in selected}
    remaining = [p for p in pairs if p[0].item_id not in selected_ids]
    target = min(k, len(pairs))
    while len(selected) < target and remaining:
        selected.append(remaining.pop(0))

    return [item for item, _ in selected[:k]]


def _round_robin_interleave(per_unit: dict[str, list[QuestionBankItem]]) -> list[QuestionBankItem]:
    """Interleave items from multiple units round-robin for better UX."""
    result: list[QuestionBankItem] = []
    queues = [items for items in per_unit.values() if items]
    if not queues:
        return result
    idx = 0
    while any(queues):
        if queues[idx % len(queues)]:
            result.append(queues[idx % len(queues)].pop(0))
        idx += 1
    return result


# ---------------------------------------------------------------------------
# Mode 1 — random uniform per unit
# ---------------------------------------------------------------------------


class PerUnitRandomUniformStrategy:
    name = "random_uniform"

    def select(self, unit_pools: UnitPools, k: int = 5) -> list[QuestionBankItem]:
        per_unit: dict[str, list[QuestionBankItem]] = {}
        for unit_id, pairs in unit_pools.items():
            if not pairs:
                log.info("placement: unit %s has empty pool — skipping", unit_id)
                continue
            items = [item for item, _ in pairs]
            n = min(k, len(items))
            per_unit[unit_id] = random.sample(items, n)
        return _round_robin_interleave(per_unit)


# ---------------------------------------------------------------------------
# Mode 2 — spread by difficulty_prior (default when coverage ≥ 0.5)
# ---------------------------------------------------------------------------


class PerUnitSpreadByPriorStrategy:
    name = "spread_by_prior"

    def select(self, unit_pools: UnitPools, k: int = 5) -> list[QuestionBankItem]:
        per_unit: dict[str, list[QuestionBankItem]] = {}
        for unit_id, pairs in unit_pools.items():
            if not pairs:
                log.info("placement: unit %s has empty pool — skipping", unit_id)
                continue
            per_unit[unit_id] = _bucket_select_k(pairs, k)
        return _round_robin_interleave(per_unit)
