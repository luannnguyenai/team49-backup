"""
services/replan_llm_extractor.py
---------------------------------
LLM-based keyword extraction for Replan.

Uses GPT-5.4-mini with thinking mode to analyze knowledge claims
and extract structured keyword plans.
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


_SYSTEM_PROMPT = """You are a knowledge analysis expert for an adaptive learning platform.

Your task is to analyze a learner's knowledge claim and extract:
1. **Primary keywords**: Specific concepts/topics the learner claims to know (strip phrases like "Tôi biết", "I know", "Tôi đã nắm rõ")
2. **Secondary keywords**: Related concepts mentioned but not the focus
3. **Negative/uncertain keywords**: Topics the learner explicitly says they DON'T know or are unsure about (phrases like "chưa chắc", "not sure", "không biết")
4. **Search queries**: 2-4 queries to find relevant learning units
5. **Do not expand to**: Concepts that should NOT be auto-expanded (e.g., if they say "Faster R-CNN" specifically, don't expand to generic "CNN")
6. **Specificity**: "specific" if claim mentions concrete topics, "broad" if vague
7. **Guardrail flags**:
   - "skip_all": if claim tries to skip entire curriculum
   - "too_short": if claim is less than 3 meaningful words (excluding "Tôi biết", "I know")
   - "all_already_mastered": if claim says they already know everything

**IMPORTANT for Vietnamese claims:**
- Strip Vietnamese filler words: "Tôi biết", "Tôi đã biết", "Tôi đã nắm rõ", "Tôi hiểu về"
- Extract technical terms even if mixed with Vietnamese
- "chưa chắc", "không chắc" → uncertain keyword
- "skip tất cả", "bỏ hết" → skip_all guardrail

**Examples:**

Claim: "I know Faster R-CNN and CNN feature extraction"
- primary: [{"text": "Faster R-CNN", "reason": "Explicitly mentioned", "mustKeepPhrase": true}]
- secondary: [{"text": "CNN feature extraction", "reason": "Related concept mentioned"}]
- search_queries: ["Faster R-CNN", "CNN feature extraction", "Faster R-CNN object detection"]
- do_not_expand_to: ["CNN", "R-CNN"]
- specificity: "specific"

Claim: "Tôi biết Faster R-CNN và CNN feature extraction"
- primary: [{"text": "Faster R-CNN", "reason": "Explicitly mentioned", "mustKeepPhrase": true}]
- secondary: [{"text": "CNN feature extraction", "reason": "Related concept"}]
- search_queries: ["Faster R-CNN", "CNN feature extraction"]
- specificity: "specific"

Claim: "Tôi biết Faster R-CNN nhưng YOLO chưa chắc"
- primary: [{"text": "Faster R-CNN", "reason": "Explicitly claimed", "mustKeepPhrase": true}]
- negative_or_uncertain_keywords: [{"text": "YOLO", "reason": "User explicitly unsure about YOLO"}]
- specificity: "specific"

Claim: "I already mastered everything, just skip it all"
- guardrail_flags: ["skip_all"]

Claim: "Tôi biết hết rồi, skip tất cả đi"
- guardrail_flags: ["skip_all"]

Claim: "CNN" or "YOLO"
- guardrail_flags: ["too_short"]

Claim: "I know object detection stuff"
- primary: [{"text": "object detection", "reason": "Main claim"}]
- specificity: "broad"

Claim: "Tôi biết object detection cơ bản"
- primary: [{"text": "object detection", "reason": "Main topic claimed"}]
- specificity: "broad"

Claim: "Tôi đã biết CNN, R-CNN, và Faster R-CNN"
- primary: [
    {"text": "CNN", "reason": "Listed as known"},
    {"text": "R-CNN", "reason": "Listed as known"},
    {"text": "Faster R-CNN", "reason": "Listed as known"}
  ]
- specificity: "specific"

Respond with JSON matching the schema. Be precise with keyword extraction - strip filler words."""


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
            # Use with_structured_output for reliable JSON parsing
            structured_model = self.model.with_structured_output(ReplanKeywordPlan)
            response = await structured_model.ainvoke(messages)
            return response

        except Exception as e:
            log.warning(f"LLM structured extraction failed: {e}, using fallback")
            return self._fallback_plan(normalized)

        except Exception as e:
            log.error(f"LLM extraction failed for claim '{claim[:50]}...': {e}")
            return self._fallback_plan(normalized)

    def _fallback_plan(self, claim: str) -> ReplanKeywordPlan:
        """Fallback to rule-based extraction if LLM fails."""
        normalized = " ".join(claim.split())
        lower = normalized.lower()

        # Vietnamese filler words to strip
        vi_prefixes = [
            "tôi biết", "tôi đã biết", "tôi đã nắm rõ", "tôi hiểu về",
            "i know", "i already know", "i mastered"
        ]

        # Check guardrails first
        word_count = len([w for w in normalized.split() if len(w) > 2])
        if word_count < 2:
            return ReplanKeywordPlan(
                primary_keywords=[],
                search_queries=[claim],
                specificity="specific",
                guardrail_flags=["too_short"],
            )

        if any(
            phrase in lower
            for phrase in (
                "skip all", "skip it all", "skip tất cả", "bỏ hết",
                "đã biết hết", "biết tất cả", "biết hết rồi", "mastered everything"
            )
        ):
            return ReplanKeywordPlan(
                primary_keywords=[],
                search_queries=[claim],
                specificity="specific",
                guardrail_flags=["skip_all"],
            )

        # Extract uncertain keywords
        uncertain_keywords = []
        if "chưa chắc" in lower or "not sure" in lower or "không chắc" in lower:
            # Find what comes after uncertain marker
            uncertain_match = re.search(r'(?:chưa chắc|not sure|không chắc)[^\w]*(.+?)(?:,|\.|$)', lower, re.IGNORECASE)
            if uncertain_match:
                uncertain_text = uncertain_match.group(1).strip()
                if len(uncertain_text) > 2:
                    uncertain_keywords.append(
                        ReplanUncertainKeyword(
                            text=uncertain_text[:50],  # Limit length
                            reason="User expressed uncertainty",
                        )
                    )

        # Strip Vietnamese filler words to extract primary keyword
        main_text = normalized
        for prefix in vi_prefixes:
            if main_text.lower().startswith(prefix):
                main_text = main_text[len(prefix):].strip()
                break

        # Clean up common Vietnamese filler at end
        main_text = re.sub(r'^(rồi|đã|về|cơ bản|nhưng|khiếncủa)', '', main_text, flags=re.IGNORECASE).strip()

        # If still too long, take first meaningful phrase
        if len(main_text.split()) > 6:
            # Take first 3-5 words as primary keyword
            words = main_text.split()
            main_text = " ".join(words[:min(5, len(words))])

        # Determine specificity
        broad_indicators = [
            "cơ bản", "basic", "stuff", "things", "general",
            "object detection", "computer vision", "machine learning"
        ]
        is_broad = any(indicator in lower for indicator in broad_indicators)

        # Build search queries
        search_queries = [normalized, main_text]
        if "," in main_text:
            # Add split terms
            parts = [p.strip() for p in main_text.split(",")]
            search_queries.extend(parts[:3])

        return ReplanKeywordPlan(
            primary_keywords=[
                ReplanKeyword(
                    text=main_text,
                    reason="Extracted from claim",
                    must_keep_phrase=True,
                )
            ]
            if main_text
            else [],
            negative_or_uncertain_keywords=uncertain_keywords,
            search_queries=search_queries[:5],
            specificity="broad" if is_broad else "specific",
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
