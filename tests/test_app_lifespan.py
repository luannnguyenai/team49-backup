from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_lifespan_continues_when_redis_connect_fails():
    from src.api import app as app_module

    dispose_mock = AsyncMock()
    fake_engine = SimpleNamespace(dispose=dispose_mock)

    with (
        patch("src.api.app.connect_redis", new=AsyncMock(side_effect=RuntimeError("redis down"))),
        patch("src.api.app.disconnect_redis", new=AsyncMock()) as disconnect_mock,
        patch("src.api.app.async_engine", fake_engine),
    ):
        async with app_module.lifespan(app_module.app):
            pass

    disconnect_mock.assert_awaited_once()
    dispose_mock.assert_awaited_once()
