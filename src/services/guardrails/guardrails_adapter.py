from __future__ import annotations

import re
from typing import Protocol

from src.services.guardrails.types import GuardrailDetectedEntity

_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"(?:(?<=\D)|^)(?:\+?\d[\d\-\s().]{7,}\d)(?=\D|$)")
_US_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class PIIDetectorAdapter(Protocol):
    def detect(self, text: str) -> list[GuardrailDetectedEntity]: ...


class GuardrailsPIIDetector:
    """Internal adapter boundary for guardrails-based PII detection.

    This keeps third-party integration isolated from product code. Until the
    optional dependency is installed, a deterministic regex fallback handles the
    core entity types used in tests and initial rollout.
    """

    def detect(self, text: str) -> list[GuardrailDetectedEntity]:
        return _detect_with_regex_fallback(text)


def _detect_with_regex_fallback(text: str) -> list[GuardrailDetectedEntity]:
    entities: list[GuardrailDetectedEntity] = []
    for match in _EMAIL_PATTERN.finditer(text):
        entities.append(
            GuardrailDetectedEntity(
                entityType="EMAIL_ADDRESS",
                start=match.start(),
                end=match.end(),
                text=match.group(0),
            )
        )
    for match in _PHONE_PATTERN.finditer(text):
        entities.append(
            GuardrailDetectedEntity(
                entityType="PHONE_NUMBER",
                start=match.start(),
                end=match.end(),
                text=match.group(0),
            )
        )
    for match in _US_SSN_PATTERN.finditer(text):
        entities.append(
            GuardrailDetectedEntity(
                entityType="US_SSN",
                start=match.start(),
                end=match.end(),
                text=match.group(0),
            )
        )
    return sorted(entities, key=lambda item: (item.start, item.end))
