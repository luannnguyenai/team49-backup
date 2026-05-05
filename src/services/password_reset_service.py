from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.user import User
from src.repositories.password_reset_repo import PasswordResetTokenRepository
from src.repositories.user_repo import UserRepository
from src.services.auth_service import hash_password


class PasswordResetError(ValueError):
    reason: str

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(tz=UTC).replace(microsecond=0)


async def create_password_reset_token(
    db: AsyncSession,
    user: User,
    requested_ip: str | None,
) -> str:
    token = secrets.token_urlsafe(48)
    repo = PasswordResetTokenRepository(db)
    await repo.create_token(
        user_id=user.id,
        token_hash=hash_reset_token(token),
        expires_at=_now_utc() + timedelta(minutes=settings.password_reset_token_ttl_minutes),
        requested_ip=requested_ip,
    )
    return token


async def confirm_password_reset(
    db: AsyncSession,
    token: str,
    new_password: str,
) -> User:
    now = _now_utc()
    token_repo = PasswordResetTokenRepository(db)
    reset_token = await token_repo.get_by_token_hash(hash_reset_token(token))
    if reset_token is None:
        raise PasswordResetError("invalid")
    if reset_token.used_at is not None:
        raise PasswordResetError("used")
    if reset_token.expires_at < now:
        raise PasswordResetError("expired")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(reset_token.user_id)
    if user is None:
        raise PasswordResetError("invalid")

    await user_repo.update_password_changed_at(user, hash_password(new_password), now)
    await token_repo.mark_user_tokens_used(user.id, now)
    await db.flush()
    return user


def is_token_stale_for_user(payload_iat: int, user: User) -> bool:
    if user.password_changed_at is None:
        return False
    changed_at = user.password_changed_at
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=UTC)
    return datetime.fromtimestamp(payload_iat, tz=UTC) < changed_at
