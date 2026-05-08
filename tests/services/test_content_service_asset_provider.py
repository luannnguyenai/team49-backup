import uuid
from types import SimpleNamespace

import pytest

from src.config import settings
from src.services.content_service import _canonical_unit_video_url

pytestmark = pytest.mark.anyio


class _ScalarResult:
    def __init__(self, asset: SimpleNamespace | None) -> None:
        self._asset = asset

    def scalar_one_or_none(self) -> SimpleNamespace | None:
        return self._asset


class _FakeDb:
    def __init__(self, asset: SimpleNamespace | None) -> None:
        self._asset = asset

    async def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self._asset)


def _unit() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


async def test_content_video_url_uses_cloudfront_for_s3_storage_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "s3")
    monkeypatch.setattr(settings, "cloudfront_domain", "d123.cloudfront.net")
    asset = SimpleNamespace(
        delivery_url=None,
        storage_key="courses/CS231n/videos/lecture1.mp4",
    )

    video_url = await _canonical_unit_video_url(_FakeDb(asset), _unit(), None)

    assert video_url == "https://d123.cloudfront.net/courses/CS231n/videos/lecture1.mp4"


async def test_content_video_url_uses_signed_data_url_for_local_storage_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "local")
    asset = SimpleNamespace(
        delivery_url=None,
        storage_key="courses/CS231n/videos/lecture1.mp4",
    )

    video_url = await _canonical_unit_video_url(_FakeDb(asset), _unit(), None)

    assert video_url is not None
    assert video_url.startswith("/data/courses/CS231n/videos/lecture1.mp4?")
    assert "exp=" in video_url
    assert "sig=" in video_url


async def test_content_video_url_prefers_explicit_delivery_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "s3")
    asset = SimpleNamespace(
        delivery_url="https://media.example.com/prebuilt.mp4",
        storage_key="courses/CS231n/videos/lecture1.mp4",
    )

    video_url = await _canonical_unit_video_url(_FakeDb(asset), _unit(), None)

    assert video_url == "https://media.example.com/prebuilt.mp4"
