from pathlib import Path

from src.scripts.pipeline.check_legacy_schema_usage import iter_python_files, scan_legacy_usage


def test_scan_legacy_usage_reports_deprecated_references(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text(
        "from src.models.content import Question\n"
        "async def load():\n"
        "    return 'questions'\n",
        encoding="utf-8",
    )

    report = scan_legacy_usage([tmp_path], max_per_surface=10, excluded_parts=set())

    question_surface = next(surface for surface in report["surfaces"] if surface["table"] == "questions")
    assert report["status"] == "blocked"
    assert question_surface["reference_count"] == 2
    assert question_surface["references"][0]["path"] == str(source.resolve())


def test_scan_legacy_usage_ready_when_no_legacy_references(tmp_path: Path):
    source = tmp_path / "canonical_service.py"
    source.write_text(
        "from src.models.canonical import QuestionBankItem\n"
        "def load():\n"
        "    return QuestionBankItem\n",
        encoding="utf-8",
    )

    report = scan_legacy_usage([tmp_path], excluded_parts=set())

    assert report["status"] == "ready"
    assert report["deprecated_reference_count"] == 0


def test_iter_python_files_skips_default_excluded_parts(tmp_path: Path):
    included = tmp_path / "src" / "service.py"
    included.parent.mkdir()
    included.write_text("print('ok')\n", encoding="utf-8")
    excluded = tmp_path / "src" / "__pycache__" / "service.py"
    excluded.parent.mkdir()
    excluded.write_text("print('skip')\n", encoding="utf-8")

    files = iter_python_files([tmp_path / "src"])

    assert files == [included.resolve()]
