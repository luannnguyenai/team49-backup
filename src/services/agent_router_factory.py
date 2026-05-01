from __future__ import annotations

from langchain.chat_models import init_chat_model

from src.config import settings
from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_structured_router import StructuredAgentRouter
from src.services.chat_model_factory import build_chat_model_kwargs


def build_production_agent_router(
    *,
    app_settings=settings,
    init_model=init_chat_model,
) -> StructuredAgentRouter:
    provider = str(app_settings.model_provider or "").strip()
    model = str(app_settings.fast_model or "").strip()
    if not provider or not model:
        raise AgentRouterUnavailableError("agent_router_model_not_configured")
    try:
        chat_model = init_model(
            **build_chat_model_kwargs(
                model=model,
                model_provider=provider,
                temperature=0,
            )
        )
    except Exception as exc:
        raise AgentRouterUnavailableError("agent_router_model_unavailable") from exc
    return StructuredAgentRouter(model=chat_model)
