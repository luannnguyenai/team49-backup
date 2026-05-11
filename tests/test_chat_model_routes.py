from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app


@pytest.mark.asyncio
async def test_chat_model_availability_route_returns_safe_model_statuses():
    fake_availability = [
        {
            "id": "default",
            "label": "Default",
            "status": "healthy",
            "available": True,
            "checked_at": "2026-05-11T00:00:00+00:00",
        },
        {
            "id": "qwen35_4b",
            "label": "Qwen 3.5 4B",
            "status": "down",
            "available": False,
            "checked_at": "2026-05-11T00:00:00+00:00",
        },
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch(
            "src.routers.chat_models.check_all_chat_model_availability",
            new=AsyncMock(return_value=fake_availability),
        ):
            response = await client.get("/api/chat-models/availability")

    assert response.status_code == 200
    assert response.json() == {"models": fake_availability}
    assert "base_url" not in response.text
    assert "error" not in response.text
