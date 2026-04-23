import pytest

from src.exceptions import ValidationError
from src.services import module_test_service


def test_module_test_question_read_guard_blocks_when_disabled(monkeypatch):
    monkeypatch.setattr(module_test_service.settings, "allow_legacy_question_reads", False)

    with pytest.raises(ValidationError, match="Legacy module-test question reads are disabled"):
        module_test_service._ensure_legacy_module_test_question_reads_allowed()


def test_module_test_mutation_guard_blocks_mastery_when_disabled(monkeypatch):
    monkeypatch.setattr(module_test_service.settings, "allow_legacy_mastery_writes", False)
    monkeypatch.setattr(module_test_service.settings, "allow_legacy_planner_writes", True)

    with pytest.raises(ValidationError, match="Legacy module-test mastery writes are disabled"):
        module_test_service._ensure_legacy_module_test_mutations_allowed()


def test_module_test_mutation_guard_blocks_learning_path_when_disabled(monkeypatch):
    monkeypatch.setattr(module_test_service.settings, "allow_legacy_mastery_writes", True)
    monkeypatch.setattr(module_test_service.settings, "allow_legacy_planner_writes", False)

    with pytest.raises(ValidationError, match="Legacy module-test learning_path writes are disabled"):
        module_test_service._ensure_legacy_module_test_mutations_allowed()
