import pytest

from src.services.language_normalization import (
    InputLanguageNormalizer,
    LanguageNormalizationResult,
)


class FakeTranslator:
    def __init__(self):
        self.calls = []

    async def translate_to_english(self, text: str) -> str:
        self.calls.append(text)
        return "Explain attention mechanisms in neural networks."


@pytest.mark.parametrize(
    ("text", "expected_language"),
    [
        ("Giải thích attention mechanism trong neural network.", "vi"),
        ("Explain attention mechanisms in neural networks.", "en"),
    ],
)
@pytest.mark.asyncio
async def test_language_normalizer_keeps_english_and_vietnamese(text, expected_language):
    translator = FakeTranslator()
    normalizer = InputLanguageNormalizer(translator=translator)

    result = await normalizer.normalize(text)

    assert result == LanguageNormalizationResult(
        original_text=text,
        normalized_text=text,
        detected_language=expected_language,
        target_language=expected_language,
        translated=False,
    )
    assert translator.calls == []


@pytest.mark.parametrize(
    "text",
    [
        "Explique les mécanismes d’attention dans les réseaux neuronaux.",
        "Explica los mecanismos de atención en redes neuronales.",
        "Erkläre Attention-Mechanismen in neuronalen Netzen.",
    ],
)
@pytest.mark.asyncio
async def test_language_normalizer_translates_third_language_to_english(text):
    translator = FakeTranslator()
    normalizer = InputLanguageNormalizer(translator=translator)

    result = await normalizer.normalize(text)

    assert result == LanguageNormalizationResult(
        original_text=text,
        normalized_text="Explain attention mechanisms in neural networks.",
        detected_language="other",
        target_language="en",
        translated=True,
    )
    assert translator.calls == [text]


@pytest.mark.asyncio
async def test_language_normalizer_defaults_short_uncertain_text_to_english():
    translator = FakeTranslator()
    normalizer = InputLanguageNormalizer(translator=translator)

    result = await normalizer.normalize("ok")

    assert result.detected_language == "en"
    assert result.normalized_text == "ok"
    assert result.translated is False
    assert translator.calls == []
