"""
routers/replan.py
-----------------
Replan Production E2E API:

    POST /api/replan/analyze           Analyze knowledge claim against real current path
    POST /api/replan/assessment/start  Start assessment with exact unit+difficulty filters
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.replan import (
    ReplanAnalyzeRequest,
    ReplanAnalyzeResponse,
    ReplanAssessmentStartRequest,
    ReplanAssessmentStartResponse,
)
from src.services.replan_service import analyze_replan, start_replan_assessment

replan_router = APIRouter(prefix="/api/replan", tags=["Replan"])


# ---------------------------------------------------------------------------
# POST /api/replan/analyze
# ---------------------------------------------------------------------------


@replan_router.post(
    "/analyze",
    response_model=ReplanAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a knowledge claim against the user's real current learning path",
    description=(
        "Takes the user's natural-language knowledge claim, runs keyword planning, "
        "discovers matching units in the current learning path, identifies prerequisites, "
        "and returns real review scope with question counts by difficulty."
    ),
)
async def api_replan_analyze(
    body: ReplanAnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ReplanAnalyzeResponse:
    result = await analyze_replan(db, user.id, body.claim)
    return result


# ---------------------------------------------------------------------------
# POST /api/replan/assessment/start
# ---------------------------------------------------------------------------


@replan_router.post(
    "/assessment/start",
    response_model=ReplanAssessmentStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a replan assessment with exact unit and difficulty filters",
    description=(
        "Creates a real assessment session for the selected canonical units, "
        "filtering questions by the per-unit difficulty ceiling chosen by the user. "
        "Returns session ID and assessment href for the existing /assessment page."
    ),
)
async def api_replan_assessment_start(
    body: ReplanAssessmentStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ReplanAssessmentStartResponse:
    result = await start_replan_assessment(db, user.id, body.selected_units)
    await db.commit()
    return result
