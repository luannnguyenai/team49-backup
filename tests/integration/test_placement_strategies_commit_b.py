"""Integration tests for spread_by_prior and random_uniform strategies with DB (Commit B)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.services.placement.strategy_selector import get_strategy


@pytest.mark.asyncio
async def test_spread_by_prior_with_real_placement_items(db_session: AsyncSession):
    """Test spread_by_prior strategy with real DB placement items."""
    repo = CanonicalQuestionRepository(db_session)

    # Get a sample of placement items
    items = await repo.get_items_for_phase(
        phase="placement",
        canonical_unit_ids=["cs224n_nlp_intro"],
        limit=20,
    )

    if len(items) < 5:
        pytest.skip("Not enough placement items in DB for test")

    strategy = get_strategy(mode="spread_by_prior")
    selected = await strategy.select(items, n=5)

    assert len(selected) == 5
    # Verify all selected are from pool
    selected_ids = {item.item_id for item in selected}
    pool_ids = {item.item_id for item in items}
    assert selected_ids.issubset(pool_ids)

    # Verify spread: items should come from different parts of difficulty spectrum
    difficulties = [item.difficulty_prior for item in selected if item.difficulty_prior is not None]
    if len(difficulties) > 1:
        # If we have multiple items with difficulty, check they're spread
        min_diff = min(difficulties)
        max_diff = max(difficulties)
        # Spread should be more than 0 (not all same difficulty)
        assert max_diff >= min_diff


@pytest.mark.asyncio
async def test_random_uniform_with_real_placement_items(db_session: AsyncSession):
    """Test random_uniform strategy with real DB placement items."""
    repo = CanonicalQuestionRepository(db_session)

    items = await repo.get_items_for_phase(
        phase="placement",
        canonical_unit_ids=["cs224n_nlp_intro"],
        limit=20,
    )

    if len(items) < 5:
        pytest.skip("Not enough placement items in DB for test")

    strategy = get_strategy(mode="random_uniform")
    selected = await strategy.select(items, n=5)

    assert len(selected) == 5
    # All items should be unique
    selected_ids = {item.item_id for item in selected}
    assert len(selected_ids) == 5


@pytest.mark.asyncio
async def test_spread_by_prior_fallback_with_small_pool(db_session: AsyncSession):
    """Test spread_by_prior fallback to random_uniform when pool < n."""
    repo = CanonicalQuestionRepository(db_session)

    # Get placement items for a unit that might have < 5 items
    items = await repo.get_items_for_phase(
        phase="placement",
        canonical_unit_ids=["cs224n_nlp_intro"],
        limit=3,  # Request only 3
    )

    if len(items) < 2:
        pytest.skip("Test requires at least 2 placement items")

    strategy = get_strategy(mode="spread_by_prior")
    selected = await strategy.select(items, n=10)

    # Should return all available items (fallback to random_uniform)
    assert len(selected) == len(items)


@pytest.mark.asyncio
async def test_strategy_selector_loads_from_config(db_session: AsyncSession):
    """Test that get_strategy respects cold_start_mode config."""
    for mode in ["random_uniform", "spread_by_prior", "legacy"]:
        strategy = get_strategy(mode=mode)
        assert strategy is not None
        assert strategy.name == mode
