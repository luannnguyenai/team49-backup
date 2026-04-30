from __future__ import annotations

import re

from src.schemas.agent import QueryExpansion


SYNONYMS: dict[str, list[str]] = {
    "vit": ["vision transformer"],
    "vision transformer": ["vit"],
    "convnet": ["cnn", "convolutional network"],
    "cnn": ["convnet", "convolutional network"],
    "rf": ["receptive field"],
    "receptive field": ["rf"],
    "word vectors": ["embeddings", "word embeddings"],
    "embeddings": ["word vectors", "word embeddings"],
}


def normalize_query(query: str) -> tuple[str, list[str], list[QueryExpansion]]:
    normalized = re.sub(r"\s+", " ", query.lower()).strip()
    terms = [term for term in re.split(r"[^a-z0-9]+", normalized) if len(term) > 1]
    expansions: list[QueryExpansion] = []
    expanded = set(terms)

    for key, values in SYNONYMS.items():
        if key in normalized:
            expansions.append(
                QueryExpansion(from_term=key, to=values, reason="domain_synonym")
            )
            for value in values:
                expanded.update(term for term in value.split() if len(term) > 1)

    return normalized, sorted(expanded), expansions
