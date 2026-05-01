from __future__ import annotations

import re

from src.schemas.agent import QueryExpansion


def normalize_query(query: str) -> tuple[str, list[str], list[QueryExpansion]]:
    normalized = re.sub(r"\s+", " ", query.lower()).strip()
    terms = [term for term in re.split(r"[^a-z0-9]+", normalized) if len(term) > 1]
    expanded = set(terms)
    for compactable in re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)+", normalized):
        parts = [part for part in re.split(r"[-_]+", compactable) if part]
        compacted = re.sub(r"[^a-z0-9]+", "", compactable)
        if len(compacted) > 1:
            expanded.add(compacted)
        if any(len(part) == 1 for part in parts):
            for part in parts:
                expanded.discard(part)

    return normalized, sorted(expanded), []
