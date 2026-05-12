from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ChatMessageResponse:
    content: str


class OpenAICompatibleHTTPChatModel:
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float,
        timeout: float,
        max_retries: int = 0,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self._client_factory = client_factory or httpx.Client

    def invoke(self, messages: list[Any]) -> ChatMessageResponse:
        payload = {
            "model": self.model,
            "messages": self._normalize_messages(messages),
            "temperature": self.temperature,
            "stream": False,
        }
        return ChatMessageResponse(content=self._post_chat_completions(payload))

    def with_structured_output(self, schema, method: str | None = None, **_kwargs: Any):
        return _StructuredHTTPChatModel(self, schema)

    def _post_chat_completions(self, payload: dict[str, Any]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AI-Learning-Hub/1.0",
        }
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            client = self._client_factory()
            try:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return self._extract_message_content(response.json())
            except Exception as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
        raise RuntimeError("openai_compatible_chat_completion_failed") from last_exc

    @staticmethod
    def _extract_message_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not choices:
            raise ValueError("chat_completion_missing_choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise ValueError("chat_completion_missing_message")
        content = message.get("content")
        if content is None:
            raise ValueError("chat_completion_missing_content")
        return str(content)

    @staticmethod
    def _normalize_messages(messages: list[Any]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for message in messages:
            if isinstance(message, dict):
                role = str(message.get("role") or "user")
                content = message.get("content") or ""
            else:
                role = getattr(message, "role", None) or getattr(message, "type", None) or "user"
                if role == "human":
                    role = "user"
                elif role == "ai":
                    role = "assistant"
                content = getattr(message, "content", message)
            normalized.append({"role": str(role), "content": str(content)})
        return normalized


class _StructuredHTTPChatModel:
    def __init__(self, model: OpenAICompatibleHTTPChatModel, schema) -> None:
        self.model = model
        self.schema = schema

    def invoke(self, messages: list[Any]):
        schema_json = self._schema_json()
        normalized_messages = self.model._normalize_messages(messages)
        system_instruction = (
            "Return only one valid JSON object matching this JSON schema. "
            "Do not include markdown, code fences, or commentary.\n"
            f"JSON schema: {schema_json}"
        )
        if normalized_messages and normalized_messages[0]["role"] == "system":
            payload_messages = [
                {
                    "role": "system",
                    "content": f"{system_instruction}\n\n{normalized_messages[0]['content']}",
                },
                *normalized_messages[1:],
            ]
        else:
            payload_messages = [
                {"role": "system", "content": system_instruction},
                *normalized_messages,
            ]
        content = self.model._post_chat_completions(
            {
                "model": self.model.model,
                "messages": payload_messages,
                "temperature": self.model.temperature,
                "stream": False,
                "response_format": {"type": "json_object"},
            }
        )
        data = self._parse_json_object(content)
        if hasattr(self.schema, "model_validate"):
            return self.schema.model_validate(data)
        return data

    def _schema_json(self) -> str:
        if hasattr(self.schema, "model_json_schema"):
            schema = self.schema.model_json_schema()
        else:
            schema = self.schema
        return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _parse_json_object(content: str) -> dict[str, Any]:
        text = content.strip()
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise
            parsed = json.loads(text[start : end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("structured_chat_output_not_object")
        return parsed
