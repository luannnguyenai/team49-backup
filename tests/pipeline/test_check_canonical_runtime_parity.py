from src.scripts.pipeline.check_canonical_runtime_parity import classify_parity_status


def test_classify_parity_status_blocks_when_missing_links():
    assert classify_parity_status(unlinked_units=1, missing_question_phase_maps=0) == "blocked"


def test_classify_parity_status_blocks_when_missing_phase_maps():
    assert classify_parity_status(unlinked_units=0, missing_question_phase_maps=1) == "blocked"


def test_classify_parity_status_ready_when_clean():
    assert classify_parity_status(unlinked_units=0, missing_question_phase_maps=0) == "ready"
