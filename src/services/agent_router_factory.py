from __future__ import annotations

from langchain.chat_models import init_chat_model

from src.config import settings
from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_structured_router import StructuredAgentRouter, StructuredRouteOutput
from src.services.chat_model_factory import build_chat_model_kwargs
from src.services.model_registry import build_chat_model_kwargs_for_option, get_chat_model_option
from src.services.openai_compatible_http_chat_model import OpenAICompatibleHTTPChatModel


class _FallbackChatModel:
    def __init__(self, *, primary, fallback=None, primary_schemas=()):
        self.primary = primary
        self.fallback = fallback
        self.primary_schemas = tuple(primary_schemas)

    def invoke(self, messages, **kwargs):
        try:
            return self.primary.invoke(messages, **kwargs)
        except Exception:
            if self.fallback is None:
                raise
            return self.fallback.invoke(messages, **kwargs)

    def with_structured_output(self, schema, method: str | None = None, **kwargs):
        use_primary = not self.primary_schemas or schema in self.primary_schemas
        primary = (
            _with_structured_output(self.primary, schema, method=method, **kwargs)
            if use_primary
            else None
        )
        fallback = _with_structured_output(
            self.fallback or self.primary,
            schema,
            method=method,
            **kwargs,
        )
        return _FallbackStructuredChatModel(primary=primary, fallback=fallback)


class _FallbackStructuredChatModel:
    def __init__(self, *, primary, fallback=None):
        self.primary = primary
        self.fallback = fallback

    def invoke(self, messages):
        try:
            if self.primary is None:
                raise RuntimeError("primary_structured_model_not_configured")
            return self.primary.invoke(messages)
        except Exception:
            if self.fallback is None:
                raise
            return self.fallback.invoke(messages)


def _with_structured_output(model, schema, *, method: str | None = None, **kwargs):
    if method is not None:
        try:
            return model.with_structured_output(schema, method=method, **kwargs)
        except TypeError:
            return model.with_structured_output(schema, **kwargs)
    return model.with_structured_output(schema, **kwargs)


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


def _build_guardrail_http_model(*, app_settings=settings):
    base_url = str(getattr(app_settings, "guardrail_router_base_url", "") or "").strip()
    model = str(getattr(app_settings, "guardrail_router_model", "") or "").strip()
    if not base_url or not model:
        return None
    return OpenAICompatibleHTTPChatModel(
        model=model,
        base_url=base_url,
        api_key=str(getattr(app_settings, "guardrail_router_api_key", "") or ""),
        temperature=0,
        timeout=float(getattr(app_settings, "guardrail_router_timeout_seconds", 10.0)),
        max_retries=int(getattr(app_settings, "llm_max_retries", 0)),
    )


def build_production_agent_router(
    *,
    app_settings=settings,
    init_model=init_chat_model,
) -> StructuredAgentRouter:
    primary_model = _build_guardrail_http_model(app_settings=app_settings)
    try:
        fallback_model = _build_fast_model(app_settings=app_settings, init_model=init_model)
    except Exception as exc:
        raise AgentRouterUnavailableError("agent_router_model_unavailable") from exc
    if primary_model is None and fallback_model is None:
        raise AgentRouterUnavailableError("agent_router_model_not_configured")
    chat_model = (
        _FallbackChatModel(
            primary=primary_model,
            fallback=fallback_model,
            primary_schemas=(StructuredRouteOutput,),
        )
        if primary_model is not None
        else fallback_model
    )
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
