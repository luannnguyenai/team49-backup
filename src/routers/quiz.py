"""
routers/quiz.py
---------------
Quiz System API.

Endpoints
---------
POST  /api/quiz/start                    Start a new quiz for a topic
POST  /api/quiz/{session_id}/answer      Submit one answer (real-time feedback)
POST  /api/quiz/{session_id}/complete    Finalize the quiz and get full results
GET   /api/quiz/history                  List past quiz sessions

All endpoints require a valid Bearer token.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.quiz import (
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizCompleteResponse,
    QuizHistoryResponse,
    QuizStartRequest,
    QuizStartResponse,
)
from src.services.quiz_service import (
    answer_question,
    complete_quiz,
    get_quiz_history,
    start_quiz,
)

quiz_router = APIRouter(prefix="/api/quiz", tags=["Quiz"])


# ---------------------------------------------------------------------------
# POST /api/quiz/start
# ---------------------------------------------------------------------------


@quiz_router.post(
    "/start",
    response_model=QuizStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new quiz session for a topic",
    description=(
        "Selects 10 questions (3 Easy · 4 Medium · 3 Hard) filtered by "
        "usage_context='quiz'. Prioritises unanswered and previously-wrong "
        "questions. Excludes questions seen in the last 2 assessment sessions."
    ),
)
async def api_start_quiz(
    body: QuizStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> QuizStartResponse:
    return await start_quiz(db, user.id, body.topic_id)


# ---------------------------------------------------------------------------
# POST /api/quiz/{session_id}/answer
# ---------------------------------------------------------------------------


@quiz_router.post(
    "/{session_id}/answer",
    response_model=QuizAnswerResponse,
    summary="Submit a single answer and receive immediate feedback",
    description=(
        "Records the interaction, grades it, and returns the correct answer "
        "plus explanation. Can be called once per question per session."
    ),
)
async def api_answer_question(
    session_id: uuid.UUID,
    body: QuizAnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> QuizAnswerResponse:
    return await answer_question(db, user.id, session_id, body)


# ---------------------------------------------------------------------------
# POST /api/quiz/{session_id}/complete
# ---------------------------------------------------------------------------


@quiz_router.post(
    "/{session_id}/complete",
    response_model=QuizCompleteResponse,
    summary="Finalize the quiz and compute mastery update",
    description=(
        "Closes the session, applies the EMA mastery formula "
        "(new = old × 0.3 + quiz_score × 0.7), updates bloom_max_achieved, "
        "detects new misconceptions, and auto-completes the learning-path item "
        "if mastery ≥ 76%."
    ),
)
async def api_complete_quiz(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> QuizCompleteResponse:
    return await complete_quiz(db, user.id, session_id)


# ---------------------------------------------------------------------------
# GET /api/quiz/history
# ---------------------------------------------------------------------------


@quiz_router.get(
    "/history",
    response_model=QuizHistoryResponse,
    summary="List past quiz sessions for the current user",
)
async def api_quiz_history(
    topic_id: uuid.UUID | None = Query(
        default=None,
        description="Filter by topic UUID (optional)",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> QuizHistoryResponse:
    return await get_quiz_history(db, user.id, topic_id)
