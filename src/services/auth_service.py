"""
services/auth_service.py
------------------------
Pure business logic for authentication and user management.
No HTTP concerns here — can be tested independently.
"""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.user import User
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
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Service methods
# ---------------------------------------------------------------------------


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Create a new user. Raises ValueError if email already exists."""
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise ValueError("An account with this email already exists.")

    user = User(
        email=data.email.lower(),
        full_name=data.full_name.strip(),
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()  # get the generated UUID before commit
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials. Raises ValueError on invalid email or password."""
    user = await get_user_by_email(db, email.lower())
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Incorrect email or password.")
    return user


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
    await db.refresh(user)
    return user
