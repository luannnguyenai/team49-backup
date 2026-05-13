from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from src.config import settings
from src.services.chat_model_factory import build_chat_model_kwargs

DEFAULT_CHAT_MODEL_ID = "default"
QWEN35_4B_CHAT_MODEL_ID = "qwen35_4b"
QWEN35_08B_MODEL_ID = "qwen35_08b"

_HEALTH_CACHE_TTL_SECONDS = 60.0
_health_cache: dict[str, tuple[float, dict]] = {}
_health_cache_lock = threading.Lock()


class ChatModelUnavailableError(Exception):
    def __init__(self, *, model_id: str, label: str, status: str) -> None:
        self.model_id = model_id
        self.label = label
        self.status = status
        super().__init__(f"chat_model_unavailable:{model_id}:{status}")

    def public_detail(self) -> dict[str, str]:
        return {
            "code": "chat_model_unavailable",
            "modelId": self.model_id,
            "label": self.label,
            "status": self.status,
        }


@dataclass(frozen=True)
class ChatModelOption:
    id: str
    label: str
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    is_default: bool = False
    user_selectable: bool = True

    def public_dict(self) -> dict[str, str | bool | None]:
        return {
            "id": self.id,
            "label": self.label,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "is_default": self.is_default,
        }


def list_chat_model_options(*, include_non_selectable: bool = False) -> list[ChatModelOption]:
    options: list[ChatModelOption] = [
        ChatModelOption(
            id=DEFAULT_CHAT_MODEL_ID,
            label="Default",
            provider=settings.model_provider,
            model=settings.default_model,
            is_default=True,
        ),
        ChatModelOption(
            id=QWEN35_4B_CHAT_MODEL_ID,
            label="Qwen 3.5 4B",
            provider="openai",
            model=settings.qwen35_4b_model,
            base_url=settings.qwen35_4b_base_url.rstrip("/"),
            api_key=settings.qwen35_4b_api_key or "EMPTY",
        ),
    ]
    if include_non_selectable:
        guardrail_base_url = settings.guardrail_router_base_url.strip().rstrip("/")
        guardrail_api_key = settings.guardrail_router_api_key or "EMPTY"
        if guardrail_base_url:
            options.append(
                ChatModelOption(
                    id=QWEN35_08B_MODEL_ID,
                    label="Qwen 3.5 0.8B (Guardrail)",
                    provider="openai",
                    model=settings.guardrail_router_model,
                    base_url=guardrail_base_url,
                    api_key=guardrail_api_key,
                    user_selectable=False,
                )
            )
    return options


def list_user_selectable_model_options() -> list[ChatModelOption]:
    return [opt for opt in list_chat_model_options() if opt.user_selectable]


def get_chat_model_option(model_id: str | None) -> ChatModelOption:
    normalized = (model_id or DEFAULT_CHAT_MODEL_ID).strip() or DEFAULT_CHAT_MODEL_ID
    for option in list_chat_model_options(include_non_selectable=True):
        if option.id == normalized:
            return option
    raise ValueError(f"unsupported_chat_model:{normalized}")


def build_chat_model_kwargs_for_option(
    model_id: str | None,
    *,
    temperature: float,
    max_tokens: int | None = None,
) -> dict:
    option = get_chat_model_option(model_id)
    extra_kwargs: dict[str, str] = {}
    reasoning_effort = settings.model_reasoning_effort
    if option.base_url:
        extra_kwargs["base_url"] = option.base_url
        extra_kwargs["api_key"] = option.api_key or "EMPTY"
        reasoning_effort = "off"

    return build_chat_model_kwargs(
        model=option.model,
        temperature=temperature,
        max_tokens=max_tokens,
        model_provider=option.provider,
        reasoning_effort=reasoning_effort,
        extra_kwargs=extra_kwargs,
    )


def _model_health_base_url(option: ChatModelOption) -> str | None:
    if option.base_url:
        return option.base_url.rstrip("/")
    if option.provider.lower() == "openai":
        return "https://api.openai.com/v1"
    return None


def _model_health_api_key(option: ChatModelOption) -> str:
    if option.base_url:
        return option.api_key or "EMPTY"
    if option.provider.lower() == "openai":
        return settings.openai_api_key
    return ""


def _health_payload(
    option: ChatModelOption,
    *,
    status: str,
    latency_ms: int | None,
    error: str | None,
) -> dict:
    payload = option.public_dict()
    payload.update(
        {
            "status": status,
            "latency_ms": latency_ms,
            "checked_at": datetime.now(UTC).isoformat(),
            "error": error,
            "user_selectable": option.user_selectable,
        }
    )
    return payload


async def check_chat_model_health(
    model_id: str | None,
    *,
    timeout_s: float | None = None,
    client=None,
) -> dict:
    option = get_chat_model_option(model_id)
    effective_timeout_s = (
        timeout_s if timeout_s is not None else settings.chat_model_health_timeout_seconds
    )
    base_url = _model_health_base_url(option)
    if not base_url:
        return _health_payload(
            option,
            status="degraded",
            latency_ms=None,
            error=f"health_check_not_supported_for_provider:{option.provider}",
        )

    api_key = _model_health_api_key(option)
    if option.provider.lower() == "openai" and not api_key:
        return _health_payload(
            option,
            status="down",
            latency_ms=None,
            error="missing_model_api_key",
        )

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    owns_client = client is None
    http_client = client or httpx.AsyncClient()
    started = time.perf_counter()
    try:
        response = await http_client.get(
            f"{base_url}/models",
            headers=headers,
            timeout=effective_timeout_s,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        model_ids = {
            str(item.get("id")) for item in data or [] if isinstance(item, dict) and item.get("id")
        }
        status = "healthy"
        error = None
        if model_ids and option.model not in model_ids:
            status = "degraded"
            error = "model_not_listed"
        return _health_payload(option, status=status, latency_ms=latency_ms, error=error)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return _health_payload(
            option,
            status="down",
            latency_ms=latency_ms,
            error=str(exc)[:240],
        )
    finally:
        if owns_client:
            await http_client.aclose()


async def check_all_chat_model_health(*, timeout_s: float | None = None, client=None) -> list[dict]:
    return [
        await check_chat_model_health(option.id, timeout_s=timeout_s, client=client)
        for option in list_chat_model_options(include_non_selectable=True)
    ]


def _availability_payload(health: dict) -> dict:
    status = str(health.get("status") or "down")
    return {
        "id": health["id"],
        "label": health["label"],
        "status": status,
        "available": status != "down",
        "checked_at": health.get("checked_at"),
        "user_selectable": health.get("user_selectable", True),
    }


async def check_all_chat_model_availability(
    *, timeout_s: float | None = None, client=None
) -> list[dict]:
    return [
        _availability_payload(health)
        for health in await check_all_chat_model_health(timeout_s=timeout_s, client=client)
    ]


def _cached_health(model_id: str) -> dict | None:
    now = time.monotonic()
    with _health_cache_lock:
        entry = _health_cache.get(model_id)
        if entry is None:
            return None
        cached_at, cached_health = entry
        if now - cached_at > _HEALTH_CACHE_TTL_SECONDS:
            del _health_cache[model_id]
            return None
        return cached_health


def _store_cached_health(model_id: str, health: dict) -> None:
    with _health_cache_lock:
        _health_cache[model_id] = (time.monotonic(), health)


async def _check_health_cached(model_id: str) -> dict:
    cached = _cached_health(model_id)
    if cached is not None:
        return cached
    health = await check_chat_model_health(model_id)
    _store_cached_health(model_id, health)
    return health


async def ensure_chat_model_available(
    model_id: str | None,
    *,
    timeout_s: float | None = None,
    client=None,
) -> ChatModelOption:
    option = get_chat_model_option(model_id)
    health = await _check_health_cached(option.id)
    if health.get("status") != "down":
        return option

    tried = {option.id}
    for fallback_option in list_chat_model_options(include_non_selectable=False):
        if fallback_option.id in tried:
            continue
        if not fallback_option.user_selectable:
            continue
        fallback_health = await _check_health_cached(fallback_option.id)
        if fallback_health.get("status") != "down":
            return fallback_option

    raise ChatModelUnavailableError(
        model_id=option.id,
        label=option.label,
        status=str(health.get("status") or "down"),
    )
