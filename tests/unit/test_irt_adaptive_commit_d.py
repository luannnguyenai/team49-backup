"""Unit tests for IRTAdaptiveStrategy with 3PL-lite batch CAT (Commit D)."""

import pytest

from src.services.placement.strategies import STRATEGY_REGISTRY
from src.services.placement.strategies.irt_adaptive import (
    IRTAdaptiveStrategy,
    _fisher_info_3pl,
)


class MockCalibratedItem:
    """Mock calibrated item for testing."""

    def __init__(
        self,
        item_id: str,
        difficulty_b: float = 0.0,
        discrimination_a: float = 1.0,
        guessing_c: float = 0.25,
        standard_error_b: float = 0.2,
        is_calibrated: bool = True,
    ):
        self.item_id = item_id
        self.difficulty_b = difficulty_b
        self.discrimination_a = discrimination_a
        self.guessing_c = guessing_c
        self.standard_error_b = standard_error_b
        self.is_calibrated = is_calibrated


def test_irt_adaptive_registered():
    """Test that irt_adaptive strategy is registered."""
    assert "irt_adaptive" in STRATEGY_REGISTRY
    assert isinstance(STRATEGY_REGISTRY["irt_adaptive"], IRTAdaptiveStrategy)


def test_fisher_info_3pl_at_origin():
    """Test Fisher info formula at theta=0, b=0, a=1, c=0.25."""
    # At theta=0, b=0: p_star = 0.5
    # p = 0.25 + 0.75 * 0.5 = 0.625
    # I = 1^2 * 0.75^2 * 0.5 * 0.5 / (0.625 * 0.375)
    #   = 0.5625 * 0.25 / 0.234375
    #   ≈ 0.6
    info = _fisher_info_3pl(theta=0.0, a=1.0, b=0.0, c=0.25)
    assert info > 0.5  # Approximate check
    assert info < 1.0


def test_fisher_info_3pl_away_from_item():
    """Test Fisher info decreases when theta is far from item difficulty."""
    # Item at b=2.0 (difficult); theta=0 is far away
    info_far = _fisher_info_3pl(theta=0.0, a=1.0, b=2.0, c=0.25)
    # Item at b=0.0 (easy); theta=0 is aligned
    info_close = _fisher_info_3pl(theta=0.0, a=1.0, b=0.0, c=0.25)
    assert info_far < info_close


def test_fisher_info_3pl_2pl_vs_3pl():
    """Test that 2PL (c=0) has different info than 3PL (c=0.25)."""
    info_2pl = _fisher_info_3pl(theta=0.0, a=1.0, b=0.0, c=0.0)
    info_3pl = _fisher_info_3pl(theta=0.0, a=1.0, b=0.0, c=0.25)
    assert info_2pl != info_3pl


def test_fisher_info_boundary_cases():
    """Test Fisher info handles boundary cases gracefully."""
    # Very high theta (P -> 1)
    info_high = _fisher_info_3pl(theta=100.0, a=1.0, b=0.0, c=0.25)
    assert info_high >= 0.0

    # Very low theta (P -> c)
    info_low = _fisher_info_3pl(theta=-100.0, a=1.0, b=0.0, c=0.25)
    assert info_low >= 0.0

    # Invalid a (should default to 1.0)
    info_bad_a = _fisher_info_3pl(theta=0.0, a=-1.0, b=0.0, c=0.25)
    assert info_bad_a >= 0.0


@pytest.mark.asyncio
async def test_irt_adaptive_select_empty_pool():
    """Test IRT adaptive with empty pool."""
    strategy = STRATEGY_REGISTRY["irt_adaptive"]
    selected = await strategy.select([], n=5)
    assert selected == []


@pytest.mark.asyncio
async def test_irt_adaptive_select_no_calibrated_items():
    """Test IRT adaptive fallback when no items pass calibration gate."""
    # Create uncalibrated items
    items = [
        MockCalibratedItem("q1", is_calibrated=False),
        MockCalibratedItem("q2", is_calibrated=False),
    ]

    strategy = STRATEGY_REGISTRY["irt_adaptive"]
    # Should fallback to spread_by_prior (or return all if spread_by_prior unavailable)
    selected = await strategy.select(items, n=2)
    # Should not crash; may return items or fallback
    assert isinstance(selected, list)


@pytest.mark.asyncio
async def test_irt_adaptive_select_calibrated_items():
    """Test IRT adaptive selects from calibrated pool."""
    # Create calibrated items with varied difficulty
    items = [
        MockCalibratedItem("easy", difficulty_b=-0.8),
        MockCalibratedItem("easy2", difficulty_b=-0.7),
        MockCalibratedItem("medium", difficulty_b=0.0),
        MockCalibratedItem("medium2", difficulty_b=0.1),
        MockCalibratedItem("hard", difficulty_b=0.8),
        MockCalibratedItem("hard2", difficulty_b=0.9),
    ]

    strategy = STRATEGY_REGISTRY["irt_adaptive"]
    selected = await strategy.select(items, n=3, theta_init=0.0)

    assert len(selected) == 3
    # At theta=0, items near difficulty 0 should score highest in Fisher info
    selected_difficulties = [item.difficulty_b for item in selected]
    # Should be somewhat centered around 0 (not all hard or all easy)
    assert min(selected_difficulties) <= 0.5
    assert max(selected_difficulties) >= -0.5


@pytest.mark.asyncio
async def test_irt_adaptive_select_with_se_b_gate():
    """Test IRT adaptive respects standard_error_b gate (SE_b <= 0.3)."""
    items = [
        MockCalibratedItem("good1", standard_error_b=0.2),
        MockCalibratedItem("good2", standard_error_b=0.3),
        MockCalibratedItem("bad1", standard_error_b=0.31),  # Fails gate
        MockCalibratedItem("bad2", standard_error_b=0.5),   # Fails gate
    ]

    strategy = STRATEGY_REGISTRY["irt_adaptive"]
    selected = await strategy.select(items, n=2, theta_init=0.0)

    # Only "good1" and "good2" pass the SE_b gate
    selected_ids = {item.item_id for item in selected}
    assert "good1" in selected_ids
    assert "good2" in selected_ids
    assert "bad1" not in selected_ids
    assert "bad2" not in selected_ids


@pytest.mark.asyncio
async def test_irt_adaptive_select_2pl_mode():
    """Test IRT adaptive with 2PL flag (c=0 instead of 0.25)."""
    items = [
        MockCalibratedItem("q1", difficulty_b=-0.5),
        MockCalibratedItem("q2", difficulty_b=0.0),
        MockCalibratedItem("q3", difficulty_b=0.5),
    ]

    strategy = STRATEGY_REGISTRY["irt_adaptive"]
    selected_2pl = await strategy.select(items, n=2, theta_init=0.0, use_2pl=True)
    selected_3pl = await strategy.select(items, n=2, theta_init=0.0, use_2pl=False)

    # Both should return 2 items (order may differ)
    assert len(selected_2pl) == 2
    assert len(selected_3pl) == 2
