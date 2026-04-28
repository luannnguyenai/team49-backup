# src/schemas/placement_assessment.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlacementStartRequest(BaseModel):
    """POST /api/placement-assessment/start"""
    topic_unit_ids: list[uuid.UUID] = Field(
        min_length=1,
        description="learning_units.id values selected at onboarding Step 2",
    )


class PlacementQuestion(BaseModel):
    item_id: str
    canonical_unit_id: str
    topic_unit_id: uuid.UUID
    stem_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class PlacementStartResponse(BaseModel):
    session_id: uuid.UUID
    total_questions: int
    questions: list[PlacementQuestion]
    topic_unit_ids: list[uuid.UUID]
    skipped_topics: list[uuid.UUID] = []  # units with no placement items
    should_skip_step: bool = False         # True when ALL requested units have no items


class PlacementAnswerInput(BaseModel):
    item_id: str
    selected_answer: str = Field(pattern="^[ABCD]$")
    topic_unit_id: uuid.UUID


class PlacementSubmitRequest(BaseModel):
    """POST /api/placement-assessment/submit"""
    session_id: uuid.UUID
    answers: list[PlacementAnswerInput] = Field(min_length=1)


class TopicDecision(BaseModel):
    topic_unit_id: uuid.UUID
    score_pct: float
    decision: Literal["skip", "review", "relearn"]
    user_choice: Optional[str] = None


class PlacementSubmitResponse(BaseModel):
    session_id: uuid.UUID
    topic_decisions: list[TopicDecision]
    skipped_count: int
    review_count: int
    relearn_count: int


class PlacementResultsResponse(BaseModel):
    results: list[TopicDecision]
    has_placement: bool


class TopicUserChoiceRequest(BaseModel):
    """PATCH /api/placement-assessment/topic-decision"""
    topic_unit_id: uuid.UUID
    user_choice: str = Field(pattern="^(skip|review)$")
