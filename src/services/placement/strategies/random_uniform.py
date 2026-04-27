"""Random uniform sampling strategy for item selection."""

import random
from typing import Any

from src.models.canonical import QuestionBankItem
from src.services.placement.strategies import register


@register("random_uniform")
class RandomUniformStrategy:
    """Random uniform sampling — safety-net fallback when pool < n."""

    name = "random_uniform"

    async def select(
        self,
        pool: list[QuestionBankItem],
        n: int = 5,
        **ctx: Any,
    ) -> list[QuestionBankItem]:
        """Randomly sample n items from pool without replacement."""
        if not pool:
            return []
        return random.sample(pool, min(n, len(pool)))
