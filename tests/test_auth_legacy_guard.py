from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.routers import auth


@pytest.mark.asyncio
async def test_user_skill_overview_uses_canonical_when_legacy_mastery_reads_disabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "allow_legacy_mastery_reads", False)
    monkeypatch.setattr(auth.settings, "allow_legacy_topic_content_reads", True)
    monkeypatch.setattr(
        auth,
        "_build_canonical_user_skill_overview",
        AsyncMock(return_value="canonical-skills"),
    )

    result = await auth._build_user_skill_overview(AsyncMock(), user_id="user-id")

    assert result == "canonical-skills"


@pytest.mark.asyncio
async def test_user_skill_overview_uses_canonical_when_legacy_topic_reads_disabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "allow_legacy_mastery_reads", True)
    monkeypatch.setattr(auth.settings, "allow_legacy_topic_content_reads", False)
    monkeypatch.setattr(
        auth,
        "_build_canonical_user_skill_overview",
        AsyncMock(return_value="canonical-skills"),
    )

    result = await auth._build_user_skill_overview(AsyncMock(), user_id="user-id")

    assert result == "canonical-skills"


@pytest.mark.asyncio
async def test_canonical_user_skill_overview_groups_kp_mastery(monkeypatch):
    rows = [
        (
            SimpleNamespace(mastery_mean_cached=0.8),
            SimpleNamespace(name="Transformer language model", domain_tags=["NLP"]),
        ),
        (
            SimpleNamespace(mastery_mean_cached=0.6),
            SimpleNamespace(name="Convolutional networks", domain_tags=["computer vision"]),
        ),
    ]
    db = AsyncMock()
    result = Mock()
    result.all.return_value = rows
    db.execute.return_value = result

    result = await auth._build_canonical_user_skill_overview(db, user_id="user-id")

    by_label = {skill.label: skill for skill in result.skills}
    assert by_label["NLP"].value == 80.0
    assert by_label["Computer Vision"].value == 60.0
