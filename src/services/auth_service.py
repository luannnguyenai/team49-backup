"""
services/auth_service.py
------------------------
Pure business logic for authentication and user management.
No HTTP concerns here — can be tested independently.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.user import User
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.repositories.user_repo import UserRepository
from src.schemas.auth import OnboardingRequest, RegisterRequest, TokenPayload

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Returns (encoded_jwt, expires_in_seconds)."""
    expire = _now_utc() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(_now_utc().timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, settings.access_token_expire_minutes * 60


def create_refresh_token(user_id: uuid.UUID) -> str:
    expire = _now_utc() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(_now_utc().timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT. Raises ValueError on any failure."""
    try:
        raw = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return TokenPayload(**raw)
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


def get_token_remaining_seconds(payload: TokenPayload) -> int:
    """Return remaining TTL for a decoded token, never below zero."""
    remaining = payload.exp - int(_now_utc().timestamp())
    return max(0, remaining)


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    repo = UserRepository(db)
    return await repo.get_by_email(email)


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    repo = UserRepository(db)
    return await repo.get_by_id(user_id)


# ---------------------------------------------------------------------------
# Service methods
# ---------------------------------------------------------------------------


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Create a new user. Raises ValueError if email already exists."""
    repo = UserRepository(db)
    existing = await repo.get_by_email(data.email)
    if existing:
        raise ValueError("An account with this email already exists.")

    user = await repo.create(
        email=data.email.lower(),
        full_name=data.full_name.strip(),
        hashed_password=hash_password(data.password),
    )
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials. Raises ValueError on invalid email or password."""
    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Incorrect email or password.")
    return user


async def reset_password_for_email(
    db: AsyncSession,
    email: str,
    new_password: str,
) -> User:
    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if not user:
        raise ValueError("No account found for this email.")

    hashed_password = hash_password(new_password)
    return await repo.update_hashed_password(user, hashed_password)


async def update_onboarding(
    db: AsyncSession,
    user: User,
    data: OnboardingRequest,
) -> User:
    """Persist onboarding preferences onto the user row."""
    user.available_hours_per_week = data.available_hours_per_week
    user.target_deadline = data.target_deadline
    user.preferred_method = data.preferred_method
    user.is_onboarded = True

    db.add(user)
    await db.flush()
    await _write_goal_preferences_if_enabled(db, user, data)
    await db.refresh(user)
    return user


async def _write_goal_preferences_if_enabled(
    db: AsyncSession,
    user: User,
    data: OnboardingRequest,
) -> None:
    """
    Persist the course-first goal-preference snapshot used by the planner.
    """
    if not settings.write_goal_preferences_enabled:
        return

    repo = GoalPreferenceRepository(db)
    goal_weights_json = {
        "available_hours_per_week": data.available_hours_per_week,
        "preferred_method": data.preferred_method.value,
        "desired_section_count": len(data.desired_section_ids),
        "known_unit_count": len(data.known_unit_ids),
        "selected_course_count": len(data.selected_course_ids),
    }
    notes = json.dumps(
        {
            "desired_section_ids": [str(section_id) for section_id in data.desired_section_ids],
            "known_unit_ids": [str(unit_id) for unit_id in data.known_unit_ids],
            "selected_course_ids": data.selected_course_ids,
            "source": "auth_onboarding_course_first_runtime",
        },
        sort_keys=True,
    )
    await repo.upsert_for_user(
        user_id=user.id,
        goal_weights_json=goal_weights_json,
        selected_course_ids=data.selected_course_ids or None,
        goal_embedding=None,
        goal_embedding_version=None,
        derived_from_course_set_hash=None,
        notes=notes,
    )
