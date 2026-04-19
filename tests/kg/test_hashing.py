"""Tests for deterministic KG canonical hashing."""

from src.kg.hashing import canonical_hash


def test_nested_dict_key_order_does_not_change_hash() -> None:
    """Nested dict key ordering must not affect canonical hashes."""
    left = {"b": {"y": 2, "x": [3, {"d": 4, "c": 5}]}, "a": 1}
    right = {"a": 1, "b": {"x": [3, {"c": 5, "d": 4}], "y": 2}}

    assert canonical_hash(left) == canonical_hash(right)


def test_list_order_is_stable_and_significant() -> None:
    """List order must be preserved by canonicalization."""
    assert canonical_hash({"items": ["a", "b"]}) == canonical_hash({"items": ["a", "b"]})
    assert canonical_hash({"items": ["a", "b"]}) != canonical_hash({"items": ["b", "a"]})


def test_float_precision_is_stable() -> None:
    """Equivalent float values must hash identically across canonicalization."""
    value = 0.1 + 0.2

    assert canonical_hash({"score": value}) == canonical_hash({"score": 0.30000000000000004})
