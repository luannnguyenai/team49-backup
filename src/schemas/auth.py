"""
schemas/auth.py
---------------
Pydantic v2 schemas for all authentication endpoints.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.models.user import PreferredMethod

# ---------------------------------------------------------------------------
# Register / Login
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """POST /api/auth/register"""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


class LoginRequest(BaseModel):
    """POST /api/auth/login"""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """POST /api/auth/refresh"""

    refresh_token: str


# ---------------------------------------------------------------------------
# Token responses
# ---------------------------------------------------------------------------


class TokenPair(BaseModel):
    """Returned on register, login, and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class AccessToken(BaseModel):
    """Returned on token refresh (only access token is rotated)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# JWT payload (internal — not exposed to clients)
# ---------------------------------------------------------------------------


class TokenPayload(BaseModel):
    sub: str  # user UUID as string
    type: str  # "access" | "refresh"
    exp: int  # unix timestamp
    jti: str


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


class OnboardingRequest(BaseModel):
    """PUT /api/users/me/onboarding"""

    known_topic_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Topics the user already knows (used to seed mastery scores)",
    )
    desired_module_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Modules the user wants to learn"
    )
    available_hours_per_week: float = Field(
        gt=0, le=168, description="Hours per week the user can dedicate"
    )
    target_deadline: date = Field(description="ISO-8601 date string: YYYY-MM-DD")
    preferred_method: PreferredMethod


# ---------------------------------------------------------------------------
# User profile response (auth-specific, no password field)
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    """Returned from GET /api/users/me and PUT /api/users/me/onboarding."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    full_name: str
    available_hours_per_week: float | None
    target_deadline: date | None
    preferred_method: PreferredMethod | None
    is_onboarded: bool
    created_at: datetime
