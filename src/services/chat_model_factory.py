"""
services/chat_model_factory.py
------------------------------
Shared helpers for constructing LangChain chat model kwargs with the
appropriate provider credential.
"""

from __future__ import annotations

from src.config import settings


class MissingModelCredentialError(RuntimeError):
    pass


_CLOUD_PROVIDER_KEY_LABELS = {
    "openai": "OPENAI_API_KEY",
    "google_genai": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def _resolve_api_key(model_provider: str) -> str:
    provider = model_provider.lower()
    if provider == "openai":
        return settings.openai_api_key
    if provider in {"google_genai", "google", "gemini"}:
        return settings.gemini_api_key
    if provider == "anthropic":
        return settings.anthropic_api_key
    return ""


def build_chat_model_kwargs(
    *,
    model: str,
    temperature: float,
    max_tokens: int | None = None,
    model_provider: str | None = None,
    reasoning_effort: str | None = None,
    extra_kwargs: dict | None = None,
) -> dict:
    provider = model_provider or settings.model_provider
    kwargs = {
        "model": model,
        "model_provider": provider,
        "temperature": temperature,
        "timeout": settings.llm_request_timeout_seconds,
        "max_retries": settings.llm_max_retries,
    }

    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    effort = reasoning_effort if reasoning_effort is not None else settings.model_reasoning_effort
    if provider.lower() == "openai" and effort and effort != "off":
        kwargs["reasoning"] = {"effort": effort}

    configured_extra = dict(getattr(settings, "model_extra_kwargs", {}) or {})
    if configured_extra:
        kwargs.update(configured_extra)
    if extra_kwargs:
        kwargs.update(extra_kwargs)

    api_key = str(kwargs.get("api_key") or _resolve_api_key(provider) or "")
    provider_key_label = _CLOUD_PROVIDER_KEY_LABELS.get(provider.lower())
    if provider_key_label and not api_key:
        raise MissingModelCredentialError(
            f"{provider_key_label} is required for MODEL_PROVIDER={provider}"
        )
    if api_key:
        kwargs["api_key"] = api_key

    return kwargs
