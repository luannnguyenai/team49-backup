"""Unit tests for spread_by_prior and random_uniform strategies (Commit B)."""

import pytest

from src.services.placement.strategies import STRATEGY_REGISTRY
from src.services.placement.strategies.random_uniform import RandomUniformStrategy
from src.services.placement.strategies.spread_by_prior import (
    SpreadByPriorStrategy,
    _split_into_bins,
)


class MockItem:
    """Mock QuestionBankItem for testing."""

    def __init__(
        self,
        item_id: str,
        difficulty_prior: float | None = 0.0,
        qa_gate_passed: bool = True,
        review_status: str = "approved",
    ):
        self.item_id = item_id
        self.difficulty_prior = difficulty_prior
        self.qa_gate_passed = qa_gate_passed
        self.review_status = review_status


def test_random_uniform_registered():
    """Test that random_uniform strategy is registered."""
    assert "random_uniform" in STRATEGY_REGISTRY
    assert isinstance(STRATEGY_REGISTRY["random_uniform"], RandomUniformStrategy)


def test_spread_by_prior_registered():
    """Test that spread_by_prior strategy is registered."""
    assert "spread_by_prior" in STRATEGY_REGISTRY
    assert isinstance(STRATEGY_REGISTRY["spread_by_prior"], SpreadByPriorStrategy)


def test_split_into_bins_equal_distribution():
    """Test _split_into_bins with equal distribution."""
    items = [MockItem(f"q{i}") for i in range(10)]
    bins = _split_into_bins(items, 5)

    assert len(bins) == 5
    assert all(len(bin) == 2 for bin in bins)
    assert sum(len(bin) for bin in bins) == 10


def test_split_into_bins_unequal_distribution():
    """Test _split_into_bins with unequal distribution (remainder)."""
    items = [MockItem(f"q{i}") for i in range(7)]
    bins = _split_into_bins(items, 3)

    assert len(bins) == 3
    assert bins[0].__len__() == 3  # 7 // 3 = 2, remainder 1
    assert bins[1].__len__() == 2
    assert bins[2].__len__() == 2


def test_split_into_bins_more_bins_than_items():
    """Test _split_into_bins when n > len(items)."""
    items = [MockItem(f"q{i}") for i in range(3)]
    bins = _split_into_bins(items, 5)

    # Should have 5 bins, some empty
    assert len(bins) == 5
    non_empty = [b for b in bins if len(b) > 0]
    assert len(non_empty) == 3


def test_split_into_bins_empty_list():
    """Test _split_into_bins with empty items."""
    bins = _split_into_bins([], 5)
    assert bins == []


@pytest.mark.asyncio
async def test_random_uniform_select():
    """Test RandomUniformStrategy.select returns n random items."""
    items = [MockItem(f"q{i}") for i in range(20)]
    strategy = STRATEGY_REGISTRY["random_uniform"]
    selected = await strategy.select(items, n=5)

    assert len(selected) == 5
    selected_ids = {item.item_id for item in selected}
    assert len(selected_ids) == 5  # All unique


@pytest.mark.asyncio
async def test_random_uniform_select_empty():
    """Test RandomUniformStrategy.select with empty pool."""
    strategy = STRATEGY_REGISTRY["random_uniform"]
    selected = await strategy.select([], n=5)
    assert selected == []


@pytest.mark.asyncio
async def test_random_uniform_select_less_than_n():
    """Test RandomUniformStrategy.select when pool < n."""
    items = [MockItem(f"q{i}") for i in range(3)]
    strategy = STRATEGY_REGISTRY["random_uniform"]
    selected = await strategy.select(items, n=10)

    assert len(selected) == 3


@pytest.mark.asyncio
async def test_spread_by_prior_select_filters_validity():
    """Test SpreadByPriorStrategy filters by qa_gate_passed and review_status."""
    items = [
        MockItem("q1", difficulty_prior=-0.7, qa_gate_passed=True, review_status="approved"),
        MockItem("q2", difficulty_prior=0.0, qa_gate_passed=False, review_status="approved"),
        MockItem("q3", difficulty_prior=0.8, qa_gate_passed=True, review_status="draft"),
        MockItem("q4", difficulty_prior=-0.2, qa_gate_passed=True, review_status="final"),
    ]

    strategy = STRATEGY_REGISTRY["spread_by_prior"]
    selected = await strategy.select(items, n=2)

    # Only q1 and q4 should pass filter
    selected_ids = {item.item_id for item in selected}
    assert "q2" not in selected_ids  # qa_gate_passed=False
    assert "q3" not in selected_ids  # review_status=draft


@pytest.mark.asyncio
async def test_spread_by_prior_select_empty():
    """Test SpreadByPriorStrategy.select with empty pool."""
    strategy = STRATEGY_REGISTRY["spread_by_prior"]
    selected = await strategy.select([], n=5)
    assert selected == []


@pytest.mark.asyncio
async def test_spread_by_prior_select_fallback_to_random():
    """Test SpreadByPriorStrategy fallbacks to random_uniform when pool < n."""
    items = [MockItem(f"q{i}", difficulty_prior=float(i) - 2) for i in range(3)]
    strategy = STRATEGY_REGISTRY["spread_by_prior"]
    selected = await strategy.select(items, n=5)

    # Should fallback and return all 3
    assert len(selected) == 3


@pytest.mark.asyncio
async def test_spread_by_prior_select_spreads_by_difficulty():
    """Test SpreadByPriorStrategy spreads selection across difficulty spectrum."""
    # Create items with wide difficulty range
    items = [
        MockItem(f"easy_{i}", difficulty_prior=-0.8 + i * 0.1) for i in range(5)
    ] + [
        MockItem(f"med_{i}", difficulty_prior=-0.2 + i * 0.1) for i in range(5)
    ] + [
        MockItem(f"hard_{i}", difficulty_prior=0.6 + i * 0.1) for i in range(5)
    ]

    strategy = STRATEGY_REGISTRY["spread_by_prior"]
    selected = await strategy.select(items, n=5)

    assert len(selected) == 5
    # Verify items come from different bins (approximate check)
    difficulties = [item.difficulty_prior for item in selected]
    assert min(difficulties) <= -0.7
    assert max(difficulties) >= 0.5
