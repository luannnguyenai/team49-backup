from __future__ import annotations

from langchain.chat_models import init_chat_model

from src.config import settings
from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_structured_router import StructuredAgentRouter
from src.services.chat_model_factory import build_chat_model_kwargs
from src.services.model_registry import build_chat_model_kwargs_for_option


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
                reasoning_effort=getattr(app_settings, "model_reasoning_effort", None),
                extra_kwargs=getattr(app_settings, "model_extra_kwargs", None),
            )
        )
    except Exception as exc:
        raise AgentRouterUnavailableError("agent_router_model_unavailable") from exc
    return StructuredAgentRouter(model=chat_model)


def build_production_agent_response_router(
    *,
    chat_model_id: str | None = None,
    init_model=init_chat_model,
) -> StructuredAgentRouter:
    try:
        chat_model = init_model(
            **build_chat_model_kwargs_for_option(
                chat_model_id,
                temperature=0.2,
            )
        )
    except ValueError as exc:
        raise AgentRouterUnavailableError("agent_response_model_not_configured") from exc
    except Exception as exc:
        raise AgentRouterUnavailableError("agent_response_model_unavailable") from exc
    return StructuredAgentRouter(model=chat_model)
