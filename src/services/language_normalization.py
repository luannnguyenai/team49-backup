from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

import httpx
from lingua import Language, LanguageDetectorBuilder


DetectedLanguage = Literal["en", "vi", "other"]


@dataclass(frozen=True)
class LanguageNormalizationResult:
    original_text: str
    normalized_text: str
    detected_language: DetectedLanguage
    target_language: Literal["en", "vi"]
    translated: bool = False


class EnglishTranslator(Protocol):
    async def translate_to_english(self, text: str) -> str:
        ...


class GoogleTranslateEnglishTranslator:
    def __init__(
        self,
        *,
        endpoint: str = "https://translate.googleapis.com/translate_a/single",
        timeout_seconds: float = 3.0,
    ):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    async def translate_to_english(self, text: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.endpoint,
                params={
                    "client": "gtx",
                    "sl": "auto",
                    "tl": "en",
                    "dt": "t",
                    "q": text,
                },
            )
            response.raise_for_status()
        payload = response.json()
        translated = "".join(
            segment[0]
            for segment in (payload[0] if payload else [])
            if isinstance(segment, list) and segment
        ).strip()
        return translated or text


class InputLanguageNormalizer:
    def __init__(self, translator: EnglishTranslator | None = None):
        self.translator = translator or GoogleTranslateEnglishTranslator()
        self.detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH,
            Language.VIETNAMESE,
            Language.FRENCH,
            Language.SPANISH,
            Language.GERMAN,
        ).with_minimum_relative_distance(0.2).build()

    async def normalize(self, text: str) -> LanguageNormalizationResult:
        detected = self.detect(text)
        if detected in {"en", "vi"}:
            return LanguageNormalizationResult(
                original_text=text,
                normalized_text=text,
                detected_language=detected,
                target_language=detected,
                translated=False,
            )
        try:
            translated = await self.translator.translate_to_english(text)
        except Exception:
            translated = text
        return LanguageNormalizationResult(
            original_text=text,
            normalized_text=translated,
            detected_language="other",
            target_language="en",
            translated=translated != text,
        )

    def detect(self, text: str) -> DetectedLanguage:
        stripped = (text or "").strip()
        if not stripped:
            return "en"
        language = self.detector.detect_language_of(stripped)
        if language == Language.VIETNAMESE:
            return "vi"
        if language == Language.ENGLISH or language is None:
            return "en"
        return "other"


_default_normalizer: InputLanguageNormalizer | None = None


def get_input_language_normalizer() -> InputLanguageNormalizer:
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = InputLanguageNormalizer()
    return _default_normalizer
