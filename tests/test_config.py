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
    assert settings.model_reasoning_effort == "medium"
    assert settings.model_extra_kwargs == {}
    assert settings.gemini_requests_per_minute == 15


def test_settings_parses_model_extra_kwargs(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    monkeypatch.setenv("MODEL_EXTRA_KWARGS", '{"thinking_budget": 1024}')

    settings = Settings(_env_file=None)

    assert settings.model_extra_kwargs == {"thinking_budget": 1024}


def test_settings_default_guardrail_router_config(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    for env_name in (
        "GUARDRAIL_ROUTER_BASE_URL",
        "GUARDRAIL_ROUTER_MODEL",
        "GUARDRAIL_ROUTER_API_KEY",
        "GUARDRAIL_ROUTER_CF_ACCESS_CLIENT_ID",
        "GUARDRAIL_ROUTER_CF_ACCESS_CLIENT_SECRET",
        "GUARDRAIL_ROUTER_TIMEOUT_SECONDS",
        "GUARDRAIL_ROUTER_UNHEALTHY_COOLDOWN_SECONDS",
        "GUARDRAIL_ROUTER_FALLBACK_PROVIDER",
        "GUARDRAIL_ROUTER_FALLBACK_MODEL",
        "GUARDRAIL_ROUTER_MAX_TOKENS",
    ):
        monkeypatch.delenv(env_name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.guardrail_router_base_url == ""
    assert settings.guardrail_router_model == "guardrail-router-merged"
    assert settings.guardrail_router_api_key == ""
    assert settings.guardrail_router_cf_access_client_id == ""
    assert settings.guardrail_router_cf_access_client_secret == ""
    assert settings.guardrail_router_timeout_seconds == 10.0
    assert settings.guardrail_router_unhealthy_cooldown_seconds == 60.0
    assert settings.guardrail_router_fallback_provider == ""
    assert settings.guardrail_router_fallback_model == ""
    assert settings.guardrail_router_max_tokens == 96


def test_settings_parses_guardrail_router_config(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    monkeypatch.setenv("GUARDRAIL_ROUTER_BASE_URL", "https://router.example.com/v1")
    monkeypatch.setenv("GUARDRAIL_ROUTER_MODEL", "guardrail-router-merged")
    monkeypatch.setenv("GUARDRAIL_ROUTER_API_KEY", "router-token")
    monkeypatch.setenv("GUARDRAIL_ROUTER_CF_ACCESS_CLIENT_ID", "cf-id")
    monkeypatch.setenv("GUARDRAIL_ROUTER_CF_ACCESS_CLIENT_SECRET", "cf-secret")
    monkeypatch.setenv("GUARDRAIL_ROUTER_TIMEOUT_SECONDS", "1.75")
    monkeypatch.setenv("GUARDRAIL_ROUTER_UNHEALTHY_COOLDOWN_SECONDS", "45")
    monkeypatch.setenv("GUARDRAIL_ROUTER_FALLBACK_PROVIDER", "openai")
    monkeypatch.setenv("GUARDRAIL_ROUTER_FALLBACK_MODEL", "gpt-5.4-nano")
    monkeypatch.setenv("GUARDRAIL_ROUTER_MAX_TOKENS", "80")

    settings = Settings(_env_file=None)

    assert settings.guardrail_router_base_url == "https://router.example.com/v1"
    assert settings.guardrail_router_model == "guardrail-router-merged"
    assert settings.guardrail_router_api_key == "router-token"
    assert settings.guardrail_router_cf_access_client_id == "cf-id"
    assert settings.guardrail_router_cf_access_client_secret == "cf-secret"
    assert settings.guardrail_router_timeout_seconds == 1.75
    assert settings.guardrail_router_unhealthy_cooldown_seconds == 45.0
    assert settings.guardrail_router_fallback_provider == "openai"
    assert settings.guardrail_router_fallback_model == "gpt-5.4-nano"
    assert settings.guardrail_router_max_tokens == 80


def test_settings_default_cutover_flags_are_production_canonical(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    for env_name in (
        "WRITE_GOAL_PREFERENCES_ENABLED",
        "WRITE_LEARNER_MASTERY_KP_ENABLED",
        "WRITE_WAIVED_UNITS_ENABLED",
        "WRITE_PLANNER_AUDIT_ENABLED",
        "READ_GOAL_PREFERENCES_ENABLED",
        "READ_LEARNER_MASTERY_KP_ENABLED",
        "READ_CANONICAL_QUESTIONS_ENABLED",
        "WRITE_CANONICAL_INTERACTIONS_ENABLED",
        "READ_CANONICAL_PLANNER_ENABLED",
    ):
        monkeypatch.delenv(env_name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.write_goal_preferences_enabled is True
    assert settings.write_learner_mastery_kp_enabled is True
    assert settings.write_waived_units_enabled is True
    assert settings.write_planner_audit_enabled is True
    assert settings.read_goal_preferences_enabled is True
    assert settings.read_learner_mastery_kp_enabled is True
    assert settings.read_canonical_questions_enabled is True
    assert settings.write_canonical_interactions_enabled is True
    assert settings.read_canonical_planner_enabled is True


def test_settings_parses_cutover_flags_from_env(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    monkeypatch.setenv("WRITE_GOAL_PREFERENCES_ENABLED", "true")
    monkeypatch.setenv("WRITE_LEARNER_MASTERY_KP_ENABLED", "1")
    monkeypatch.setenv("WRITE_WAIVED_UNITS_ENABLED", "TRUE")
    monkeypatch.setenv("WRITE_PLANNER_AUDIT_ENABLED", "yes")
    monkeypatch.setenv("READ_GOAL_PREFERENCES_ENABLED", "true")
    monkeypatch.setenv("READ_LEARNER_MASTERY_KP_ENABLED", "1")
    monkeypatch.setenv("READ_CANONICAL_QUESTIONS_ENABLED", "true")
    monkeypatch.setenv("WRITE_CANONICAL_INTERACTIONS_ENABLED", "1")
    monkeypatch.setenv("READ_CANONICAL_PLANNER_ENABLED", "yes")

    settings = Settings(_env_file=None)

    assert settings.write_goal_preferences_enabled is True
    assert settings.write_learner_mastery_kp_enabled is True
    assert settings.write_waived_units_enabled is True
    assert settings.write_planner_audit_enabled is True
    assert settings.read_goal_preferences_enabled is True
    assert settings.read_learner_mastery_kp_enabled is True
    assert settings.read_canonical_questions_enabled is True
    assert settings.write_canonical_interactions_enabled is True
    assert settings.read_canonical_planner_enabled is True
