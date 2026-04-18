import hashlib
import hmac

from src.config import settings
from src.services.asset_signing import _build_signature


def test_asset_signature_uses_domain_separated_payload() -> None:
    asset_path = "CS231n/videos/example.mp4"
    expires_at = 1_700_000_300

    expected_legacy_signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        f"{asset_path}:{expires_at}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    actual_signature = _build_signature(asset_path, expires_at)

    assert actual_signature != expected_legacy_signature

