from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.models.user import User


@pytest.mark.asyncio
async def test_reset_token_hash_does_not_store_plaintext():
    from src.services.password_reset_service import hash_reset_token

    token = "plain-reset-token"
    token_hash = hash_reset_token(token)

    assert token_hash != token
    assert len(token_hash) == 64


@pytest.mark.asyncio
async def test_confirm_password_reset_rejects_invalid_token():
    from src.services.password_reset_service import PasswordResetError, confirm_password_reset

    with patch("src.services.password_reset_service.PasswordResetTokenRepository") as repo_cls:
        repo_cls.return_value.get_by_token_hash = AsyncMock(return_value=None)

        with pytest.raises(PasswordResetError) as exc:
            await confirm_password_reset(AsyncMock(), "missing-token", "NewPass456!")

    assert exc.value.reason == "invalid"


@pytest.mark.asyncio
async def test_confirm_password_reset_rejects_expired_token():
    from src.services.password_reset_service import PasswordResetError, confirm_password_reset

    reset_token = SimpleNamespace(
        user_id=uuid.uuid4(),
        used_at=None,
        expires_at=datetime.now(tz=UTC) - timedelta(minutes=1),
    )

    with patch("src.services.password_reset_service.PasswordResetTokenRepository") as repo_cls:
        repo_cls.return_value.get_by_token_hash = AsyncMock(return_value=reset_token)

        with pytest.raises(PasswordResetError) as exc:
            await confirm_password_reset(AsyncMock(), "expired-token", "NewPass456!")

    assert exc.value.reason == "expired"


@pytest.mark.asyncio
async def test_confirm_password_reset_rejects_used_token():
    from src.services.password_reset_service import PasswordResetError, confirm_password_reset

    reset_token = SimpleNamespace(
        user_id=uuid.uuid4(),
        used_at=datetime.now(tz=UTC),
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=30),
    )

    with patch("src.services.password_reset_service.PasswordResetTokenRepository") as repo_cls:
        repo_cls.return_value.get_by_token_hash = AsyncMock(return_value=reset_token)

        with pytest.raises(PasswordResetError) as exc:
            await confirm_password_reset(AsyncMock(), "used-token", "NewPass456!")

    assert exc.value.reason == "used"


@pytest.mark.asyncio
async def test_confirm_password_reset_updates_password_and_consumes_tokens():
    from src.services.auth_service import verify_password
    from src.services.password_reset_service import confirm_password_reset

    user = User(
        email="reset-user@example.com",
        full_name="Reset User",
        hashed_password="OldPass123!",
    )
    user.id = uuid.uuid4()
    reset_token = SimpleNamespace(
        user_id=user.id,
        used_at=None,
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=30),
    )

    with (
        patch("src.services.password_reset_service.PasswordResetTokenRepository") as token_repo_cls,
        patch("src.services.password_reset_service.UserRepository") as user_repo_cls,
    ):
        token_repo = token_repo_cls.return_value
        token_repo.get_by_token_hash = AsyncMock(return_value=reset_token)
        token_repo.mark_user_tokens_used = AsyncMock()
        user_repo = user_repo_cls.return_value
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update_password_changed_at = AsyncMock(return_value=user)

        result = await confirm_password_reset(AsyncMock(), "valid-token", "NewPass456!")

    assert result is user
    updated_hash = user_repo.update_password_changed_at.await_args.args[1]
    assert verify_password("NewPass456!", updated_hash)
    token_repo.mark_user_tokens_used.assert_awaited_once()


@pytest.mark.asyncio
async def test_forgot_password_request_returns_ok_and_sends_email_for_existing_user():
    from src.api.app import app

    user = User(
        email="reset-user@example.com",
        full_name="Reset User",
        hashed_password="OldPass123!",
    )
    user.id = uuid.uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            patch("src.routers.auth._is_forgot_password_allowed", new=AsyncMock(return_value=True)),
            patch("src.routers.auth.get_user_by_email", new=AsyncMock(return_value=user)) as mock_get,
            patch("src.routers.auth.create_password_reset_token", new=AsyncMock(return_value="raw-token")) as mock_token,
            patch("src.routers.auth.send_password_reset_email", new=AsyncMock()) as mock_send,
        ):
            response = await client.post(
                "/api/auth/forgot-password/request",
                json={"email": "reset-user@example.com"},
            )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_get.assert_awaited_once()
    mock_token.assert_awaited_once()
    mock_send.assert_awaited_once_with("reset-user@example.com", "raw-token")


@pytest.mark.asyncio
async def test_forgot_password_request_returns_generic_ok_for_unknown_email():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            patch("src.routers.auth._is_forgot_password_allowed", new=AsyncMock(return_value=True)),
            patch("src.routers.auth.get_user_by_email", new=AsyncMock(return_value=None)),
            patch("src.routers.auth.create_password_reset_token", new=AsyncMock()) as mock_token,
            patch("src.routers.auth.send_password_reset_email", new=AsyncMock()) as mock_send,
        ):
            response = await client.post(
                "/api/auth/forgot-password/request",
                json={"email": "missing@example.com"},
            )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_token.assert_not_awaited()
    mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_forgot_password_request_rejects_direct_reset_payload():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/auth/forgot-password/request",
            json={"email": "reset-user@example.com", "new_password": "NewPass456!"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_legacy_direct_forgot_password_route_is_removed():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/auth/forgot-password",
            json={"email": "reset-user@example.com", "new_password": "NewPass456!"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_forgot_password_request_rate_limit_returns_429():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("src.routers.auth._is_forgot_password_allowed", new=AsyncMock(return_value=False)):
            response = await client.post(
                "/api/auth/forgot-password/request",
                json={"email": "reset-user@example.com"},
            )

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_confirm_forgot_password_route_returns_ok_for_valid_token():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("src.routers.auth.confirm_password_reset", new=AsyncMock()) as mock_confirm:
            response = await client.post(
                "/api/auth/forgot-password/confirm",
                json={"token": "valid-reset-token-123", "new_password": "NewPass456!"},
            )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_confirm.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_forgot_password_route_maps_token_errors():
    from src.api.app import app
    from src.services.password_reset_service import PasswordResetError

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch(
            "src.routers.auth.confirm_password_reset",
            new=AsyncMock(side_effect=PasswordResetError("expired")),
        ):
            response = await client.post(
                "/api/auth/forgot-password/confirm",
                json={"token": "expired-reset-token-123", "new_password": "NewPass456!"},
            )

    assert response.status_code == 400
    assert response.json()["detail"] == "Reset link has expired."
