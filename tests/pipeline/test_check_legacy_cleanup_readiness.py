from pathlib import Path

from src.scripts.pipeline.check_legacy_cleanup_readiness import (
    build_cleanup_readiness_report,
    classify_usage_references,
)


def test_cleanup_readiness_blocks_when_runtime_references_remain(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text("from src.models.content import Question\n", encoding="utf-8")

    report = build_cleanup_readiness_report(
        targets=["questions"],
        roots=[tmp_path],
    )

    assert report["status"] == "blocked"
    assert "unguarded_runtime_legacy_references_remain" in report["blockers"]


def test_cleanup_readiness_blocks_when_targets_are_not_safe(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text("from src.models.canonical import QuestionBankItem\n", encoding="utf-8")

    report = build_cleanup_readiness_report(
        targets=["question_bank"],
        roots=[tmp_path],
    )

    assert report["status"] == "blocked"
    assert "cleanup_targets_not_safe" in report["blockers"]


def test_cleanup_readiness_ready_when_targets_and_usage_are_clean(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text("from src.models.canonical import QuestionBankItem\n", encoding="utf-8")

    report = build_cleanup_readiness_report(
        targets=["questions"],
        roots=[tmp_path],
    )

    assert report["status"] == "ready"
    assert report["blockers"] == []


def test_classify_usage_references_marks_guarded_and_model_definition_examples():
    usage_report = {
        "surfaces": [
            {
                "table": "questions",
                "references": [
                    {
                        "path": "/repo/src/services/quiz_service.py",
                        "line": 10,
                        "text": "select(Question)",
                    },
                    {
                        "path": "/repo/src/models/content.py",
                        "line": 159,
                        "text": "class Question",
                    },
                    {
                        "path": "/repo/src/repositories/question_repo.py",
                        "line": 31,
                        "text": "select(Question)",
                    },
                ],
            }
        ]
    }

    result = classify_usage_references(usage_report)

    assert result["guarded_example_count"] == 1
    assert result["accepted_definition_example_count"] == 1
    assert result["unguarded_example_count"] == 1
