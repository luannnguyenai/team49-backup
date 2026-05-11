from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services.model_registry import check_all_chat_model_availability


chat_models_router = APIRouter(prefix="/api/chat-models", tags=["chat-models"])


@chat_models_router.get("/availability")
async def chat_model_availability() -> dict[str, list[dict[str, Any]]]:
    return {"models": await check_all_chat_model_availability()}
