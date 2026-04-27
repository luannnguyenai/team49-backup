"""Unit tests for placement strategy registry (Commit A)."""

import pytest

from src.services.placement.strategies import STRATEGY_REGISTRY
from src.services.placement.strategies.legacy_selector import LegacySelectorStrategy


def test_legacy_strategy_registered():
    """Test that legacy strategy is registered on import."""
    assert "legacy" in STRATEGY_REGISTRY
    assert isinstance(STRATEGY_REGISTRY["legacy"], LegacySelectorStrategy)


def test_legacy_strategy_has_name():
    """Test that legacy strategy has correct name."""
    strategy = STRATEGY_REGISTRY["legacy"]
    assert strategy.name == "legacy"


@pytest.mark.asyncio
async def test_legacy_strategy_select_returns_top_n():
    """Test that legacy strategy returns top n items sorted by difficulty."""
    from src.models.canonical import QuestionBankItem

    # Mock items with different difficulties
    items = [
        type("Item", (), {"item_id": "q1", "difficulty": "hard"}),
        type("Item", (), {"item_id": "q2", "difficulty": "easy"}),
        type("Item", (), {"item_id": "q3", "difficulty": "medium"}),
        type("Item", (), {"item_id": "q4", "difficulty": "easy"}),
        type("Item", (), {"item_id": "q5", "difficulty": "hard"}),
    ]

    strategy = STRATEGY_REGISTRY["legacy"]
    selected = await strategy.select(items, n=3)

    assert len(selected) == 3
    # Should be sorted: easy (1) > medium (0) > hard (2)
    difficulties = [getattr(item, "difficulty", "medium") for item in selected]
    assert difficulties[0] == "medium"  # First because medium=0 in sort order
    assert difficulties[1] == "easy"
    assert difficulties[2] == "easy"


@pytest.mark.asyncio
async def test_legacy_strategy_select_empty_pool():
    """Test that legacy strategy handles empty pool."""
    strategy = STRATEGY_REGISTRY["legacy"]
    selected = await strategy.select([], n=5)
    assert selected == []


@pytest.mark.asyncio
async def test_legacy_strategy_select_less_than_n():
    """Test that legacy strategy returns all items if pool < n."""
    items = [
        type("Item", (), {"item_id": "q1", "difficulty": "easy"}),
        type("Item", (), {"item_id": "q2", "difficulty": "medium"}),
    ]

    strategy = STRATEGY_REGISTRY["legacy"]
    selected = await strategy.select(items, n=5)

    assert len(selected) == 2
