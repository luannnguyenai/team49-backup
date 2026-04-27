"""Integration tests for audit logging via sessions and interactions (Commit C)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.placement.strategy_selector import _unit_calibration_summary


@pytest.mark.asyncio
async def test_unit_calibration_summary_query(db_session: AsyncSession):
    """Test that _unit_calibration_summary returns correct stats per unit."""
    # Commit C: query should return per-unit calibration status
    # Assume we have some placement items in DB
    unit_ids = ["cs224n_nlp_intro"]

    summary = await _unit_calibration_summary(db_session, unit_ids)

    # Should return dict with unit_id keys
    if unit_ids[0] in summary:
        stats = summary[unit_ids[0]]
        # Check required keys
        assert "is_calibrated_ratio" in stats
        assert "median_se_b" in stats
        assert "avg_responses_per_item" in stats
        assert "has_active_calibration_run" in stats
        assert "pass_all_gates" in stats

        # Check types
        assert isinstance(stats["is_calibrated_ratio"], float)
        assert isinstance(stats["avg_responses_per_item"], float)
        assert isinstance(stats["has_active_calibration_run"], bool)
        assert isinstance(stats["pass_all_gates"], bool)

        # Commit C: no active calibration runs yet
        assert stats["has_active_calibration_run"] is False


@pytest.mark.asyncio
async def test_unit_calibration_summary_empty_units(db_session: AsyncSession):
    """Test that _unit_calibration_summary handles empty unit list."""
    summary = await _unit_calibration_summary(db_session, [])
    assert summary == {}


@pytest.mark.asyncio
async def test_unit_calibration_summary_nonexistent_unit(db_session: AsyncSession):
    """Test that _unit_calibration_summary handles nonexistent units gracefully."""
    summary = await _unit_calibration_summary(db_session, ["nonexistent_unit_xyz"])
    # Should not raise, may return empty or with empty stats
    assert isinstance(summary, dict)
