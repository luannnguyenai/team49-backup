"""
schemas/user.py
---------------
Pydantic v2 schemas for User endpoints.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from src.models.user import PreferredMethod

# ---------------------------------------------------------------------------
# Shared / base
# ---------------------------------------------------------------------------


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    available_hours_per_week: float | None = Field(
        default=None, gt=0, le=168, description="Hours per week the user can dedicate (0 < x ≤ 168)"
    )
    target_deadline: date | None = None
    preferred_method: PreferredMethod | None = None


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class UserCreate(UserBase):
    """POST /users — create a new account."""

    password: str = Field(min_length=1, max_length=128)


class UserUpdate(BaseModel):
    """PATCH /users/{id} — partial update (all fields optional)."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    available_hours_per_week: float | None = Field(default=None, gt=0, le=168)
    target_deadline: date | None = None
    preferred_method: PreferredMethod | None = None


class PasswordChange(BaseModel):
    """POST /users/{id}/change-password"""

    current_password: str
    new_password: str = Field(min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserResponse(UserBase):
    """Returned from all user read endpoints."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    created_at: datetime


class UserSummary(BaseModel):
    """Lightweight representation used inside nested responses."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    full_name: str
    email: EmailStr
