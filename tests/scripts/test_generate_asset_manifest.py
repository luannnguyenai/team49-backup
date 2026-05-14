from pathlib import Path

from scripts.generate_asset_manifest import build_asset_manifest, materialize_asset_manifest


def test_build_asset_manifest_groups_assets_by_course_and_lecture(tmp_path: Path):
    cs230_videos = tmp_path / "courses" / "CS230" / "videos"
    cs230_transcripts = tmp_path / "courses" / "CS230" / "transcripts"
    cs224n_slides = tmp_path / "courses" / "CS224n" / "slides"

    cs230_videos.mkdir(parents=True)
    cs230_transcripts.mkdir(parents=True)
    cs224n_slides.mkdir(parents=True)

    (cs230_videos / "cs230-2025-lecture01-introduction-to-deep-learning.mp4").write_text(
        "", encoding="utf-8"
    )
    (cs230_videos / "cs230-2025-lecture02-supervised-learning.mp4").write_text(
        "", encoding="utf-8"
    )
    (cs230_transcripts / "cs230-2025-lecture01-introduction_transcript.txt").write_text(
        "", encoding="utf-8"
    )
    (cs224n_slides / "cs224n-2024-lecture03-pytorch.pdf").write_text("", encoding="utf-8")

    manifest = build_asset_manifest(tmp_path / "courses")

    assert manifest == {
        "videos": {
            "cs230": {
                "1": "cs230-2025-lecture01-introduction-to-deep-learning.mp4",
                "2": "cs230-2025-lecture02-supervised-learning.mp4",
            }
        },
        "slides": {
            "cs224n": {
                "3": "cs224n-2024-lecture03-pytorch.pdf",
            }
        },
        "transcripts": {
            "cs230": {
                "1": "cs230-2025-lecture01-introduction_transcript.txt",
            }
        },
    }


def test_build_asset_manifest_ignores_non_matching_files(tmp_path: Path):
    videos_dir = tmp_path / "courses" / "CS231n" / "videos"
    videos_dir.mkdir(parents=True)

    (videos_dir / "README.txt").write_text("ignore me", encoding="utf-8")
    (videos_dir / "lecture_notes.md").write_text("ignore me", encoding="utf-8")

    manifest = build_asset_manifest(tmp_path / "courses")

    assert manifest == {
        "videos": {},
        "slides": {},
        "transcripts": {},
    }


def test_materialize_asset_manifest_preserves_existing_file_when_source_missing(tmp_path: Path):
    output_path = tmp_path / "asset_manifest.json"
    output_path.write_text('{"videos":{"cs230":{"1":"tracked.mp4"}}}', encoding="utf-8")

    changed = materialize_asset_manifest(
        courses_dir=tmp_path / "missing-courses",
        output_path=output_path,
        preserve_existing=True,
    )

    assert changed is False
    assert output_path.read_text(encoding="utf-8") == '{"videos":{"cs230":{"1":"tracked.mp4"}}}'
