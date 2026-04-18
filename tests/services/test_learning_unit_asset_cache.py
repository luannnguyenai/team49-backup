from pathlib import Path

from src.services.learning_unit_service import _available_lecture_numbers


def test_asset_availability_cache_refreshes_when_directory_changes(tmp_path: Path) -> None:
    first_file = tmp_path / "Lecture_17_transcript.txt"
    first_file.write_text("lecture 17", encoding="utf-8")

    first_numbers = _available_lecture_numbers(tmp_path)
    assert first_numbers == {17}

    second_file = tmp_path / "Lecture_18_transcript.txt"
    second_file.write_text("lecture 18", encoding="utf-8")
    tmp_path.touch()

    refreshed_numbers = _available_lecture_numbers(tmp_path)
    assert refreshed_numbers == {17, 18}
