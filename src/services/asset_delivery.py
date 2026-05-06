"""
asset_delivery.py
-----------------
Build asset URLs that point to AWS CloudFront for production deploys.

Local dev keeps using `asset_signing.build_signed_asset_url` (returns `/data/...`).
This module is the production counterpart: when `ASSET_STORAGE_PROVIDER=s3`,
callers should produce a CloudFront URL instead of a local signed URL so the
browser streams directly from CloudFront → S3 (backend never proxies bytes).

Phase 7 scope: unsigned CloudFront URLs.
Signed CloudFront URLs (key pair / private key) can be added later without
changing the public function signature.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from src.config import settings


class AssetDeliveryConfigError(RuntimeError):
    """Raised when CloudFront/S3 configuration is incomplete."""


def _normalize_storage_key(storage_key: str) -> str:
    """
    Reject unsafe storage keys before they hit CloudFront.

    Rules:
    - Must be a non-empty string.
    - Must not start with `/` after normalization.
    - Must not contain `..` segments (path traversal).
    - Must not contain backslashes (Windows-style paths).
    - Must not be schemeful (http://, s3://, ...).
    """
    if not isinstance(storage_key, str) or not storage_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage key must be a non-empty string.",
        )

    cleaned = storage_key.strip().lstrip("/")

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage key must not be empty after normalization.",
        )

    if "\\" in cleaned or "://" in cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage key must be a relative POSIX path.",
        )

    parts = cleaned.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage key must not contain traversal or empty segments.",
        )

    return cleaned


def build_cloudfront_url(storage_key: str) -> str:
    """
    Return an HTTPS CloudFront URL for `storage_key`.

    `storage_key` is expected to be relative to the bucket root, e.g.
    `courses/CS231n/videos/lecture1.mp4`. The function does NOT prepend
    `AWS_S3_PREFIX`; callers are expected to pass the full key.

    Raises:
        AssetDeliveryConfigError: if `cloudfront_domain` is not configured.
        HTTPException(400): if `storage_key` is unsafe.
    """
    domain = settings.cloudfront_domain.strip()
    if not domain:
        raise AssetDeliveryConfigError(
            "CLOUDFRONT_DOMAIN is not configured; cannot build asset URL."
        )

    # Domain stored without scheme; if user accidentally included scheme, strip it.
    if domain.startswith("http://"):
        domain = domain[len("http://") :]
    elif domain.startswith("https://"):
        domain = domain[len("https://") :]
    domain = domain.rstrip("/")

    normalized_key = _normalize_storage_key(storage_key)
    return f"https://{domain}/{normalized_key}"
