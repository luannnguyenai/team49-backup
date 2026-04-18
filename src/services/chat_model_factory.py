"""
services/chat_model_factory.py
------------------------------
Shared helpers for constructing LangChain chat model kwargs with the
appropriate provider credential.
"""

from __future__ import annotations

from src.config import settings


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
) -> dict:
    provider = model_provider or settings.model_provider
    kwargs = {
        "model": model,
        "model_provider": provider,
        "temperature": temperature,
    }

    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    api_key = _resolve_api_key(provider)
    if api_key:
        kwargs["api_key"] = api_key

    return kwargs
