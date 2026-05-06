import pytest
from fastapi import HTTPException

from src.config import settings
from src.services.asset_delivery import (
    AssetDeliveryConfigError,
    _normalize_storage_key,
    build_cloudfront_url,
)


@pytest.fixture
def cloudfront_domain(monkeypatch: pytest.MonkeyPatch) -> str:
    domain = "d123.cloudfront.net"
    monkeypatch.setattr(settings, "cloudfront_domain", domain)
    return domain


def test_build_cloudfront_url_returns_https_url(cloudfront_domain: str) -> None:
    url = build_cloudfront_url("courses/CS231n/videos/lecture1.mp4")
    assert url == f"https://{cloudfront_domain}/courses/CS231n/videos/lecture1.mp4"


def test_build_cloudfront_url_strips_scheme_in_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "cloudfront_domain", "https://cdn.example.com/")
    url = build_cloudfront_url("courses/x.mp4")
    assert url == "https://cdn.example.com/courses/x.mp4"


def test_build_cloudfront_url_strips_leading_slash(cloudfront_domain: str) -> None:
    url = build_cloudfront_url("/courses/x.mp4")
    assert url == f"https://{cloudfront_domain}/courses/x.mp4"


def test_build_cloudfront_url_requires_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "cloudfront_domain", "")
    with pytest.raises(AssetDeliveryConfigError):
        build_cloudfront_url("courses/x.mp4")


@pytest.mark.parametrize(
    "bad_key",
    [
        "",
        "   ",
        "..",
        "../etc/passwd",
        "courses/../secret.mp4",
        "courses//x.mp4",
        "courses/./x.mp4",
        "https://evil.com/x.mp4",
        "s3://bucket/x.mp4",
        "courses\\windows\\x.mp4",
    ],
)
def test_build_cloudfront_url_rejects_unsafe_keys(
    cloudfront_domain: str, bad_key: str
) -> None:
    with pytest.raises(HTTPException) as exc:
        build_cloudfront_url(bad_key)
    assert exc.value.status_code == 400


def test_normalize_storage_key_rejects_non_string() -> None:
    with pytest.raises(HTTPException):
        _normalize_storage_key(None)  # type: ignore[arg-type]
