from pathlib import Path

from src.scripts.pipeline.check_legacy_cleanup_readiness import build_cleanup_readiness_report


def test_cleanup_readiness_blocks_when_runtime_references_remain(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text("from src.models.content import Question\n", encoding="utf-8")

    report = build_cleanup_readiness_report(
        targets=["questions"],
        roots=[tmp_path],
    )

    assert report["status"] == "blocked"
    assert "runtime_legacy_references_remain" in report["blockers"]


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
