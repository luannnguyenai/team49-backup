from __future__ import annotations

import re

from src.services.guardrails.guardrails_adapter import GuardrailsPIIDetector, PIIDetectorAdapter
from src.services.guardrails.pii_policy import get_policy_rule
from src.services.guardrails.types import GuardrailDetectedEntity, GuardrailResult


class PIIGuardrailService:
    def __init__(self, adapter: PIIDetectorAdapter | None = None):
        self.adapter = adapter or GuardrailsPIIDetector()

    def sanitize_input(self, text: str) -> GuardrailResult:
        return self._sanitize(text, failure_mode="fail_open")

    def sanitize_output(self, text: str) -> GuardrailResult:
        return self._sanitize(text, failure_mode="fail_closed")

    def _sanitize(self, text: str, *, failure_mode: str) -> GuardrailResult:
        try:
            entities = self.adapter.detect(text)
        except Exception:
            if failure_mode == "fail_closed":
                return GuardrailResult(
                    sanitizedText="",
                    shouldBlock=True,
                    blockReason="pii_output_scan_failed",
                    errorCode="pii_guardrail_adapter_error",
                )
            return GuardrailResult(
                sanitizedText=text,
                errorCode="pii_guardrail_adapter_error",
            )

        blocked = self._find_blocking_entity(entities)
        if blocked is not None:
            rule = get_policy_rule(blocked.entity_type)
            return GuardrailResult(
                sanitizedText=text,
                detectedEntities=entities,
                shouldBlock=True,
                blockReason=rule.block_reason if rule is not None else "pii_blocked",
            )

        sanitized_text = self._apply_redactions(text, entities)
        return GuardrailResult(
            sanitizedText=sanitized_text,
            detectedEntities=entities,
            wasRedacted=sanitized_text != text,
        )

    def _find_blocking_entity(
        self,
        entities: list[GuardrailDetectedEntity],
    ) -> GuardrailDetectedEntity | None:
        for entity in entities:
            rule = get_policy_rule(entity.entity_type)
            if rule is not None and rule.action == "block":
                return entity
        return None

    def _apply_redactions(self, text: str, entities: list[GuardrailDetectedEntity]) -> str:
        redactions: list[tuple[int, int, str]] = []
        for entity in entities:
            rule = get_policy_rule(entity.entity_type)
            if rule is None or rule.action != "redact" or not rule.placeholder:
                continue
            if self._span_overlaps_url(text, entity.start, entity.end):
                continue
            redactions.append((entity.start, entity.end, rule.placeholder))

        if not redactions:
            return text

        merged: list[tuple[int, int, str]] = []
        for start, end, placeholder in sorted(redactions, key=lambda item: (item[0], item[1])):
            if merged and start < merged[-1][1]:
                continue
            merged.append((start, end, placeholder))

        parts: list[str] = []
        cursor = 0
        for start, end, placeholder in merged:
            parts.append(text[cursor:start])
            parts.append(placeholder)
            cursor = end
        parts.append(text[cursor:])
        return "".join(parts)

    @staticmethod
    def _span_overlaps_url(text: str, start: int, end: int) -> bool:
        for match in re.finditer(r"https?://\S+", text):
            if start < match.end() and end > match.start():
                return True
        return False
