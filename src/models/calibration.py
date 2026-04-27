"""Models for IRT calibration infrastructure (Commit E).

Tracks calibration runs, fitted parameters history, and rollback support.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class CalibrationRun(Base):
    """Record of a single IRT calibration job execution."""

    __tablename__ = "calibration_runs"

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    method: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        comment="IRT model: 1pl | 2pl | 3pl | mirt",
    )
    dataset_version: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Data snapshot version (e.g., timestamp or git hash)",
    )
    real_response_count: Mapped[int] = mapped_column(Integer, nullable=False)
    synthetic_response_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        comment="started | passed | failed",
    )
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="true for the current active run; false for historical runs",
    )

    __table_args__ = (
        Index("ix_calibration_runs_active", "active"),
        Index("ix_calibration_runs_status", "status"),
    )


class ItemCalibrationHistory(Base):
    """Audit trail of fitted IRT parameters for each item after a calibration run."""

    __tablename__ = "item_calibration_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(String(180), nullable=False)
    calibration_run_id: Mapped[str] = mapped_column(String(80), nullable=False)
    difficulty_b: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discrimination_a: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    guessing_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    standard_error_b: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    standard_error_a: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    standard_error_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    real_response_count: Mapped[int] = mapped_column(Integer, nullable=False)
    synthetic_response_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_item_calibration_history_item", "item_id"),
        Index("ix_item_calibration_history_run", "calibration_run_id"),
    )
