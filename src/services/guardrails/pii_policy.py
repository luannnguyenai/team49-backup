from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PIIPolicyRule:
    action: str
    placeholder: str | None = None
    block_reason: str | None = None


REDACTION_POLICY: dict[str, PIIPolicyRule] = {
    "EMAIL_ADDRESS": PIIPolicyRule(action="redact", placeholder="[REDACTED_EMAIL]"),
    "PHONE_NUMBER": PIIPolicyRule(action="redact", placeholder="[REDACTED_PHONE]"),
    "PERSON": PIIPolicyRule(action="redact", placeholder="[REDACTED_PERSON]"),
    "LOCATION": PIIPolicyRule(action="redact", placeholder="[REDACTED_LOCATION]"),
    "US_SSN": PIIPolicyRule(action="block", block_reason="pii_blocked_us_ssn"),
    "CREDIT_CARD": PIIPolicyRule(action="block", block_reason="pii_blocked_credit_card"),
    "US_BANK_NUMBER": PIIPolicyRule(action="block", block_reason="pii_blocked_bank_number"),
    "US_PASSPORT": PIIPolicyRule(action="block", block_reason="pii_blocked_passport"),
}


def get_policy_rule(entity_type: str) -> PIIPolicyRule | None:
    return REDACTION_POLICY.get(entity_type)
