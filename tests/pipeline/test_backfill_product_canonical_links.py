from types import SimpleNamespace

from src.scripts.pipeline import backfill_product_canonical_links as script


def test_normalize_course_slug_to_canonical_id():
    assert script.canonical_course_id_from_slug("cs224n") == "CS224n"
    assert script.canonical_course_id_from_slug("cs231n") == "CS231n"
    assert script.canonical_course_id_from_slug("unknown") is None


def test_match_learning_unit_to_canonical_unit_by_course_and_lecture():
    product_unit = SimpleNamespace(slug="lecture-01-wordvecs", title="Word Vectors", sort_order=1)
    canonical_units = [
        SimpleNamespace(unit_id="local::lecture01-wordvecs::seg2", course_id="CS224n", lecture_id="lecture-01"),
    ]

    match = script.match_canonical_unit(product_unit, "CS224n", canonical_units)

    assert match == "local::lecture01-wordvecs::seg2"


def test_match_learning_unit_returns_none_when_no_safe_match():
    product_unit = SimpleNamespace(slug="unrelated", title="Unrelated", sort_order=99)
    canonical_units = [
        SimpleNamespace(unit_id="local::lecture01-wordvecs::seg2", course_id="CS224n", lecture_id="lecture-01"),
    ]

    assert script.match_canonical_unit(product_unit, "CS224n", canonical_units) is None


def test_match_learning_unit_returns_none_when_multiple_matches():
    product_unit = SimpleNamespace(slug="lecture-01-wordvecs", title="Word Vectors", sort_order=1)
    canonical_units = [
        SimpleNamespace(unit_id="local::lecture01-wordvecs::seg2", course_id="CS224n", lecture_id="lecture-01"),
        SimpleNamespace(unit_id="local::lecture01-wordvecs::seg3", course_id="CS224n", lecture_id="lecture-01"),
    ]

    assert script.match_canonical_unit(product_unit, "CS224n", canonical_units) is None
