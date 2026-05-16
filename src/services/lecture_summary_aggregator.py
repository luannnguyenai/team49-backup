from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.services.chat_model_factory import build_chat_model_kwargs

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You compose a lecture-level summary from ordered unit summaries of a single lecture. "
    "The lecture has no pre-written description in the database; aggregate the unit summaries "
    "below into one coherent overview that a learner can read instead of opening every unit. "
    "Stay strictly within the provided unit content. Do not invent new facts, examples, "
    "rankings, versions, or topics. Do not add follow-up offers or quiz suggestions. "
    "Answer in English or Vietnamese to match the learner question language indicated in the "
    "request; if unsure, mirror the language of the unit summaries. Keep the output concise: "
    "a one or two sentence opener about the lecture's overall arc, then 4 to 8 short bullet "
    "points covering the main ideas in lecture order. No headings. No closing question."
)


class LectureSummaryAggregator:
    def __init__(self, model: Any = None, *, cache: dict[str, str] | None = None):
        self._model = model
        self._cache: dict[str, str] = cache if cache is not None else {}

    @property
    def model(self):
        if self._model is None:
            kwargs = build_chat_model_kwargs(
                model=settings.default_model,
                temperature=0.2,
                max_tokens=900,
            )
            self._model = init_chat_model(**kwargs)
            logger.info(
                "Initialized LectureSummaryAggregator with model: %s",
                settings.default_model,
            )
        return self._model

    async def aggregate(
        self,
        *,
        lecture_title: str | None,
        units: list[dict],
        language_hint: str | None = None,
    ) -> str | None:
        normalized_units = self._normalize_units(units)
        if not normalized_units:
            return None
        cache_key = self._cache_key(lecture_title, normalized_units, language_hint)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        user_payload = {
            "lecture_title": lecture_title,
            "language_hint": language_hint,
            "units": normalized_units,
        }
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
        ]
        try:
            response = await self.model.ainvoke(messages)
        except Exception:
            logger.exception("LectureSummaryAggregator invocation failed")
            return None
        text = self._extract_text(response).strip()
        if not text:
            return None
        self._cache[cache_key] = text
        return text

    @staticmethod
    def _normalize_units(units: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for unit in units or []:
            if not isinstance(unit, dict):
                continue
            summary = unit.get("summary") or unit.get("description")
            if not summary or not str(summary).strip():
                continue
            normalized.append(
                {
                    "canonical_unit_id": unit.get("canonical_unit_id"),
                    "unit_name": unit.get("unit_name"),
                    "ordering_index": unit.get("ordering_index"),
                    "summary": str(summary).strip(),
                }
            )
        return normalized

    @staticmethod
    def _cache_key(
        lecture_title: str | None,
        units: list[dict],
        language_hint: str | None,
    ) -> str:
        payload = {
            "lecture_title": lecture_title,
            "language_hint": language_hint,
            "units": units,
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _extract_text(response: Any) -> str:
        if response is None:
            return ""
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                elif isinstance(part, str):
                    parts.append(part)
            return "\n".join(parts)
        return str(content)
