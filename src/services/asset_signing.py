import hashlib
import hmac
import time
from urllib.parse import urlencode

from fastapi import HTTPException, status

from src.config import settings

_ASSET_SIGNATURE_CONTEXT = "asset-url:v1"


def _normalize_asset_path(asset_path: str) -> str:
    return asset_path.lstrip("/")


def _build_signature(asset_path: str, expires_at: int) -> str:
    normalized_path = _normalize_asset_path(asset_path)
    payload = f"{_ASSET_SIGNATURE_CONTEXT}:{normalized_path}:{expires_at}".encode("utf-8")
    secret = settings.secret_key.encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def build_signed_asset_url(
    asset_path: str,
    *,
    expires_in_seconds: int | None = None,
    now: float | None = None,
) -> str:
    normalized_path = _normalize_asset_path(asset_path)
    issued_at = int(now if now is not None else time.time())
    ttl = expires_in_seconds or settings.asset_url_expire_seconds
    expires_at = issued_at + ttl
    signature = _build_signature(normalized_path, expires_at)
    query = urlencode({"exp": expires_at, "sig": signature})
    return f"/data/{normalized_path}?{query}"


def verify_signed_asset_url(
    asset_path: str,
    *,
    expires_at: str | None,
    signature: str | None,
    now: float | None = None,
) -> None:
    if not expires_at or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Protected asset URL is missing a valid signature.",
        )

    try:
        expires_at_int = int(expires_at)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Protected asset URL is invalid or expired.",
        ) from exc

    current_time = int(now if now is not None else time.time())
    if expires_at_int < current_time:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Protected asset URL is invalid or expired.",
        )

    expected_signature = _build_signature(asset_path, expires_at_int)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Protected asset URL is invalid or expired.",
        )
