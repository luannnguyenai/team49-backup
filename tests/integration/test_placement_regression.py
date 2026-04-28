"""Integration tests for placement strategy refactoring (Commit A regression testing)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import Session, SessionType
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.services.placement.strategy_selector import get_strategy


@pytest.mark.asyncio
async def test_placement_lite_with_legacy_strategy(db_session: AsyncSession):
    """Test that legacy strategy selection works with real DB data."""
    # Get a sample of placement items
    repo = CanonicalQuestionRepository(db_session)

    # Get placement items for a sample unit (assuming at least one exists)
    items = await repo.get_items_for_phase(
        phase="placement",
        canonical_unit_ids=["cs224n_nlp_intro"],  # Example unit
        limit=20,
    )

    if len(items) < 5:
        pytest.skip("Not enough placement items in DB for test")

    # Apply legacy strategy
    strategy = get_strategy(mode="legacy")
    selected = await strategy.select(items, n=5)

    assert len(selected) == 5
    # Verify all selected items are from the pool
    selected_ids = {item.item_id for item in selected}
    pool_ids = {item.item_id for item in items}
    assert selected_ids.issubset(pool_ids)


@pytest.mark.asyncio
async def test_strategy_registry_initialization(db_session: AsyncSession):
    """Test that get_strategy initializes and returns valid strategy."""
    from src.services.placement.strategies import STRATEGY_REGISTRY

    assert "legacy" in STRATEGY_REGISTRY

    strategy = get_strategy(mode="legacy")
    assert strategy is not None
    assert strategy.name == "legacy"
