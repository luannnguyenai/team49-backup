from typing import Any, Protocol

from src.models.canonical import QuestionBankItem


class PlacementStrategy(Protocol):
    """Strategy interface for item selection in placement assessments."""

    name: str

    async def select(
        self,
        pool: list[QuestionBankItem],
        n: int = 5,
        **ctx: Any,
    ) -> list[QuestionBankItem]:
        """
        Select n items from pool. Context dict **ctx may contain:
        - theta_init: float (current ability estimate)
        - user_id: UUID (for exposure filtering)
        - exposure_repo: repository (for item_exposure_stats lookup)
        """
        ...


STRATEGY_REGISTRY: dict[str, PlacementStrategy] = {}


def register(name: str):
    """Decorator to register a strategy in the global registry."""

    def decorator(cls):
        instance = cls()
        STRATEGY_REGISTRY[name] = instance
        return cls

    return decorator
