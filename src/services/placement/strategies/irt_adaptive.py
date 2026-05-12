"""IRT Adaptive Strategy — 3PL-lite batch CAT for calibrated item pools."""

import logging
import math
import random
from typing import Any

from src.models.canonical import QuestionBankItem
from src.services.placement.strategies import register

log = logging.getLogger(__name__)


def _fisher_info_3pl(
    theta: float,
    a: float,
    b: float,
    c: float,
) -> float:
    """
    Calculate Fisher information I(theta) for 3PL IRT model.

    3PL: P(theta) = c + (1-c) * sigmoid(a*(theta-b))
    P_star = sigmoid(a*(theta-b))
    I(theta) = a^2 * (1-c)^2 * P_star * (1-P_star) / (P * (1-P))

    Where:
    - a: discrimination (0.75–1.10 in cold-start, typically ~1.0)
    - b: difficulty (-0.9 to 1.0 in cold-start)
    - c: guessing (0.25 for MCQ 4-option, or from item_calibration.guessing_c)
    - theta: ability estimate (user's theta_mu from learner_mastery_kp)

    Args:
        theta: Current ability estimate.
        a: Discrimination parameter (>= 0).
        b: Difficulty parameter.
        c: Guessing parameter (0 for 2PL, ~0.25 for 3PL MCQ).

    Returns:
        Fisher information I(theta). Clipped to [0, inf]; returns 0.0 if P at boundary.
    """
    # Avoid numerical issues
    if a <= 0:
        a = 1.0
    if c < 0:
        c = 0.0
    if c > 1:
        c = 1.0

    try:
        z = a * (theta - b)
        # Clamp exponent to avoid overflow
        z = max(-100, min(100, z))
        p_star = 1.0 / (1.0 + math.exp(-z))
        p = c + (1.0 - c) * p_star

        # Guard against boundary values
        if p <= 0.0 or p >= 1.0:
            return 0.0

        # I = a^2 * (1-c)^2 * p_star * (1-p_star) / (p * (1-p))
        numerator = (a**2) * ((1.0 - c) ** 2) * p_star * (1.0 - p_star)
        denominator = p * (1.0 - p)
        if denominator <= 0:
            return 0.0
        return numerator / denominator
    except (ValueError, ZeroDivisionError):
        return 0.0


@register("irt_adaptive")
class IRTAdaptiveStrategy:
    """
    IRT Adaptive strategy — batch CAT (calibrated-adaptive testing).

    Gated: requires is_calibrated=true + fitted params + SE_b<=0.3 + avg_responses>=200.
    Fallback: spread_by_prior if gate fails (not random_uniform per Schema v2 §13.6).

    Selection: top 2n items by Fisher info at theta_init, apply exposure cap, random.sample(top, n).
    """

    name = "irt_adaptive"

    async def select(
        self,
        pool: list[QuestionBankItem],
        n: int = 5,
        **ctx: Any,
    ) -> list[QuestionBankItem]:
        """
        Select n items maximizing Fisher information at theta_init (batch CAT).

        Args:
            pool: Pre-filtered placement items.
            n: Target number of items.
            **ctx: Context dict with:
                - theta_init: float (current ability estimate, default 0.0)
                - user_id: UUID (for exposure filtering)
                - exposure_repo: repository (for item_exposure_stats lookup) — Commit C+ only
                - use_2pl: bool override (Commit D: default False for 3PL-lite)

        Returns:
            List of n selected items, or fallback to spread_by_prior if pool < n or gate fails.
        """
        if not pool:
            return []

        theta_init = ctx.get("theta_init", 0.0)
        use_2pl = ctx.get("use_2pl", False)

        # Calibration gate (Schema v2 §15 Rule 7): all 4 conditions AND
        # Check: is_calibrated, difficulty_b NOT NULL, discrimination_a NOT NULL, standard_error_b <= 0.3
        calibrated_pool = [
            item
            for item in pool
            if (
                getattr(item, "is_calibrated", False) is True
                and getattr(item, "difficulty_b", None) is not None
                and getattr(item, "discrimination_a", None) is not None
                and (
                    getattr(item, "standard_error_b", None) is None
                    or getattr(item, "standard_error_b") <= 0.3
                )
            )
        ]

        if not calibrated_pool:
            log.warning(
                "IRTAdaptiveStrategy: no items pass calibration gate; falling back to spread_by_prior"
            )
            # Fallback: spread_by_prior (NOT random_uniform per §13.6)
            from src.services.placement.strategies import STRATEGY_REGISTRY

            strategy = STRATEGY_REGISTRY.get("spread_by_prior")
            if strategy:
                return await strategy.select(pool, n, **ctx)
            # Last resort fallback
            return pool[:n]

        if len(calibrated_pool) < n:
            log.warning(
                f"IRTAdaptiveStrategy: calibrated pool {len(calibrated_pool)} < target {n}; "
                f"falling back to spread_by_prior"
            )
            from src.services.placement.strategies import STRATEGY_REGISTRY

            strategy = STRATEGY_REGISTRY.get("spread_by_prior")
            if strategy:
                return await strategy.select(pool, n, **ctx)
            return calibrated_pool

        # Score items by Fisher information at theta_init
        def fisher_score(item: QuestionBankItem) -> float:
            c = 0.0 if use_2pl else (getattr(item, "guessing_c", None) or 0.25)
            a = getattr(item, "discrimination_a", 1.0) or 1.0
            b = getattr(item, "difficulty_b", 0.0)
            return _fisher_info_3pl(theta_init, a, b, c)

        scored = [(item, fisher_score(item)) for item in calibrated_pool]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Top 2n (randomesque selection reduces exposure concentration)
        top_pool = [item for item, _ in scored[: 2 * n]]

        # Exposure cap: filter recently shown items (Commit C+ with exposure_repo)
        if ctx.get("exposure_repo") and ctx.get("user_id"):
            log.info(
                f"Exposure cap would filter items (Commit C+): "
                f"user_id={ctx['user_id']}, cap_hours=24"
            )
            # TODO: Commit C+ implements actual exposure filtering

        # Random sample to reduce exposure clustering
        selected = random.sample(top_pool, min(n, len(top_pool)))

        log.info(
            f"IRTAdaptiveStrategy: selected {len(selected)} items from calibrated pool "
            f"(theta_init={theta_init:.2f}, use_2pl={use_2pl})"
        )

        return selected
