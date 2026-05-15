"""
schemas/auth.py
---------------
Pydantic v2 schemas for all authentication endpoints.
"""

import uuid
from datetime import date, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.config.goal_course_map import VALID_GOAL_IDS
from src.models.learning import MasteryLevel
from src.models.user import PreferredMethod

# ---------------------------------------------------------------------------
# Register / Login
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """POST /api/auth/register"""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """POST /api/auth/login"""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """POST /api/auth/refresh"""

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """POST /api/auth/forgot-password/request"""

    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class ForgotPasswordConfirmRequest(BaseModel):
    """POST /api/auth/forgot-password/confirm"""

    token: str = Field(min_length=16, max_length=512)
    new_password: str = Field(min_length=1, max_length=128)


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
    iat: int = 0


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


class OnboardingRequest(BaseModel):
    """PUT /api/users/me/onboarding"""

    known_unit_ids: list[uuid.UUID] = Field(
        default_factory=list,
        validation_alias=AliasChoices("known_unit_ids", "known_topic_ids"),
        description="Learning units the user already knows",
    )
    desired_section_ids: list[uuid.UUID] = Field(
        default_factory=list,
        validation_alias=AliasChoices("desired_section_ids", "desired_module_ids"),
        description="Course sections the user wants to learn",
    )
    selected_course_ids: list[str] = Field(
        default_factory=list,
        description="Explicit selected course IDs or canonical course IDs for planner scoping",
    )
    goal_ids: list[str] = Field(
        default_factory=list,
        description="Onboarding goal identifier: 'computer_vision' | 'nlp'",
    )

    @field_validator("goal_ids")
    @classmethod
    def validate_goal_ids(cls, v: list[str]) -> list[str]:
        invalid = [g for g in v if g not in VALID_GOAL_IDS]
        if invalid:
            raise ValueError(f"Unknown goal_ids: {invalid}. Valid: {sorted(VALID_GOAL_IDS)}")
        if len(v) > 1:
            raise ValueError("Planner V1 requires exactly one goal_id")
        return v

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
    role: str = "user"
    created_at: datetime


class UserSkillSnapshot(BaseModel):
    label: str
    value: float = Field(ge=0, le=100)
    level: MasteryLevel | str


class UserSkillOverview(BaseModel):
    skills: list[UserSkillSnapshot]
