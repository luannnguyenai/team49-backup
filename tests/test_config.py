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


def test_settings_default_cutover_flags_disabled(monkeypatch: pytest.MonkeyPatch):
    from src.config import Settings

    for env_name in (
        "WRITE_GOAL_PREFERENCES_ENABLED",
        "WRITE_LEARNER_MASTERY_KP_ENABLED",
        "WRITE_WAIVED_UNITS_ENABLED",
        "WRITE_PLANNER_AUDIT_ENABLED",
        "READ_GOAL_PREFERENCES_ENABLED",
        "READ_LEARNER_MASTERY_KP_ENABLED",
        "ALLOW_LEGACY_QUESTION_READS",
        "ALLOW_LEGACY_MASTERY_READS",
        "ALLOW_LEGACY_MASTERY_WRITES",
        "ALLOW_LEGACY_PLANNER_WRITES",
        "ALLOW_LEGACY_TOPIC_CONTENT_READS",
        "ALLOW_LEGACY_KG_ROUTES",
    ):
        monkeypatch.delenv(env_name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.write_goal_preferences_enabled is False
    assert settings.write_learner_mastery_kp_enabled is False
    assert settings.write_waived_units_enabled is False
    assert settings.write_planner_audit_enabled is False
    assert settings.read_goal_preferences_enabled is False
    assert settings.read_learner_mastery_kp_enabled is False
    assert settings.read_canonical_questions_enabled is False
    assert settings.write_canonical_interactions_enabled is False
    assert settings.read_canonical_planner_enabled is False
    assert settings.allow_legacy_question_reads is True
    assert settings.allow_legacy_mastery_reads is True
    assert settings.allow_legacy_mastery_writes is True
    assert settings.allow_legacy_planner_writes is True
    assert settings.allow_legacy_topic_content_reads is True
    assert settings.allow_legacy_kg_routes is True


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
    monkeypatch.setenv("ALLOW_LEGACY_QUESTION_READS", "false")
    monkeypatch.setenv("ALLOW_LEGACY_MASTERY_READS", "0")
    monkeypatch.setenv("ALLOW_LEGACY_MASTERY_WRITES", "0")
    monkeypatch.setenv("ALLOW_LEGACY_PLANNER_WRITES", "FALSE")
    monkeypatch.setenv("ALLOW_LEGACY_TOPIC_CONTENT_READS", "no")
    monkeypatch.setenv("ALLOW_LEGACY_KG_ROUTES", "false")

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
    assert settings.allow_legacy_question_reads is False
    assert settings.allow_legacy_mastery_reads is False
    assert settings.allow_legacy_mastery_writes is False
    assert settings.allow_legacy_planner_writes is False
    assert settings.allow_legacy_topic_content_reads is False
    assert settings.allow_legacy_kg_routes is False
