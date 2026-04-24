from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.placement_lite import PlacementLiteStartRequest, PlacementLiteStartResponse
from src.services.placement_lite_service import start_placement_lite_session

placement_lite_router = APIRouter(prefix="/api/placement-lite", tags=["Placement Lite"])


@placement_lite_router.post(
    "/start",
    response_model=PlacementLiteStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def api_start_placement_lite(
    body: PlacementLiteStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> PlacementLiteStartResponse:
    return await start_placement_lite_session(
        db,
        user_id=user.id,
        selected_course_ids=body.selected_course_ids,
        count=body.count,
        max_units=body.max_units,
    )
