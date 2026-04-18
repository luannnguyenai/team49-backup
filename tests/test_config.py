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
