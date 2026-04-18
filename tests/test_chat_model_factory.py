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


if __name__ == "__main__":
    unittest.main()
