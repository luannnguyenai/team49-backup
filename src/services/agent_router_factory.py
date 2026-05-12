from __future__ import annotations

from langchain.chat_models import init_chat_model

from src.config import settings
from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_structured_router import StructuredAgentRouter
from src.services.chat_model_factory import build_chat_model_kwargs
from src.services.model_registry import build_chat_model_kwargs_for_option, get_chat_model_option
from src.services.openai_compatible_http_chat_model import OpenAICompatibleHTTPChatModel


def _build_fast_model(*, app_settings=settings, init_model=init_chat_model):
    provider = str(app_settings.model_provider or "").strip()
    model = str(app_settings.fast_model or "").strip()
    if not provider or not model:
        return None
    return init_model(
        **build_chat_model_kwargs(
            model=model,
            model_provider=provider,
            temperature=0,
            reasoning_effort=getattr(app_settings, "model_reasoning_effort", None),
            extra_kwargs=getattr(app_settings, "model_extra_kwargs", None),
        )
    )


def build_production_agent_router(
    *,
    app_settings=settings,
    init_model=init_chat_model,
) -> StructuredAgentRouter:
    try:
        chat_model = _build_fast_model(app_settings=app_settings, init_model=init_model)
    except Exception as exc:
        raise AgentRouterUnavailableError("agent_router_model_unavailable") from exc
    if chat_model is None:
        raise AgentRouterUnavailableError("agent_router_model_not_configured")
    return StructuredAgentRouter(model=chat_model)


def build_production_agent_response_router(
    *,
    chat_model_id: str | None = None,
    init_model=init_chat_model,
) -> StructuredAgentRouter:
    try:
        option = get_chat_model_option(chat_model_id)
        if option.base_url:
            chat_model = OpenAICompatibleHTTPChatModel(
                model=option.model,
                base_url=option.base_url,
                api_key=option.api_key or "EMPTY",
                temperature=0.2,
                timeout=settings.llm_request_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        else:
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
