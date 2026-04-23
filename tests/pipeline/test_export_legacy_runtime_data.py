from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from src.scripts.pipeline.export_legacy_runtime_data import (
    build_manifest,
    encode_json_line,
    timestamped_output_dir,
    write_jsonl,
)


def test_timestamped_output_dir_uses_utc_format():
    output_dir = timestamped_output_dir(
        Path("data/legacy_archive"),
        datetime(2026, 4, 23, 1, 2, 3, tzinfo=UTC),
    )

    assert output_dir == Path("data/legacy_archive/20260423T010203Z")


def test_encode_json_line_serializes_uuid_and_datetime():
    line = encode_json_line(
        {
            "id": UUID("00000000-0000-0000-0000-000000000001"),
            "created_at": datetime(2026, 4, 23, 1, 2, 3, tzinfo=UTC),
        }
    )

    assert '"id": "00000000-0000-0000-0000-000000000001"' in line
    assert '"created_at": "2026-04-23 01:02:03+00:00"' in line


def test_write_jsonl_returns_count_and_sha(tmp_path: Path):
    output = tmp_path / "questions.jsonl"

    result = write_jsonl(output, [{"item_id": "q1"}, {"item_id": "q2"}])

    assert result["rows"] == 2
    assert len(result["sha256"]) == 64
    assert output.read_text(encoding="utf-8").splitlines() == [
        '{"item_id": "q1"}',
        '{"item_id": "q2"}',
    ]


def test_build_manifest_records_table_exports(tmp_path: Path):
    manifest = build_manifest(
        output_dir=tmp_path,
        table_exports={
            "questions": {
                "rows": 2,
                "sha256": "a" * 64,
                "path": str(tmp_path / "questions.jsonl"),
            }
        },
    )

    assert manifest["output_dir"] == str(tmp_path)
    assert manifest["tables"]["questions"]["rows"] == 2
