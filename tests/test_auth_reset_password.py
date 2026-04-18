from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.models.user import User


@pytest.mark.asyncio
async def test_reset_password_for_email_updates_hash_for_existing_user():
    from src.services.auth_service import reset_password_for_email, verify_password

    user = User(
        email="reset-user@example.com",
        full_name="Reset User",
        hashed_password="OldPass123!",
    )

    with patch("src.services.auth_service.UserRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_by_email = AsyncMock(return_value=user)
        repo.update_hashed_password = AsyncMock(return_value=user)

        result = await reset_password_for_email(AsyncMock(), "reset-user@example.com", "NewPass456!")

    assert result is user
    updated_hash = repo.update_hashed_password.await_args.args[1]
    assert verify_password("NewPass456!", updated_hash)


@pytest.mark.asyncio
async def test_forgot_password_route_returns_ok_for_existing_user():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("src.routers.auth.reset_password_for_email", new=AsyncMock()) as mock_reset:
            response = await client.post(
                "/api/auth/forgot-password",
                json={
                    "email": "reset-user@example.com",
                    "new_password": "NewPass456!",
                },
            )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_reset.assert_awaited_once()


@pytest.mark.asyncio
async def test_forgot_password_route_returns_404_for_unknown_email():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch(
            "src.routers.auth.reset_password_for_email",
            new=AsyncMock(side_effect=ValueError("No account found for this email.")),
        ):
            response = await client.post(
                "/api/auth/forgot-password",
                json={
                    "email": "missing@example.com",
                    "new_password": "NewPass456!",
                },
            )

    assert response.status_code == 404
    assert response.json()["detail"] == "No account found for this email."
