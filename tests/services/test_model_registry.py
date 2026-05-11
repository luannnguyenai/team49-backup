from __future__ import annotations

import pytest

from src.services.model_registry import (
    ChatModelUnavailableError,
    build_chat_model_kwargs_for_option,
    check_all_chat_model_availability,
    check_chat_model_health,
    ensure_chat_model_available,
    get_chat_model_option,
    list_chat_model_options,
)


def test_chat_model_registry_exposes_default_and_qwen_options():
    options = list_chat_model_options()

    assert [option.id for option in options] == ["default", "qwen35_4b"]
    assert options[0].is_default is True
    assert options[1].label == "Qwen 3.5 4B"
    assert options[1].base_url == "https://vllm.a20-app-049.io.vn/v1"
    assert options[1].model == "qwen 3.5 4B"


def test_build_kwargs_for_qwen_uses_openai_compatible_base_url():
    kwargs = build_chat_model_kwargs_for_option("qwen35_4b", temperature=0.2)

    assert kwargs["model_provider"] == "openai"
    assert kwargs["model"] == "qwen 3.5 4B"
    assert kwargs["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
    assert kwargs["api_key"] == "EMPTY"
    assert "reasoning" not in kwargs


def test_unknown_chat_model_id_is_rejected():
    with pytest.raises(ValueError, match="unsupported_chat_model"):
        get_chat_model_option("unknown-model")


@pytest.mark.asyncio
async def test_qwen_health_uses_openai_compatible_models_endpoint():
    calls: list[dict[str, object]] = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "qwen 3.5 4B"}]}

    class FakeClient:
        async def get(self, url, **kwargs):
            calls.append({"url": url, **kwargs})
            return FakeResponse()

    result = await check_chat_model_health("qwen35_4b", client=FakeClient())

    assert result["id"] == "qwen35_4b"
    assert result["status"] == "healthy"
    assert result["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
    assert calls[0]["url"] == "https://vllm.a20-app-049.io.vn/v1/models"
    assert calls[0]["headers"] == {"Authorization": "Bearer EMPTY"}


@pytest.mark.asyncio
async def test_chat_model_availability_marks_down_models_unavailable_without_exposing_details():
    calls: list[str] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "gpt-5.4-mini"}]}

    class FakeClient:
        async def get(self, url, **_kwargs):
            calls.append(url)
            if "vllm.a20-app-049.io.vn" in url:
                raise RuntimeError("raw upstream failure with endpoint details")
            return FakeResponse()

    result = await check_all_chat_model_availability(client=FakeClient())

    assert [item["id"] for item in result] == ["default", "qwen35_4b"]
    assert result[0]["available"] is True
    assert result[1]["status"] == "down"
    assert result[1]["available"] is False
    assert "error" not in result[1]
    assert "base_url" not in result[1]
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_ensure_chat_model_available_rejects_down_model():
    class FakeClient:
        async def get(self, *_args, **_kwargs):
            raise RuntimeError("connection refused")

    with pytest.raises(ChatModelUnavailableError) as exc:
        await ensure_chat_model_available("qwen35_4b", client=FakeClient())

    assert exc.value.model_id == "qwen35_4b"
    assert exc.value.status == "down"
