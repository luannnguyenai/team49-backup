"""
models/user.py
--------------
User account model for the adaptive learning platform.
"""

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.learning import Interaction, LearningPath, MasteryScore, Session


class PreferredMethod(enum.StrEnum):
    reading = "reading"
    video = "video"


class User(UUIDPrimaryKeyMixin, Base):
    """Platform user / learner."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    available_hours_per_week: Mapped[float | None] = mapped_column(
        nullable=True, comment="Self-reported hours available per week"
    )
    target_deadline: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="When the user wants to finish the curriculum"
    )
    preferred_method: Mapped[PreferredMethod | None] = mapped_column(
        Enum(PreferredMethod, name="preferred_method_enum"),
        nullable=True,
    )
    is_onboarded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="True once the user has completed the onboarding flow",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---- relationships ----
    sessions: Mapped[list["Session"]] = relationship(  # type: ignore[name-defined]
        "Session", back_populates="user", lazy="select"
    )
    interactions: Mapped[list["Interaction"]] = relationship(  # type: ignore[name-defined]
        "Interaction", back_populates="user", lazy="select"
    )
    mastery_scores: Mapped[list["MasteryScore"]] = relationship(  # type: ignore[name-defined]
        "MasteryScore", back_populates="user", lazy="select"
    )
    learning_paths: Mapped[list["LearningPath"]] = relationship(  # type: ignore[name-defined]
        "LearningPath", back_populates="user", lazy="select"
    )
