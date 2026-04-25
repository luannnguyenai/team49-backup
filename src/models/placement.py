# src/models/placement.py
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.base import Base, UUIDPrimaryKeyMixin


class PlacementAssessmentResult(UUIDPrimaryKeyMixin, Base):
    """Per-topic placement assessment result (append-only).

    Uses UUIDPrimaryKeyMixin for id but NOT TimestampMixin — the DB schema
    has no updated_at column; created_at is manually declared to match.
    """

    __tablename__ = "placement_assessment_results"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    score_pct: Mapped[Decimal] = mapped_column(Numeric(precision=5, scale=2), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    user_choice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_answers: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'")
    )
    theta_estimate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=8, scale=4), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "decision IN ('skip', 'review', 'relearn')",
            name="ck_placement_results_decision",
        ),
        CheckConstraint(
            "user_choice IS NULL OR user_choice IN ('skip', 'review')",
            name="ck_placement_results_user_choice",
        ),
        CheckConstraint(
            "score_pct >= 0 AND score_pct <= 100",
            name="ck_placement_results_score_range",
        ),
        Index("ix_placement_results_user_unit", "user_id", "topic_unit_id"),
        Index("ix_placement_results_user", "user_id"),
    )
