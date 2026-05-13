from src.services.agent_context_service import canonicalize_agent_course_ids


def test_canonicalize_agent_course_ids_normalizes_legacy_lowercase_ids():
    assert canonicalize_agent_course_ids(["cs230", "cs231n", "CS224n"]) == [
        "CS230",
        "CS231n",
        "CS224n",
    ]


def test_canonicalize_agent_course_ids_deduplicates_case_variants():
    assert canonicalize_agent_course_ids(["cs231n", "CS231n", "custom"]) == [
        "CS231n",
        "custom",
    ]
