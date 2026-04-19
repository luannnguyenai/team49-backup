"""Canonical hashing helpers for KG sync comparisons."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel


def _normalize(obj: Any) -> Any:
    """Normalize Python objects into JSON-serializable canonical values."""
    if isinstance(obj, BaseModel):
        return _normalize(obj.model_dump(mode="json"))
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Mapping):
        return {str(key): _normalize(value) for key, value in obj.items()}
    if isinstance(obj, tuple | list):
        return [_normalize(value) for value in obj]
    if isinstance(obj, set | frozenset):
        normalized = [_normalize(value) for value in obj]
        return sorted(normalized, key=lambda value: json.dumps(value, sort_keys=True))
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("canonical_hash does not support NaN or infinite floats")
        return 0.0 if obj == 0 else obj
    if isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray):
        return [_normalize(value) for value in obj]
    return obj


def canonical_hash(obj: Any) -> str:
    """Return a sha256 hex digest of canonicalized JSON.

    Canonicalization uses sorted object keys, compact separators, UTF-8 bytes,
    finite JSON float rendering, and preserved list ordering.

    Args:
        obj: JSON-like value, Pydantic model, or nested structure to hash.

    Returns:
        SHA-256 hex digest of the canonical JSON representation.
    """
    payload = json.dumps(
        _normalize(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
