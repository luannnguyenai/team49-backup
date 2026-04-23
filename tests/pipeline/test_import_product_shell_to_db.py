import json
from pathlib import Path

from src.scripts.pipeline import import_product_shell_to_db as importer


def test_build_product_shell_bundle_groups_sections_and_links_units(tmp_path: Path):
    canonical_dir = tmp_path / "canonical"
    canonical_dir.mkdir()
    units_path = canonical_dir / "units.jsonl"
    rows = [
        {
            "unit_id": "local::lecture01-wordvecs::seg1",
            "course_id": "CS224n",
            "lecture_id": "lecture-01",
            "lecture_order": 1,
            "lecture_title": "Lecture 1 - Intro and Word Vectors",
            "unit_name": "Why embeddings matter",
            "summary": "Segment one",
            "duration_min": 8,
            "content_ref": {"video_url": "https://example.com/v1"},
        },
        {
            "unit_id": "local::lecture01-wordvecs::seg2",
            "course_id": "CS224n",
            "lecture_id": "lecture-01",
            "lecture_order": 1,
            "lecture_title": "Lecture 1 - Intro and Word Vectors",
            "unit_name": "Distributional intuition",
            "summary": "Segment two",
            "duration_min": 7,
            "content_ref": {"video_url": "https://example.com/v1"},
        },
        {
            "unit_id": "local::lecture02-python::seg1",
            "course_id": "CS224n",
            "lecture_id": "lecture-02",
            "lecture_order": 2,
            "lecture_title": "Lecture 2 - Python Review",
            "unit_name": "Python recap",
            "summary": "Segment three",
            "duration_min": 6,
            "content_ref": {"video_url": None},
        },
    ]
    units_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    courses_path = tmp_path / "courses.json"
    courses_path.write_text(
        json.dumps(
            [
                {
                    "slug": "cs224n",
                    "title": "CS224n",
                    "short_description": "NLP",
                    "status": "ready",
                    "visibility": "public",
                    "cover_image_url": None,
                    "hero_badge": "Ready",
                    "primary_subject": "nlp",
                    "sort_order": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    overviews_path = tmp_path / "overviews.json"
    overviews_path.write_text(
        json.dumps(
            [
                {
                    "course_slug": "cs224n",
                    "headline": "Learn NLP",
                    "subheadline": None,
                    "summary_markdown": "Overview",
                    "learning_outcomes": ["A"],
                    "target_audience": None,
                    "prerequisites_summary": None,
                    "estimated_duration_text": "2 lectures",
                    "structure_snapshot": "Lecture-first",
                    "cta_label": "Start",
                }
            ]
        ),
        encoding="utf-8",
    )

    bundle = importer.build_product_shell_bundle(
        canonical_units_path=units_path,
        courses_path=courses_path,
        overviews_path=overviews_path,
    )

    assert len(bundle["courses"]) == 1
    assert len(bundle["course_overviews"]) == 1
    assert len(bundle["course_sections"]) == 2
    assert len(bundle["learning_units"]) == 3
    assert bundle["courses"][0]["canonical_course_id"] == "CS224n"
    assert bundle["course_sections"][0]["title"] == "Lecture 1 - Intro and Word Vectors"
    assert bundle["course_sections"][0]["is_entry_section"] is True
    assert bundle["learning_units"][0]["canonical_unit_id"] == "local::lecture01-wordvecs::seg1"
    assert bundle["learning_units"][0]["section_id"] == bundle["course_sections"][0]["id"]


def test_canonical_unit_slug_is_stable_and_path_safe():
    assert (
        importer.canonical_unit_slug("local::lecture01-wordvecs::seg1")
        == "lecture01-wordvecs-seg1"
    )


def test_product_shell_import_uses_natural_conflict_keys():
    assert importer.conflict_columns_for_table("courses") == ("slug",)
    assert importer.conflict_columns_for_table("course_overviews") == ("course_id",)
    assert importer.conflict_columns_for_table("course_sections") == ("id",)
    assert importer.conflict_columns_for_table("learning_units") == ("course_id", "slug")
