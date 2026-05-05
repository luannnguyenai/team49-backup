"""Tests for the asset-provider switch in learning_unit_service.

These ensure Phase 8 wiring keeps local dev behavior intact while enabling
CloudFront URLs when ASSET_STORAGE_PROVIDER=s3.
"""

from pathlib import Path

import pytest

from src.config import settings
from src.services.learning_unit_service import (
    _resolve_course_asset_url,
    _resolve_transcript_available,
)


@pytest.fixture
def cloudfront_domain(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "cloudfront_domain", "d123.cloudfront.net")
    return "d123.cloudfront.net"


def test_local_mode_returns_signed_url_when_file_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "local")
    fake_file = tmp_path / "video.mp4"
    fake_file.write_bytes(b"")

    url = _resolve_course_asset_url(
        "courses/CS231n/videos/video.mp4", local_disk_path=fake_file
    )

    assert url is not None
    assert url.startswith("/data/courses/CS231n/videos/video.mp4?")
    assert "exp=" in url and "sig=" in url


def test_local_mode_returns_none_when_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "local")
    missing = tmp_path / "missing.mp4"

    url = _resolve_course_asset_url(
        "courses/CS231n/videos/missing.mp4", local_disk_path=missing
    )
    assert url is None


def test_s3_mode_returns_cloudfront_url_without_disk_check(
    monkeypatch: pytest.MonkeyPatch, cloudfront_domain: str, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "s3")
    missing = tmp_path / "does-not-exist.mp4"

    url = _resolve_course_asset_url(
        "courses/CS231n/videos/lecture1.mp4", local_disk_path=missing
    )

    assert url == f"https://{cloudfront_domain}/courses/CS231n/videos/lecture1.mp4"


def test_s3_mode_returns_none_when_cloudfront_domain_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "s3")
    monkeypatch.setattr(settings, "cloudfront_domain", "")

    assert (
        _resolve_course_asset_url(
            "courses/CS231n/videos/lecture1.mp4", local_disk_path=None
        )
        is None
    )


def test_transcript_available_local_requires_disk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "local")
    existing = tmp_path / "t.txt"
    existing.write_text("hello", encoding="utf-8")

    assert _resolve_transcript_available(str(existing)) is True
    assert _resolve_transcript_available(str(tmp_path / "missing.txt")) is False
    assert _resolve_transcript_available(None) is False
    assert _resolve_transcript_available("") is False


def test_transcript_available_s3_trusts_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "asset_storage_provider", "s3")

    assert _resolve_transcript_available("any/path.txt") is True
    assert _resolve_transcript_available(None) is False
    assert _resolve_transcript_available("") is False
