"""
routers/history.py
------------------
Unified Learning History API.

Endpoints
---------
GET  /api/history                       Paginated session list with summary stats
GET  /api/history/{session_id}/detail   Per-question breakdown for one session

Query params for GET /api/history
-----------------------------------
session_type  : assessment | quiz | module_test  (optional, default = all)
module_id     : UUID                             (optional)
days          : 7 | 30                           (optional, default = all time)
page          : int ≥ 1                          (default 1)
page_size     : int 1–100                        (default 20)

All endpoints require a valid Bearer token.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.learning import SessionType
from src.models.user import User
from src.schemas.history import HistoryResponse, SessionDetailResponse
from src.services.history_service import get_history, get_session_detail

history_router = APIRouter(prefix="/api/history", tags=["History"])


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------

@history_router.get(
    "",
    response_model=HistoryResponse,
    summary="Paginated learning history with summary stats",
    description=(
        "Returns all sessions (assessment, quiz, module_test) for the current user "
        "with aggregate stats (total sessions, avg score, study time, score trend). "
        "Supports filtering by session type, module, and recency window."
    ),
)
async def api_get_history(
    session_type: SessionType | None = Query(
        default=None,
        description="Filter by session type (omit for all types)",
    ),
    module_id: uuid.UUID | None = Query(
        default=None,
        description="Filter by module UUID (matches session.module_id or topic.module_id)",
    ),
    days: int | None = Query(
        default=None,
        ge=1,
        description="Only include sessions started within the last N days (omit for all time)",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> HistoryResponse:
    return await get_history(
        db,
        user.id,
        session_type=session_type,
        module_id=module_id,
        days=days,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# GET /api/history/{session_id}/detail
# ---------------------------------------------------------------------------

@history_router.get(
    "/{session_id}/detail",
    response_model=SessionDetailResponse,
    summary="Per-question breakdown for one completed session",
    description=(
        "Returns all interactions with question data, bloom breakdown across topics, "
        "weak KC names, and detected misconception IDs. "
        "Returns 409 if the session is still in progress."
    ),
)
async def api_get_session_detail(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> SessionDetailResponse:
    return await get_session_detail(db, user.id, session_id)
