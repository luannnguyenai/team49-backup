"""
routers/learning_path.py
-------------------------
Learning Path / Recommendation Engine API.

Endpoints
---------
POST  /api/learning-path/generate        Generate (or regenerate) the personalised path
GET   /api/learning-path                 Current user's full path
GET   /api/learning-path/timeline        Weekly timeline breakdown
PUT   /api/learning-path/{path_id}/status Update status of one path item

All endpoints require a valid Bearer token.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.learning_path import (
    GeneratePathRequest,
    GeneratePathResponse,
    LearningPathResponse,
    PathItemResponse,
    TimelineResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
    WeekEntry,
)
from src.services.recommendation_engine import (
    generate_learning_path,
    get_learning_path,
    get_learning_path_timeline,
    update_path_status,
)

learning_path_router = APIRouter(
    prefix="/api/learning-path",
    tags=["Learning Path"],
)


# ---------------------------------------------------------------------------
# POST /api/learning-path/generate
# ---------------------------------------------------------------------------


@learning_path_router.post(
    "/generate",
    response_model=GeneratePathResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalised learning path",
    description=(
        "Runs the rule-based recommendation engine: topological sort of topics "
        "by prerequisites, mastery-based action assignment, timeline binpacking. "
        "Replaces any existing path for this user."
    ),
)
async def api_generate_learning_path(
    body: GeneratePathRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> GeneratePathResponse:
    return await generate_learning_path(db, user, body)


# ---------------------------------------------------------------------------
# GET /api/learning-path
# ---------------------------------------------------------------------------


@learning_path_router.get(
    "",
    response_model=LearningPathResponse,
    summary="Get the current user's full learning path",
)
async def api_get_learning_path(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> LearningPathResponse:
    rows = await get_learning_path(db, user.id)

    items: list[PathItemResponse] = [
        PathItemResponse(
            id=lp.id,
            learning_unit_id=lp.learning_unit_id,
            learning_unit_title=topic_name,
            section_title=module_name,
            action=lp.action,
            estimated_hours=lp.estimated_hours,
            order_index=lp.order_index,
            week_number=lp.week_number,
            status=lp.status,
            canonical_unit_id=lp.canonical_unit_id,
        )
        for lp, topic_name, module_name in rows
    ]

    from src.models.learning import PathStatus

    return LearningPathResponse(
        total_topics=len(items),
        completed_topics=sum(1 for i in items if i.status == PathStatus.completed),
        in_progress_topics=sum(1 for i in items if i.status == PathStatus.in_progress),
        items=items,
    )


# ---------------------------------------------------------------------------
# GET /api/learning-path/timeline
# ---------------------------------------------------------------------------


@learning_path_router.get(
    "/timeline",
    response_model=TimelineResponse,
    summary="Get the weekly timeline breakdown",
    description=(
        "Returns topics grouped by their assigned calendar week. "
        "Skipped topics (week_number IS NULL) are excluded."
    ),
)
async def api_get_timeline(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> TimelineResponse:
    grouped = await get_learning_path_timeline(db, user.id)

    week_entries: list[WeekEntry] = []
    for week_num in sorted(grouped.keys()):
        rows = grouped[week_num]
        week_items: list[PathItemResponse] = [
            PathItemResponse(
                id=lp.id,
                learning_unit_id=lp.learning_unit_id,
                learning_unit_title=topic_name,
                section_title=module_name,
                action=lp.action,
                estimated_hours=lp.estimated_hours,
                order_index=lp.order_index,
                week_number=lp.week_number,
                status=lp.status,
                canonical_unit_id=lp.canonical_unit_id,
            )
            for lp, topic_name, module_name in rows
        ]
        total_hours = round(sum(i.estimated_hours or 0.0 for i in week_items), 4)
        week_entries.append(
            WeekEntry(
                week=week_num,
                topics=week_items,
                total_hours=total_hours,
            )
        )

    return TimelineResponse(
        total_weeks=len(week_entries),
        items=week_entries,
    )


# ---------------------------------------------------------------------------
# PUT /api/learning-path/{path_id}/status
# ---------------------------------------------------------------------------


@learning_path_router.put(
    "/{path_id}/status",
    response_model=UpdateStatusResponse,
    summary="Update the status of a learning path item",
    description="Allowed transitions: pending → in_progress → completed | skipped.",
)
async def api_update_status(
    path_id: uuid.UUID,
    body: UpdateStatusRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UpdateStatusResponse:
    lp = await update_path_status(db, user.id, path_id, body.status)
    return UpdateStatusResponse(
        id=lp.id,
        learning_unit_id=lp.learning_unit_id,
        status=lp.status,
        updated_at=lp.updated_at,
    )
