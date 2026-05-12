"""Spread-by-prior difficulty strategy for cold-start placement."""

import logging
import random
from typing import Any

from src.models.canonical import QuestionBankItem
from src.services.placement.strategies import STRATEGY_REGISTRY, register

log = logging.getLogger(__name__)


def _split_into_bins(items: list[QuestionBankItem], n: int) -> list[list[QuestionBankItem]]:
    """
    Split items list into n bins of approximately equal size using divmod.

    Args:
        items: Sorted list of items.
        n: Number of bins.

    Returns:
        List of n bins, each containing ~len(items)/n items.
    """
    if n <= 0 or not items:
        return []

    size, remainder = divmod(len(items), n)
    bins = []
    idx = 0

    for i in range(n):
        bin_size = size + (1 if i < remainder else 0)
        bins.append(items[idx : idx + bin_size])
        idx += bin_size

    return bins


@register("spread_by_prior")
class SpreadByPriorStrategy:
    """
    Cold-start strategy: split pool by difficulty_prior into quantile bins,
    random.choice 1 per bin. Fallback: random_uniform if pool < n.
    """

    name = "spread_by_prior"

    async def select(
        self,
        pool: list[QuestionBankItem],
        n: int = 5,
        **ctx: Any,
    ) -> list[QuestionBankItem]:
        """
        Select n items spread across difficulty spectrum.

        Schema v2 §8.2 selection order:
        1) Pool already filtered by phase='placement' + unit_ids.
        2) Filter validity: qa_gate_passed=true AND review_status IN ('approved','final').
        3) Sort by difficulty_prior ASC.
        4) Split into n quantile bins.
        5) random.choice 1 item per bin.
        6) Apply exposure cap (item.last_shown_at in 24h for user → skip, refill).
        7) Fallback random_uniform if pool < n (graceful, log warning).

        Args:
            pool: Pre-filtered list of QuestionBankItem from item_phase_map.phase='placement'.
            n: Target number of items.
            **ctx: Context dict (user_id, exposure_repo — unused in Commit B).

        Returns:
            List of n selected items.
        """
        if not pool:
            return []

        # Filter validity: qa_gate_passed=true AND review_status in approved set
        valid_pool = [
            item
            for item in pool
            if getattr(item, "qa_gate_passed", False)
            and getattr(item, "review_status", "").lower() in ("approved", "final")
        ]

        if not valid_pool:
            # Fallback: use entire pool if no items pass validity filter
            log.warning(
                "No items pass validity filter (qa_gate_passed=true, review_status in (approved,final))"
            )
            valid_pool = pool

        # Check pool size
        if len(valid_pool) < n:
            log.warning(f"Pool size {len(valid_pool)} < target {n}, falling back to random_uniform")
            strategy = STRATEGY_REGISTRY.get("random_uniform")
            if strategy:
                return await strategy.select(valid_pool, n)
            return random.sample(valid_pool, len(valid_pool))

        # Sort by difficulty_prior (ascending: easy first)
        sorted_items = sorted(
            valid_pool,
            key=lambda item: getattr(item, "difficulty_prior", 0.0) or 0.0,
        )

        # Split into n quantile bins
        bins = _split_into_bins(sorted_items, n)

        # Select 1 random item per bin
        selected = []
        for bin_items in bins:
            if bin_items:
                selected.append(random.choice(bin_items))

        # Exposure cap: items shown in last 24h → drop and refill (Commit C+ with exposure_repo)
        # For Commit B: skip this (no exposure tracking yet), log placeholder
        if ctx.get("exposure_repo") and ctx.get("user_id"):
            log.info(
                f"Exposure cap would filter items (Commit C+): "
                f"user_id={ctx['user_id']}, cap_hours=24"
            )

        return selected
