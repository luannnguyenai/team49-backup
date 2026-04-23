from pathlib import Path

from src.scripts.pipeline.check_legacy_schema_usage import iter_python_files, scan_legacy_usage


def test_scan_legacy_usage_reports_deprecated_references(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text(
        "from src.models.content import Question\n"
        "async def load():\n"
        "    # questions per topic should not count as a DB dependency\n",
        encoding="utf-8",
    )

    report = scan_legacy_usage([tmp_path], max_per_surface=10, excluded_parts=set())

    question_surface = next(surface for surface in report["surfaces"] if surface["table"] == "questions")
    assert report["status"] == "blocked"
    assert question_surface["reference_count"] == 1
    assert question_surface["references"][0]["path"] == str(source.resolve())


def test_scan_legacy_usage_reports_sql_table_references(tmp_path: Path):
    source = tmp_path / "kg_loader.py"
    source.write_text(
        'stmt = "SELECT * FROM topics t JOIN modules m ON m.id = t.module_id"\n',
        encoding="utf-8",
    )

    report = scan_legacy_usage([tmp_path], max_per_surface=10, excluded_parts=set())

    topic_surface = next(surface for surface in report["surfaces"] if surface["table"] == "topics")
    module_surface = next(surface for surface in report["surfaces"] if surface["table"] == "modules")
    assert topic_surface["reference_count"] == 1
    assert module_surface["reference_count"] == 1


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


def test_iter_python_files_skips_config_and_pipeline_scripts(tmp_path: Path):
    config = tmp_path / "src" / "config.py"
    config.parent.mkdir()
    config.write_text("ALLOW_LEGACY_QUESTION_READS = True\n", encoding="utf-8")
    script = tmp_path / "src" / "scripts" / "pipeline" / "export.py"
    script.parent.mkdir(parents=True)
    script.write_text("LEGACY_TABLES = ['questions']\n", encoding="utf-8")
    service = tmp_path / "src" / "service.py"
    service.write_text("print('runtime')\n", encoding="utf-8")

    files = iter_python_files([tmp_path / "src"])

    assert files == [service.resolve()]


def test_scan_legacy_usage_ignores_kg_learning_path_schema_name(tmp_path: Path):
    kg_schema = tmp_path / "src" / "kg" / "schemas.py"
    kg_schema.parent.mkdir(parents=True)
    kg_schema.write_text("class LearningPath(BaseModel):\n    pass\n", encoding="utf-8")

    report = scan_legacy_usage([tmp_path / "src"], excluded_parts=set())

    learning_path_surface = next(
        surface for surface in report["surfaces"] if surface["table"] == "learning_paths"
    )
    assert learning_path_surface["reference_count"] == 0


def test_scan_legacy_usage_ignores_docstrings(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text(
        '"""This docstring mentions MasteryScore and LearningPath."""\n'
        "def ok():\n"
        "    return True\n",
        encoding="utf-8",
    )

    report = scan_legacy_usage([tmp_path], excluded_parts=set())

    assert report["deprecated_reference_count"] == 0
