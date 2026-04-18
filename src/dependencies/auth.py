"""
dependencies/auth.py
--------------------
FastAPI dependency that extracts and validates the current user from
the Authorization: Bearer <token> header.

Usage in a route:
    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)):
        ...
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.models.user import User
from src.services.auth_service import decode_token, get_user_by_id
from src.services.token_guard import is_payload_revoked

# OAuth2 bearer extractor — returns 401 automatically when header is absent
_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """Validate Bearer token and return the authenticated User ORM object."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise credentials_exception

    if await is_payload_revoked(payload):
        raise credentials_exception

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A refresh token cannot be used to authenticate requests.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_onboarded_user(
    user: User = Depends(get_current_user),
) -> User:
    """Same as get_current_user but additionally requires onboarding to be complete."""
    if not user.is_onboarded:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please complete onboarding before accessing this resource.",
        )
    return user
