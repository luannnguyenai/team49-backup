import pytest
from fastapi import HTTPException

from src.routers import content


def test_legacy_topic_content_guard_blocks_when_disabled(monkeypatch):
    monkeypatch.setattr(content.settings, "allow_legacy_topic_content_reads", False)

    with pytest.raises(HTTPException) as exc_info:
        content._ensure_legacy_topic_content_reads_allowed()

    assert exc_info.value.status_code == 410
    assert "Legacy module/topic content APIs are disabled" in exc_info.value.detail
