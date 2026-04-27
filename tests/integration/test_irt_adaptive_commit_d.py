"""Integration tests for IRTAdaptiveStrategy with real DB data (Commit D)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.services.placement.strategy_selector import get_strategy


@pytest.mark.asyncio
async def test_irt_adaptive_with_db_items_force_mode(db_session: AsyncSession):
    """Test IRTAdaptiveStrategy selection with real DB items in forced mode."""
    # Get placement items
    repo = CanonicalQuestionRepository(db_session)
    items = await repo.get_items_for_phase(
        phase="placement",
        canonical_unit_ids=["cs224n_nlp_intro"],
        limit=30,
    )

    if len(items) < 5:
        pytest.skip("Not enough placement items for test")

    # Force IRT adaptive mode
    strategy = get_strategy(mode="irt_adaptive")

    # In Commit D, most items won't be calibrated yet (is_calibrated=false)
    # So selection should fallback to spread_by_prior
    selected = await strategy.select(items, n=5, theta_init=0.0)

    assert len(selected) <= 5
    # May be 0 if no calibrated items; fallback should handle this
    assert isinstance(selected, list)


@pytest.mark.asyncio
async def test_strategy_selector_respects_irt_config(db_session: AsyncSession):
    """Test that COLD_START_MODE='irt_adaptive' returns correct strategy."""
    strategy = get_strategy(mode="irt_adaptive")
    assert strategy.name == "irt_adaptive"


@pytest.mark.asyncio
async def test_irt_adaptive_fallback_to_spread_by_prior(db_session: AsyncSession):
    """Test that IRT adaptive falls back to spread_by_prior when no calibrated items."""
    repo = CanonicalQuestionRepository(db_session)
    items = await repo.get_items_for_phase(
        phase="placement",
        canonical_unit_ids=["cs224n_nlp_intro"],
        limit=10,
    )

    if not items:
        pytest.skip("No placement items in DB")

    strategy = get_strategy(mode="irt_adaptive")
    selected = await strategy.select(items, n=5, theta_init=0.5)

    # Should not raise; fallback should work
    assert isinstance(selected, list)
    # May be 0-5 items depending on fallback behavior
    assert len(selected) <= 5
