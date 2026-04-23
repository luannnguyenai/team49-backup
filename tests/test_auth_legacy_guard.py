from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status

from src.routers import auth


@pytest.mark.asyncio
async def test_user_skill_overview_guard_blocks_when_legacy_mastery_reads_disabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "allow_legacy_mastery_reads", False)
    monkeypatch.setattr(auth.settings, "allow_legacy_topic_content_reads", True)

    with pytest.raises(HTTPException) as exc_info:
        await auth._build_user_skill_overview(AsyncMock(), user_id="user-id")

    assert exc_info.value.status_code == status.HTTP_410_GONE
    assert "Legacy skill overview is disabled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_user_skill_overview_guard_blocks_when_legacy_topic_reads_disabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "allow_legacy_mastery_reads", True)
    monkeypatch.setattr(auth.settings, "allow_legacy_topic_content_reads", False)

    with pytest.raises(HTTPException) as exc_info:
        await auth._build_user_skill_overview(AsyncMock(), user_id="user-id")

    assert exc_info.value.status_code == status.HTTP_410_GONE
    assert "Legacy skill overview is disabled" in exc_info.value.detail
