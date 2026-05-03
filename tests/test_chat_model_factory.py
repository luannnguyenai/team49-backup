import unittest
from unittest.mock import patch

from src.services.chat_model_factory import build_chat_model_kwargs


class ChatModelFactoryTests(unittest.TestCase):
    def test_openai_provider_includes_openai_api_key(self):
        with patch("src.services.chat_model_factory.settings.model_provider", "openai"), patch(
            "src.services.chat_model_factory.settings.openai_api_key",
            "openai-key",
        ):
            kwargs = build_chat_model_kwargs(
                model="gpt-5.4-mini",
                temperature=0.2,
                max_tokens=1200,
            )

        self.assertEqual(kwargs["model"], "gpt-5.4-mini")
        self.assertEqual(kwargs["model_provider"], "openai")
        self.assertEqual(kwargs["api_key"], "openai-key")
        self.assertEqual(kwargs["max_tokens"], 1200)

    def test_google_provider_uses_gemini_key(self):
        with patch(
            "src.services.chat_model_factory.settings.model_provider",
            "google_genai",
        ), patch(
            "src.services.chat_model_factory.settings.gemini_api_key",
            "gemini-key",
        ):
            kwargs = build_chat_model_kwargs(
                model="gemini-2.5-flash",
                temperature=0,
            )

        self.assertEqual(kwargs["model_provider"], "google_genai")
        self.assertEqual(kwargs["api_key"], "gemini-key")

    def test_missing_key_leaves_api_key_unset(self):
        with patch("src.services.chat_model_factory.settings.model_provider", "openai"), patch(
            "src.services.chat_model_factory.settings.openai_api_key",
            "",
        ):
            kwargs = build_chat_model_kwargs(
                model="gpt-5.4-mini",
                temperature=0.2,
            )

        self.assertNotIn("api_key", kwargs)

    def test_openai_provider_includes_reasoning_effort_when_configured(self):
        with patch("src.services.chat_model_factory.settings.model_provider", "openai"), patch(
            "src.services.chat_model_factory.settings.model_reasoning_effort",
            "medium",
        ), patch(
            "src.services.chat_model_factory.settings.openai_api_key",
            "",
        ):
            kwargs = build_chat_model_kwargs(
                model="gpt-5.4-mini",
                temperature=0.2,
            )

        self.assertEqual(kwargs["reasoning"], {"effort": "medium"})

    def test_non_openai_provider_does_not_get_openai_reasoning_shape(self):
        with patch("src.services.chat_model_factory.settings.model_provider", "google_genai"), patch(
            "src.services.chat_model_factory.settings.model_reasoning_effort",
            "medium",
        ), patch(
            "src.services.chat_model_factory.settings.gemini_api_key",
            "",
        ):
            kwargs = build_chat_model_kwargs(
                model="gemini-3-flash-preview",
                temperature=0,
            )

        self.assertNotIn("reasoning", kwargs)

    def test_model_extra_kwargs_are_provider_neutral(self):
        with patch("src.services.chat_model_factory.settings.model_provider", "google_genai"), patch(
            "src.services.chat_model_factory.settings.model_extra_kwargs",
            {"thinking_budget": 1024},
        ), patch(
            "src.services.chat_model_factory.settings.gemini_api_key",
            "",
        ):
            kwargs = build_chat_model_kwargs(
                model="gemini-3-flash-preview",
                temperature=0,
            )

        self.assertEqual(kwargs["thinking_budget"], 1024)


if __name__ == "__main__":
    unittest.main()
