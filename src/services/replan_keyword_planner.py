from __future__ import annotations

import logging
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

log = logging.getLogger(__name__)

# Environment toggle for LLM integration
USE_LLM_FOR_REPLAN = os.getenv("USE_LLM_FOR_REPLAN", "true").lower() == "true"


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


class ReplanKeywordPlanner:
    """Keyword planner with LLM-based extraction or rule-based fallback."""

    def __init__(self, use_llm: bool = USE_LLM_FOR_REPLAN):
        self.use_llm = use_llm
        self._llm_extractor = None

    async def plan(self, claim: str) -> ReplanKeywordPlan:
        """Plan keywords from a knowledge claim.

        Uses LLM if enabled, otherwise falls back to rule-based extraction.
        """
        if self.use_llm:
            return self._allow_compact_claim(claim, await self._plan_with_llm(claim))
        return self._allow_compact_claim(claim, self._plan_rule_based(claim))

    def _allow_compact_claim(self, claim: str, plan: ReplanKeywordPlan) -> ReplanKeywordPlan:
        """Let searchable compact claims reach unit search and LLM unit selection."""
        if "too_short" not in plan.guardrail_flags or _is_too_short_for_search(claim):
            return plan

        normalized = " ".join(claim.split())
        guardrail_flags = [flag for flag in plan.guardrail_flags if flag != "too_short"]
        primary_keywords = plan.primary_keywords or [
            ReplanKeyword(
                text=normalized,
                reason="User provided a compact technical concept.",
                mustKeepPhrase=True,
            ),
        ]
        search_queries = plan.search_queries or [normalized]

        return plan.model_copy(
            update={
                "primary_keywords": primary_keywords,
                "search_queries": search_queries,
                "guardrail_flags": guardrail_flags,
                "specificity": "specific",
            },
        )

    async def _plan_with_llm(self, claim: str) -> ReplanKeywordPlan:
        """Use LLM for keyword extraction."""
        if self._llm_extractor is None:
            from src.services.replan_llm_extractor import get_llm_extractor

            self._llm_extractor = get_llm_extractor()

        return await self._llm_extractor.extract(claim)

    def _plan_rule_based(self, claim: str) -> ReplanKeywordPlan:
        """Rule-based keyword extraction (fallback)."""
        normalized = " ".join(claim.split())
        lower = normalized.lower()
        if "faster rcnn" in lower or "faster r-cnn" in lower:
            uncertain = []
            if "yolo" in lower and ("chưa chắc" in lower or "not sure" in lower):
                uncertain.append(
                    ReplanUncertainKeyword(
                        text="YOLO",
                        reason="User explicitly says they are not confident.",
                    ),
                )
            return ReplanKeywordPlan(
                primaryKeywords=[
                    ReplanKeyword(
                        text="Faster R-CNN",
                        reason="User explicitly claims Faster RCNN knowledge.",
                        mustKeepPhrase=True,
                    ),
                ],
                secondaryKeywords=[],
                negativeOrUncertainKeywords=uncertain,
                searchQueries=["Faster R-CNN", '"Faster R-CNN" object detection', "Faster RCNN"],
                doNotExpandTo=["R-CNN", "CNN"],
                specificity="specific",
                guardrailFlags=[],
            )

        if any(
            term in lower for term in ("object detection", "computer vision", "machine learning")
        ):
            return ReplanKeywordPlan(
                primaryKeywords=[
                    ReplanKeyword(
                        text=normalized,
                        reason="User made a broad but usable knowledge claim.",
                    ),
                ],
                searchQueries=[normalized, lower, "object detection"],
                specificity="broad",
            )

        return ReplanKeywordPlan(
            primaryKeywords=[
                ReplanKeyword(
                    text=normalized,
                    reason="User made a specific knowledge claim.",
                    mustKeepPhrase=True,
                ),
            ],
            searchQueries=[normalized],
            specificity="specific",
        )


def _is_too_short_for_search(claim: str) -> bool:
    compact = "".join(claim.split())
    return len(compact) < 2
