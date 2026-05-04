"""
services/replan_llm_extractor.py
---------------------------------
LLM-based keyword extraction for Replan.

Uses GPT-5.4-mini with thinking mode to analyze knowledge claims
and extract structured keyword plans.
"""

import logging
import os
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field

from src.config import settings
from src.services.chat_model_factory import build_chat_model_kwargs

log = logging.getLogger(__name__)

# Environment toggle for LLM integration
USE_LLM_FOR_REPLAN = os.getenv("USE_LLM_FOR_REPLAN", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------


class ReplanKeyword(BaseModel):
    text: str
    reason: str
    must_keep_phrase: bool = Field(default=False, alias="mustKeepPhrase")

    model_config = ConfigDict(populate_by_name=True)


class ReplanUncertainKeyword(BaseModel):
    text: str
    reason: str


class ReplanKeywordPlan(BaseModel):
    primary_keywords: list[ReplanKeyword] = Field(alias="primaryKeywords")
    secondary_keywords: list[ReplanKeyword] = Field(default_factory=list, alias="secondaryKeywords")
    negative_or_uncertain_keywords: list[ReplanUncertainKeyword] = Field(
        default_factory=list,
        alias="negativeOrUncertainKeywords",
    )
    search_queries: list[str] = Field(alias="searchQueries")
    do_not_expand_to: list[str] = Field(default_factory=list, alias="doNotExpandTo")
    specificity: Literal["specific", "broad"]
    guardrail_flags: list[str] = Field(default_factory=list, alias="guardrailFlags")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# LLM-based extractor
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = """You are a knowledge analysis expert for an adaptive learning platform.

Your task is to analyze a learner's knowledge claim and extract:
1. **Primary keywords**: Specific concepts/topics the learner claims to know
2. **Secondary keywords**: Related concepts mentioned but not the focus
3. **Negative/uncertain keywords**: Topics the learner explicitly says they DON'T know or are unsure about
4. **Search queries**: 2-4 queries to find relevant learning units
5. **Do not expand to**: Concepts that should NOT be auto-expanded (e.g., if they say "Faster R-CNN" specifically, don't expand to generic "CNN")
6. **Specificity**: "specific" if claim mentions concrete topics, "broad" if vague
7. **Guardrail flags**:
   - "skip_all": if claim tries to skip entire curriculum
   - "too_short": if claim is less than 3 meaningful words
   - "all_already_mastered": if claim says they already know everything

**Examples:**

Claim: "I know Faster R-CNN and CNN feature extraction"
- primary: [{"text": "Faster R-CNN", "reason": "Explicitly mentioned", "mustKeepPhrase": true}]
- secondary: [{"text": "CNN feature extraction", "reason": "Related concept mentioned"}]
- search_queries: ["Faster R-CNN", "CNN feature extraction", "Faster R-CNN object detection"]
- do_not_expand_to: ["CNN", "R-CNN"]  # They know Faster R-CNN specifically, don't expand
- specificity: "specific"

Claim: "I already mastered everything, just skip it all"
- guardrail_flags: ["skip_all"]

Claim: "YOLO"
- guardrail_flags: ["too_short"]

Claim: "I know object detection stuff"
- primary: [{"text": "object detection", "reason": "Main claim"}]
- specificity: "broad"
- search_queries: ["object detection", "computer vision object detection"]

Respond with JSON matching the schema."""


class ReplanLLMKeywordExtractor:
    """LLM-based keyword extraction using GPT-4.1-mini with thinking."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        """Lazy-load the model."""
        if self._model is None:
            kwargs = build_chat_model_kwargs(
                model=settings.default_model,
                temperature=0.3,  # Low temperature for consistent extraction
                max_tokens=2000,
                reasoning_effort="medium",  # Thinking mode
            )
            self._model = init_chat_model(**kwargs)
            log.info(f"Initialized Replan LLM extractor with model: {settings.default_model}")
        return self._model

    async def extract(self, claim: str) -> ReplanKeywordPlan:
        """Extract keywords from a knowledge claim using LLM.

        Args:
            claim: User's natural language knowledge claim

        Returns:
            ReplanKeywordPlan with extracted keywords and metadata
        """
        # Normalize claim
        normalized = " ".join(claim.split())

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f'Analyze this knowledge claim: "{normalized}"'),
        ]

        try:
            response = await self.model.ainuce(messages)

            # Parse structured response
            # OpenAI with reasoning returns content directly
            if hasattr(response, "content"):
                content = response.content
            else:
                content = str(response)

            # Try to parse as JSON
            import json

            try:
                data = json.loads(content)
                return ReplanKeywordPlan(**data)
            except json.JSONDecodeError:
                log.warning(f"LLM returned non-JSON response, using fallback: {content[:100]}")
                return self._fallback_plan(normalized)

        except Exception as e:
            log.error(f"LLM extraction failed for claim '{claim[:50]}...': {e}")
            return self._fallback_plan(normalized)

    def _fallback_plan(self, claim: str) -> ReplanKeywordPlan:
        """Fallback to simple keyword extraction if LLM fails."""
        lower = claim.lower()

        # Check guardrails
        if len(claim.split()) < 3:
            return ReplanKeywordPlan(
                primary_keywords=[],
                search_queries=[claim],
                specificity="specific",
                guardrail_flags=["too_short"],
            )

        if any(
            phrase in lower
            for phrase in (
                "skip all",
                "skip it all",
                "bỏ hết",
                "đã biết hết",
                "biết tất cả",
            )
        ):
            return ReplanKeywordPlan(
                primary_keywords=[],
                search_queries=[claim],
                specificity="specific",
                guardrail_flags=["skip_all"],
            )

        # Simple extraction: first few words as primary keyword
        words = claim.split()
        if len(words) <= 4:
            primary_text = claim
        else:
            primary_text = " ".join(words[:4])

        return ReplanKeywordPlan(
            primary_keywords=[
                ReplanKeyword(
                    text=primary_text,
                    reason="Extracted from claim",
                    must_keep_phrase=True,
                )
            ],
            search_queries=[claim, primary_text],
            specificity="specific" if len(words) <= 6 else "broad",
            guardrail_flags=[],
        )


# Singleton instance
_llm_extractor: ReplanLLMKeywordExtractor | None = None


def get_llm_extractor() -> ReplanLLMKeywordExtractor:
    """Get or create the singleton LLM extractor instance."""
    global _llm_extractor
    if _llm_extractor is None:
        _llm_extractor = ReplanLLMKeywordExtractor()
    return _llm_extractor
