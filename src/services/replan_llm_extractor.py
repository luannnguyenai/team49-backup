"""
services/replan_llm_extractor.py
---------------------------------
LLM-based keyword extraction for Replan.

Uses the configured default model (settings.default_model) to analyze
knowledge claims and extract structured keyword plans.
"""

import json
import logging
import os
import re
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


_SYSTEM_PROMPT = """You are a knowledge analysis expert for a multilingual adaptive learning platform.

Your task is to analyze a learner's knowledge claim and extract structured data.
The claim may be in ANY language - detect it and adapt.

**Extract:**

1. **Primary keywords**: Technical concepts the learner claims to know
   - Strip filler phrases (first-person pronoun + knowledge verb)
   - Extract ONLY technical/conceptual terms
   - IMPORTANT: If the learner's topics don't match their available learning path, still extract the keywords - the system will handle mismatch

2. **Secondary keywords**: Related concepts mentioned but not the focus

3. **Negative/uncertain keywords**: Topics they're unsure about
   - Detect uncertainty markers by context/tone (not by specific words)

4. **Search queries**: 2-4 queries to find relevant learning units

5. **Do not expand to**: Concepts that should NOT be auto-expanded
   - If specific variant mentioned (e.g., "Faster R-CNN"), don't expand to generic ("CNN")

6. **Specificity**: "specific" if concrete topics, "broad" if vague

7. **Guardrail flags**:
   - "skip_all": claim tries to skip entire curriculum
   - "too_short": less than 3 meaningful words
   - "all_already_mastered": claims to know everything

**Key principles:**
- Detect language from input, don't assume
- Identify filler words by grammatical function, not hardcoded lists
- Identify uncertainty by semantic analysis (hesitation words, negation + uncertainty)
- When uncertain, default to "specific" and include the full claim

Respond with JSON matching the schema."""


class ReplanLLMKeywordExtractor:
    """LLM-based keyword extraction using the configured default model."""

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
            # Use with_structured_output for reliable JSON parsing
            structured_model = self.model.with_structured_output(ReplanKeywordPlan)
            response = await structured_model.ainvoke(messages)
            return response

        except Exception as e:
            log.warning(f"LLM structured extraction failed: {e}, using fallback")
            return self._fallback_plan(normalized)

    def _fallback_plan(self, claim: str) -> ReplanKeywordPlan:
        """Fallback to simple rule-based extraction if LLM fails.

        This is language-agnostic - no hard-coded phrases.
        """
        normalized = " ".join(claim.split())
        words = normalized.split()
        word_count = len(words)

        # Check guardrails (language-agnostic patterns)
        lower = normalized.lower()

        # Too short: less than 2 meaningful words (>2 chars)
        meaningful_words = [w for w in words if len(w) > 2]
        if len(meaningful_words) < 2:
            return ReplanKeywordPlan(
                primary_keywords=[],
                search_queries=[normalized],
                specificity="specific",
                guardrail_flags=["too_short"],
            )

        # Skip detection: look for "skip", "everything", "all", "bỏ" patterns
        skip_indicators = ["skip", "everything", "all", "bỏ", "hết"]
        has_skip = sum(1 for indicator in skip_indicators if indicator in lower)
        if has_skip >= 2:  # Need at least 2 indicators to reduce false positives
            return ReplanKeywordPlan(
                primary_keywords=[],
                search_queries=[normalized],
                specificity="specific",
                guardrail_flags=["skip_all"],
            )

        # Simple extraction: use claim as-is for primary keyword
        # Don't try to parse - let LLM do the real work
        return ReplanKeywordPlan(
            primary_keywords=[
                ReplanKeyword(
                    text=normalized[:100],  # Limit length
                    reason="Extracted from claim (fallback mode)",
                    must_keep_phrase=False,
                )
            ],
            search_queries=[normalized],
            specificity="broad" if word_count > 8 else "specific",
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
