from src.routers import content


def test_legacy_topic_content_guard_allows_canonical_compat_when_disabled(monkeypatch):
    monkeypatch.setattr(content.settings, "allow_legacy_topic_content_reads", False)

    assert content._use_canonical_content_compat() is True
