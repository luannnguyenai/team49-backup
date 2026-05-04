from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    def plan(self, claim: str) -> ReplanKeywordPlan:
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

        if any(term in lower for term in ("object detection", "computer vision", "machine learning")):
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
