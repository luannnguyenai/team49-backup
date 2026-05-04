from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import MagicMock

import pytest

from src.core import observability as obs


def test_get_langfuse_handler_returns_none_without_keys(monkeypatch: pytest.MonkeyPatch):
    obs.get_langfuse_handler.cache_clear()
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(obs.settings, "langfuse_public_key", "")
    monkeypatch.setattr(obs.settings, "langfuse_secret_key", "")

    assert obs.get_langfuse_handler() is None


def test_build_langfuse_metadata_omits_empty_values():
    metadata = obs.build_langfuse_metadata(
        user_id="",
        session_id=None,
        tags=["tutor", "", "streaming"],
        feature="tutor",
        route=None,
        lecture_id="lec-1",
        context_binding_id="",
    )

    assert metadata == {
        "langfuse_tags": ["tutor", "streaming"],
        "feature": "tutor",
        "lecture_id": "lec-1",
    }


def test_build_langfuse_metadata_preserves_domain_fields():
    metadata = obs.build_langfuse_metadata(
        user_id="user-1",
        session_id="session-1",
        tags=["assessment", "summary"],
        feature="assessment",
        assessment_session_id="asm-1",
        route="summary",
    )

    assert metadata["langfuse_user_id"] == "user-1"
    assert metadata["langfuse_session_id"] == "session-1"
    assert metadata["langfuse_tags"] == ["assessment", "summary"]
    assert metadata["feature"] == "assessment"
    assert metadata["assessment_session_id"] == "asm-1"
    assert metadata["route"] == "summary"


def test_propagate_langfuse_attributes_noops_when_no_values():
    with obs.propagate_langfuse_attributes() as propagated:
        assert propagated is None


def test_start_langfuse_root_span_noops_without_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(obs, "get_langfuse_client", lambda: None)

    with obs.start_langfuse_root_span(name="tutor-request") as span:
        assert span is None


def test_start_langfuse_observation_noops_without_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(obs, "get_langfuse_client", lambda: None)

    with obs.start_langfuse_observation(name="tutor-fetch-context") as span:
        assert span is None


def test_score_trace_noops_when_client_unavailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(obs, "get_langfuse_client", lambda: None)

    assert obs.score_trace(trace_id="trace-1", name="user-feedback", value=1.0) is False


def test_score_trace_targets_trace_when_trace_id_present(monkeypatch: pytest.MonkeyPatch):
    fake_client = MagicMock()
    monkeypatch.setattr(obs, "get_langfuse_client", lambda: fake_client)

    assert (
        obs.score_trace(
            trace_id="trace-1",
            name="user-feedback",
            value=1.0,
            data_type="NUMERIC",
            comment="helpful",
        )
        is True
    )

    fake_client.create_score.assert_called_once_with(
        trace_id="trace-1",
        observation_id=None,
        name="user-feedback",
        value=1.0,
        data_type="NUMERIC",
        comment="helpful",
    )
