import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


@pytest.mark.asyncio
async def test_get_current_user_rejects_revoked_access_token():
    from src.dependencies.auth import get_current_user
    from src.schemas.auth import TokenPayload

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    payload = TokenPayload(
        sub=str(uuid.uuid4()),
        type="access",
        exp=9999999999,
        jti="revoked-token",
    )

    with (
        patch("src.dependencies.auth.decode_token", return_value=payload),
        patch("src.dependencies.auth.is_payload_revoked", new=AsyncMock(return_value=True)),
        patch("src.dependencies.auth.get_user_by_id", new=AsyncMock()),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=AsyncMock())

    assert exc.value.status_code == 401
    assert exc.value.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_get_current_user_rejects_access_token_issued_before_password_change():
    from src.dependencies.auth import get_current_user
    from src.models.user import User
    from src.schemas.auth import TokenPayload

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    user = User(
        email="stale@example.com",
        full_name="Stale User",
        hashed_password="hash",
    )
    user.password_changed_at = datetime.now(tz=UTC)
    payload = TokenPayload(
        sub=str(uuid.uuid4()),
        type="access",
        exp=9999999999,
        iat=int((datetime.now(tz=UTC) - timedelta(hours=1)).timestamp()),
        jti="stale-token",
    )

    with (
        patch("src.dependencies.auth.decode_token", return_value=payload),
        patch("src.dependencies.auth.is_payload_revoked", new=AsyncMock(return_value=False)),
        patch("src.dependencies.auth.get_user_by_id", new=AsyncMock(return_value=user)),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=AsyncMock())

    assert exc.value.status_code == 401
