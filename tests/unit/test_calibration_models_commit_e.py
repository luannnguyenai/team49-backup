"""Unit tests for Commit E calibration models."""

import pytest
from datetime import datetime, timezone

from src.models.calibration import CalibrationRun, ItemCalibrationHistory
from src.models.canonical import ItemCalibration


def test_calibration_run_model_fields():
    """Test CalibrationRun model fields and defaults."""
    now = datetime.now(timezone.utc)
    run = CalibrationRun(
        run_id="cal_test_001",
        method="2pl",
        dataset_version="2026-04-27T12:00:00Z",
        real_response_count=1000,
        synthetic_response_count=0,
        status="passed",
    )

    assert run.run_id == "cal_test_001"
    assert run.method == "2pl"
    assert run.dataset_version == "2026-04-27T12:00:00Z"
    assert run.real_response_count == 1000
    assert run.synthetic_response_count == 0
    assert run.status == "passed"
    assert CalibrationRun.__table__.c.active.default.arg is False
    assert run.metrics_json is None


def test_item_calibration_history_model_fields():
    """Test ItemCalibrationHistory model fields."""
    history = ItemCalibrationHistory(
        item_id="item_001",
        calibration_run_id="cal_test_001",
        difficulty_b=0.5,
        discrimination_a=1.2,
        guessing_c=0.25,
        standard_error_b=0.1,
        standard_error_a=0.15,
        standard_error_c=0.05,
        real_response_count=100,
        synthetic_response_count=0,
    )

    assert history.item_id == "item_001"
    assert history.calibration_run_id == "cal_test_001"
    assert history.difficulty_b == 0.5
    assert history.discrimination_a == 1.2
    assert history.guessing_c == 0.25
    assert history.standard_error_b == 0.1
    assert history.standard_error_a == 0.15
    assert history.standard_error_c == 0.05
    assert history.real_response_count == 100
    assert history.synthetic_response_count == 0


def test_item_calibration_new_fields():
    """Test ItemCalibration model has new Commit E fields."""
    ic = ItemCalibration(
        item_id="item_001",
        is_calibrated=False,
    )

    # Verify new Commit E fields exist
    assert hasattr(ic, "standard_error_a")
    assert hasattr(ic, "standard_error_c")
    assert hasattr(ic, "calibration_run_id")
    assert hasattr(ic, "calibration_dataset_version")
    assert hasattr(ic, "real_response_count")
    assert hasattr(ic, "synthetic_response_count")


def test_calibration_run_status_values():
    """Test CalibrationRun status field accepts valid values."""
    for status in ["started", "passed", "failed"]:
        run = CalibrationRun(
            run_id=f"cal_test_{status}",
            method="2pl",
            dataset_version="test",
            real_response_count=0,
            synthetic_response_count=0,
            status=status,
        )
        assert run.status == status


def test_calibration_run_method_values():
    """Test CalibrationRun method field accepts valid IRT models."""
    for method in ["1pl", "2pl", "3pl", "mirt"]:
        run = CalibrationRun(
            run_id=f"cal_test_{method}",
            method=method,
            dataset_version="test",
            real_response_count=0,
            synthetic_response_count=0,
            status="started",
        )
        assert run.method == method
