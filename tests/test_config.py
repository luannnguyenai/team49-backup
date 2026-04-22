import pytest


def test_settings_parses_csv_cors_origins(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:3000, http://127.0.0.1:3000 ,http://localhost:8000",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]


def test_settings_parses_json_cors_origins(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["http://localhost:3000","http://localhost:8000"]',
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://localhost:8000",
    ]


def test_settings_default_tutor_models(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("FAST_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_REQUESTS_PER_MINUTE", raising=False)

    settings = Settings(_env_file=None)

    assert settings.default_model == "gpt-5.4-mini"
    assert settings.fast_model == "gpt-5.4-nano"
    assert settings.model_provider == "openai"
    assert settings.gemini_requests_per_minute == 15
