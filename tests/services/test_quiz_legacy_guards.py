import pytest

from src.exceptions import ValidationError
from src.services import quiz_service


def test_quiz_question_read_guard_blocks_when_disabled(monkeypatch):
    monkeypatch.setattr(quiz_service.settings, "allow_legacy_question_reads", False)

    with pytest.raises(ValidationError, match="Legacy quiz question reads are disabled"):
        quiz_service._ensure_legacy_quiz_question_reads_allowed()


def test_quiz_mutation_guard_blocks_mastery_when_disabled(monkeypatch):
    monkeypatch.setattr(quiz_service.settings, "allow_legacy_mastery_writes", False)
    monkeypatch.setattr(quiz_service.settings, "allow_legacy_planner_writes", True)

    with pytest.raises(ValidationError, match="Legacy quiz mastery writes are disabled"):
        quiz_service._ensure_legacy_quiz_mutations_allowed()


def test_quiz_mutation_guard_blocks_learning_path_when_disabled(monkeypatch):
    monkeypatch.setattr(quiz_service.settings, "allow_legacy_mastery_writes", True)
    monkeypatch.setattr(quiz_service.settings, "allow_legacy_planner_writes", False)

    with pytest.raises(ValidationError, match="Legacy quiz learning_path writes are disabled"):
        quiz_service._ensure_legacy_quiz_mutations_allowed()
