"""Legacy placement selector — replicates original CanonicalQuestionSelector behavior."""

from src.models.canonical import QuestionBankItem
from src.services.placement.strategies import register

_DIFFICULTY_ORDER = {"medium": 0, "easy": 1, "hard": 2}


@register("legacy")
class LegacySelectorStrategy:
    """Original simple rank-by-difficulty strategy for regression testing."""

    name = "legacy"

    async def select(
        self,
        pool: list[QuestionBankItem],
        n: int = 5,
        **ctx,
    ) -> list[QuestionBankItem]:
        """Select by sorting on difficulty field (easy > medium > hard), take top n."""
        if not pool:
            return []

        ranked = sorted(
            pool,
            key=lambda item: (
                _DIFFICULTY_ORDER.get(str(getattr(item, "difficulty", "medium")), 1),
                str(getattr(item, "item_id", "")),
            ),
        )
        return ranked[:n]
