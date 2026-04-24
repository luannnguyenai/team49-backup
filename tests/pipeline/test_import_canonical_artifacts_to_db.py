import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from src.scripts.pipeline import import_canonical_artifacts_to_db as importer


def test_load_jsonl_reads_rows(tmp_path: Path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")

    assert importer.load_jsonl(path) == [{"id": 1}, {"id": 2}]


def test_load_jsonl_returns_empty_for_empty_file(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")

    assert importer.load_jsonl(path) == []


def test_validate_rows_rejects_unknown_columns():
    spec = importer.IMPORT_SPECS["concepts_kp"]

    with pytest.raises(ValueError, match="unknown columns"):
        importer.validate_rows("concepts_kp", [{"kp_id": "kp_a", "name": "A", "bad": 1}], spec)


def test_manifest_counts_match_canonical_bundle():
    manifest = importer.load_manifest(importer.DEFAULT_INPUT_DIR)

    assert manifest["counts"]["concepts_kp"] == 470
    assert manifest["counts"]["question_bank"] == 985
    assert importer.expected_count_keys() == [
        "concepts_kp",
        "units",
        "unit_kp_map",
        "question_bank",
        "item_calibration",
        "item_phase_map",
        "item_kp_map",
        "prerequisite_edges",
        "pruned_edges",
    ]


def test_validate_canonical_artifacts_checks_full_bundle_counts():
    report = importer.validate_canonical_artifacts(importer.DEFAULT_INPUT_DIR)

    assert report["counts"]["concepts_kp"] == 470
    assert report["counts"]["question_bank"] == 985
    assert report["counts"]["prerequisite_edges"] == 79
    assert "_loaded_rows" in report


def test_normalize_rows_maps_item_phase_suitability_labels_to_scores():
    rows = importer.normalize_rows(
        "item_phase_map",
        [
            {"item_id": "q1", "phase": "placement", "suitability_score": "high"},
            {"item_id": "q2", "phase": "review", "suitability_score": "medium"},
            {"item_id": "q3", "phase": "final_quiz", "suitability_score": "low"},
            {"item_id": "q4", "phase": "transfer", "suitability_score": 0.5},
        ],
    )

    assert [row["suitability_score"] for row in rows] == [1.0, 0.8, 0.6, 0.5]


@pytest.mark.asyncio
async def test_import_table_executes_postgres_upsert(monkeypatch):
    session = AsyncMock()
    spec = importer.IMPORT_SPECS["concepts_kp"]

    await importer.import_table(
        session=session,
        table_name="concepts_kp",
        rows=[
            {
                "kp_id": "kp_a",
                "name": "A",
                "description": "Desc",
            }
        ],
        spec=spec,
    )

    assert session.execute.await_count == 1
    assert session.flush.await_count == 1


@pytest.mark.asyncio
async def test_import_canonical_artifacts_checks_counts(tmp_path: Path, monkeypatch):
    manifest = {
        "counts": {
            key: 0 for key in importer.expected_count_keys()
        }
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for key in importer.expected_count_keys():
        (tmp_path / f"{key}.jsonl").write_text("", encoding="utf-8")

    session = AsyncMock()
    count_result = Mock()
    count_result.scalar_one.return_value = 0
    session.execute.return_value = count_result

    report = await importer.import_canonical_artifacts(session=session, input_dir=tmp_path)

    assert report["counts"] == manifest["counts"]
    assert report["imported"] == {key: 0 for key in importer.expected_count_keys()}
    assert report["db_counts"] == {key: 0 for key in importer.expected_count_keys()}


@pytest.mark.asyncio
async def test_import_canonical_artifacts_fails_on_count_mismatch(tmp_path: Path):
    manifest = {
        "counts": {
            key: 0 for key in importer.expected_count_keys()
        }
    }
    manifest["counts"]["concepts_kp"] = 1
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for key in importer.expected_count_keys():
        (tmp_path / f"{key}.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="count mismatch"):
        await importer.import_canonical_artifacts(session=Mock(), input_dir=tmp_path)


@pytest.mark.asyncio
async def test_verify_table_counts_fails_on_db_mismatch():
    session = AsyncMock()
    result = Mock()
    result.scalar_one.return_value = 999
    session.execute.return_value = result

    with pytest.raises(ValueError, match="DB count mismatch"):
        await importer.verify_table_counts(
            session=session,
            expected_counts={key: 0 for key in importer.expected_count_keys()},
        )
