"""Unit tests for audit logging in Commit C."""

import pytest

from src.services.placement.strategy_selector import get_strategy


def test_get_strategy_returns_spread_by_prior_by_default():
    """Test that default strategy is spread_by_prior (Commit C default)."""
    strategy = get_strategy()
    assert strategy.name == "spread_by_prior"


def test_get_strategy_respects_mode_override():
    """Test that explicit mode overrides default."""
    for mode in ["legacy", "random_uniform", "spread_by_prior"]:
        strategy = get_strategy(mode=mode)
        assert strategy.name == mode


def test_get_strategy_auto_mode_defaults_to_spread_by_prior():
    """Test that 'auto' mode defaults to spread_by_prior (Commit C stub)."""
    strategy = get_strategy(mode="auto")
    # Commit C: auto-mode is stubbed, returns spread_by_prior
    assert strategy.name == "spread_by_prior"


def test_get_strategy_invalid_mode_raises():
    """Test that invalid mode raises KeyError."""
    with pytest.raises(KeyError):
        get_strategy(mode="invalid_mode")
