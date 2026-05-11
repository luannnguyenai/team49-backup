from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field, ValidationError

from src.config import settings
from src.services.chat_model_factory import build_chat_model_kwargs


SafetyLabel = Literal["SAFE", "HARMFUL"]
TopicLabel = Literal["ON_TOPIC", "OFF_TOPIC", "AMBIGUOUS", "N_A"]
GuardrailAction = Literal[
    "ALLOW_LESSON_ANSWER",
    "SOFT_REFUSE_REDIRECT",
    "ASK_CLARIFY",
    "SAFETY_REFUSE",
]
AttackType = Literal[
    "none",
    "harmful_request",
    "policy_override",
    "schema_override",
    "role_override",
    "scope_override",
    "kp_injection",
    "obfuscation",
    "jailbreak_template",
    "multilingual_jailbreak",
    "unknown",
]


class GuardrailRouterUnavailableError(RuntimeError):
    def __init__(
        self,
        message: str = "guardrail_router_unavailable",
        error_code: str = "GUARDRAIL_ROUTER_UNAVAILABLE",
    ):
        super().__init__(message)
        self.error_code = error_code


class GuardrailScopePacket(BaseModel):
    feature: Literal["tutor", "agent"]
    scope_level: str
    scope_id: str
    allowed_scope_summary: str = ""
    candidate_kps: list[dict[str, str]] = Field(default_factory=list)
    recent_context: list[dict[str, Any]] = Field(default_factory=list)
    selected_text: str = ""


class GuardrailDecision(BaseModel):
    safety_label: SafetyLabel
    topic_label: TopicLabel
    action: GuardrailAction
    attack_type: AttackType
    selected_kp_ids: list[str] = Field(default_factory=list)

    @classmethod
    def allow(cls) -> "GuardrailDecision":
        return cls(
            safety_label="SAFE",
            topic_label="ON_TOPIC",
            action="ALLOW_LESSON_ANSWER",
            attack_type="none",
            selected_kp_ids=[],
        )


@dataclass(frozen=True)
class GuardrailRouterConfig:
    base_url: str = ""
    model: str = "guardrail-router-merged"
    api_key: str = ""
    cf_access_client_id: str = ""
    cf_access_client_secret: str = ""
    timeout_seconds: float = 2.5
    fallback_provider: str = ""
    fallback_model: str = ""
    fallback_temperature: float = 0.0
    max_tokens: int = 96


ROUTER_SYSTEM_RULES = (
    "You are a lesson-scope safety router.\n"
    "Return exactly one valid JSON object and nothing else.\n"
    "Do not use markdown. Do not explain.\n"
    "Use exactly these 5 keys and no extra keys: "
    "safety_label, topic_label, action, attack_type, selected_kp_ids.\n"
    "Allowed safety_label values: SAFE, HARMFUL.\n"
    "Allowed topic_label values: ON_TOPIC, OFF_TOPIC, AMBIGUOUS, N_A.\n"
    "Allowed action values: ALLOW_LESSON_ANSWER, SOFT_REFUSE_REDIRECT, ASK_CLARIFY, SAFETY_REFUSE.\n"
    "If safety_label is HARMFUL, set topic_label=N_A, action=SAFETY_REFUSE, and selected_kp_ids=[].\n"
    "attack_type is auxiliary metadata and must not override the main safety/action decision."
)


def build_guardrail_prompt(message: str, scope: GuardrailScopePacket) -> str:
    candidate_lines = [
        f"- {item.get('id', '')}: {item.get('text', '')}".strip()
        for item in scope.candidate_kps
        if item.get("id") or item.get("text")
    ]
    recent_context = (
        json.dumps(scope.recent_context, ensure_ascii=False)
        if scope.recent_context
        else ""
    )
    selected_text = scope.selected_text.strip()
    return (
        f"{ROUTER_SYSTEM_RULES}\n\n"
        "### TASK\n"
        "You are a lesson-scope safety router. Return only valid JSON.\n\n"
        "### SCOPE\n"
        f"scope_level: {scope.scope_level}\n"
        f"scope_id: {scope.scope_id}\n"
        "out_of_scope_policy: strict\n"
        f"allowed_scope_summary: {scope.allowed_scope_summary.strip()}\n\n"
        "### CANDIDATE_KPS\n"
        f"{chr(10).join(candidate_lines) if candidate_lines else '- none'}\n\n"
        "### RECENT_CONTEXT\n"
        f"{recent_context}"
        f"{chr(10) if recent_context else ''}\n"
        "### SELECTED_TEXT\n"
        f"{selected_text}"
        f"{chr(10) if selected_text else ''}\n"
        "### USER_QUERY\n"
        f"{message}\n\n"
        "### OUTPUT_JSON"
    )


def guardrail_user_message(decision: GuardrailDecision) -> str:
    if decision.action == "SAFETY_REFUSE":
        return "I cannot help with that request. Please ask a safe question within the lesson scope."
    if decision.action == "SOFT_REFUSE_REDIRECT":
        return "That question is outside the current lesson scope. Please ask about the current lesson."
    if decision.action == "ASK_CLARIFY":
        return "Could you clarify how your question relates to the current lesson?"
    return ""


class GuardrailRouterClient:
    def __init__(
        self,
        config: GuardrailRouterConfig,
        *,
        sync_http_client=None,
        async_http_client=None,
        fallback_model=None,
    ):
        self.config = config
        self.sync_http_client = sync_http_client
        self.async_http_client = async_http_client
        self.fallback_model = fallback_model

    def route_sync(self, *, message: str, scope: GuardrailScopePacket) -> GuardrailDecision:
        errors: list[str] = []
        if self.config.base_url.strip():
            try:
                return self._route_via_http_sync(message=message, scope=scope)
            except Exception as exc:
                errors.append(f"tunnel: {type(exc).__name__}: {exc}")

        try:
            return self._route_via_fallback_model(message=message, scope=scope)
        except Exception as exc:
            errors.append(f"fallback: {type(exc).__name__}: {exc}")

        raise GuardrailRouterUnavailableError("; ".join(errors))

    async def route(self, *, message: str, scope: GuardrailScopePacket) -> GuardrailDecision:
        errors: list[str] = []
        if self.config.base_url.strip():
            try:
                return await self._route_via_http_async(message=message, scope=scope)
            except Exception as exc:
                errors.append(f"tunnel: {type(exc).__name__}: {exc}")

        try:
            return self._route_via_fallback_model(message=message, scope=scope)
        except Exception as exc:
            errors.append(f"fallback: {type(exc).__name__}: {exc}")

        raise GuardrailRouterUnavailableError("; ".join(errors))

    def _route_via_http_sync(self, *, message: str, scope: GuardrailScopePacket) -> GuardrailDecision:
        client = self.sync_http_client or httpx.Client()
        response = client.post(
            self._chat_completions_url(),
            json=self._openai_payload(message, scope),
            headers=self._headers(),
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        return self._parse_openai_response(response.json())

    async def _route_via_http_async(self, *, message: str, scope: GuardrailScopePacket) -> GuardrailDecision:
        if self.async_http_client is not None:
            response = await self.async_http_client.post(
                self._chat_completions_url(),
                json=self._openai_payload(message, scope),
                headers=self._headers(),
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            return self._parse_openai_response(response.json())

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._chat_completions_url(),
                json=self._openai_payload(message, scope),
                headers=self._headers(),
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            return self._parse_openai_response(response.json())

    def _route_via_fallback_model(self, *, message: str, scope: GuardrailScopePacket) -> GuardrailDecision:
        model = self.fallback_model or self._build_fallback_model()
        if model is None:
            raise GuardrailRouterUnavailableError("guardrail_router_fallback_not_configured")
        response = model.invoke([{"role": "user", "content": build_guardrail_prompt(message, scope)}])
        return parse_guardrail_decision(getattr(response, "content", response))

    def _build_fallback_model(self):
        provider = self.config.fallback_provider.strip()
        model = self.config.fallback_model.strip()
        if not provider or not model:
            return None
        return init_chat_model(
            **build_chat_model_kwargs(
                model=model,
                model_provider=provider,
                temperature=self.config.fallback_temperature,
                max_tokens=self.config.max_tokens,
                reasoning_effort="off",
            )
        )

    def _chat_completions_url(self) -> str:
        return self.config.base_url.rstrip("/") + "/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.config.cf_access_client_id:
            headers["CF-Access-Client-Id"] = self.config.cf_access_client_id
        if self.config.cf_access_client_secret:
            headers["CF-Access-Client-Secret"] = self.config.cf_access_client_secret
        return headers

    def _openai_payload(self, message: str, scope: GuardrailScopePacket) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "messages": [{"role": "user", "content": build_guardrail_prompt(message, scope)}],
            "temperature": 0,
            "max_tokens": self.config.max_tokens,
        }

    @staticmethod
    def _parse_openai_response(payload: dict[str, Any]) -> GuardrailDecision:
        content = payload["choices"][0]["message"]["content"]
        return parse_guardrail_decision(content)


def parse_guardrail_decision(value: Any) -> GuardrailDecision:
    text = _guardrail_response_text(value).strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = _normalize_guardrail_decision_payload(parsed)
        return GuardrailDecision.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise GuardrailRouterUnavailableError("guardrail_router_invalid_response") from exc


def _normalize_guardrail_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    attack_type = str(normalized.get("attack_type", "")).strip().lower()
    if attack_type in {"", "n/a", "na", "none"}:
        normalized["attack_type"] = "none"
    return normalized


def _guardrail_response_text(value: Any) -> str:
    if isinstance(value, list):
        text_blocks = [
            str(item.get("text", ""))
            for item in value
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text")
        ]
        if text_blocks:
            return "".join(text_blocks)
    return str(value)


def build_guardrail_config_from_settings(app_settings=settings) -> GuardrailRouterConfig:
    fallback_provider = str(getattr(app_settings, "guardrail_router_fallback_provider", "") or "")
    fallback_model = str(getattr(app_settings, "guardrail_router_fallback_model", "") or "")
    return GuardrailRouterConfig(
        base_url=str(getattr(app_settings, "guardrail_router_base_url", "") or ""),
        model=str(getattr(app_settings, "guardrail_router_model", "guardrail-router-merged") or ""),
        api_key=str(getattr(app_settings, "guardrail_router_api_key", "") or ""),
        cf_access_client_id=str(getattr(app_settings, "guardrail_router_cf_access_client_id", "") or ""),
        cf_access_client_secret=str(getattr(app_settings, "guardrail_router_cf_access_client_secret", "") or ""),
        timeout_seconds=float(getattr(app_settings, "guardrail_router_timeout_seconds", 2.5)),
        fallback_provider=fallback_provider or str(getattr(app_settings, "model_provider", "") or ""),
        fallback_model=fallback_model or str(getattr(app_settings, "fast_model", "") or ""),
        max_tokens=int(getattr(app_settings, "guardrail_router_max_tokens", 96)),
    )


def build_guardrail_router_client(app_settings=settings) -> GuardrailRouterClient:
    return GuardrailRouterClient(build_guardrail_config_from_settings(app_settings))
