from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GuardrailDetectedEntity(BaseModel):
    entity_type: str = Field(alias="entityType")
    start: int
    end: int
    text: str
    score: float | None = None

    model_config = ConfigDict(populate_by_name=True)


class GuardrailResult(BaseModel):
    sanitized_text: str = Field(alias="sanitizedText")
    detected_entities: list[GuardrailDetectedEntity] = Field(default_factory=list, alias="detectedEntities")
    was_redacted: bool = Field(default=False, alias="wasRedacted")
    should_block: bool = Field(default=False, alias="shouldBlock")
    block_reason: str | None = Field(default=None, alias="blockReason")
    error_code: str | None = Field(default=None, alias="errorCode")

    model_config = ConfigDict(populate_by_name=True)
