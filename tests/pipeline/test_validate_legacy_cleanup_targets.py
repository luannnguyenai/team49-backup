from src.scripts.pipeline.validate_legacy_cleanup_targets import validate_cleanup_targets


def test_validate_cleanup_targets_allows_only_legacy_candidates():
    report = validate_cleanup_targets(["questions", "mastery_scores", "learning_paths"])

    assert report["status"] == "ready"
    assert report["allowed_targets"] == ["learning_paths", "mastery_scores", "questions"]
    assert report["protected_hits"] == []
    assert report["unsupported_targets"] == []


def test_validate_cleanup_targets_blocks_canonical_content_tables():
    report = validate_cleanup_targets(["questions", "question_bank", "item_kp_map"])

    assert report["status"] == "blocked"
    assert report["protected_hits"] == ["item_kp_map", "question_bank"]


def test_validate_cleanup_targets_blocks_product_and_shared_runtime_tables():
    report = validate_cleanup_targets(["learning_units", "sessions", "interactions"])

    assert report["status"] == "blocked"
    assert report["protected_hits"] == ["interactions", "learning_units", "sessions"]


def test_validate_cleanup_targets_blocks_unknown_or_empty_targets():
    unknown_report = validate_cleanup_targets(["random_table"])
    empty_report = validate_cleanup_targets(["", " "])

    assert unknown_report["status"] == "blocked"
    assert unknown_report["unsupported_targets"] == ["random_table"]
    assert empty_report["status"] == "blocked"
