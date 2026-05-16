import json
from types import SimpleNamespace
from uuid import uuid4

from src.services.agent_user_learning_context_service import AgentUserLearningContextService


def _row(title: str, status: str | None = None):
    unit = SimpleNamespace(
        id=uuid4(),
        title=title,
        slug=title.lower().replace(" ", "-"),
        canonical_unit_id=f"canonical::{title}",
        estimated_minutes=10,
    )
    course = SimpleNamespace(canonical_course_id="CS230", slug="cs230")
    section = SimpleNamespace(title="Lecture 2")
    progress = SimpleNamespace(status=status) if status else None
    return unit, course, section, progress


def test_path_position_payload_exposes_next_units_without_message_heuristics():
    first = _row("Segment 1", status="completed")
    current = _row("Segment 2", status="in_progress")
    skipped_next = _row("Segment 3", status="skipped")
    next_unfinished = _row("Segment 4")

    payload = AgentUserLearningContextService._path_position_payload(
        [first, current, skipped_next, next_unfinished],
        current,
    )

    assert payload["current_index"] == 2
    assert payload["total_units"] == 4
    assert payload["previous_unit"]["unit_title"] == "Segment 1"
    assert payload["current_unit"]["unit_title"] == "Segment 2"
    assert payload["next_unit"]["unit_title"] == "Segment 3"
    assert payload["next_unfinished_unit"]["unit_title"] == "Segment 4"


def test_duration_hms_formats_video_positions_for_user_facing_answers():
    assert AgentUserLearningContextService._duration_hms(1247) == "00:20:47"
    assert AgentUserLearningContextService._duration_hms(3671.8) == "01:01:11"
    assert AgentUserLearningContextService._duration_hms(None) is None


def test_available_fields_does_not_advertise_raw_seconds_to_responder():
    available = AgentUserLearningContextService.available_fields()

    current_state_fields = available["current_learning_state"]
    recent_progress_fields = available["recent_progress"]
    assert "video_progress_s" not in current_state_fields
    assert "last_position_seconds" not in recent_progress_fields
    assert "video_progress_hms" in current_state_fields
    assert "last_position_hms" in recent_progress_fields


def _quiz_row(
    *,
    is_correct: bool,
    kp_id: str,
    kp_name: str,
    unit_id: str,
    unit_title: str,
    course_id: str = "CS230",
):
    interaction = SimpleNamespace(is_correct=is_correct)
    session = SimpleNamespace(session_type="quiz")
    item = SimpleNamespace(
        course_id=course_id,
        unit_id=unit_id,
        primary_kp_id=kp_id,
        question="SHOULD_NOT_LEAK",
        answer_index=2,
    )
    concept = SimpleNamespace(kp_id=kp_id, name=kp_name)
    canonical_unit = SimpleNamespace(unit_id=unit_id, unit_name=unit_title)
    return interaction, session, item, concept, canonical_unit


def _quiz_session(score_percent: float | None, started_at: str, unit_title: str):
    session = SimpleNamespace(
        session_type="quiz",
        canonical_phase="practice",
        total_questions=5,
        correct_count=None if score_percent is None else round(score_percent / 20),
        score_percent=score_percent,
        started_at=started_at,
        completed_at=started_at,
    )
    unit = SimpleNamespace(title=unit_title)
    course = SimpleNamespace(canonical_course_id="CS230", slug="cs230")
    return session, unit, course


def test_quiz_history_payload_summarizes_errors_without_leaking_questions():
    rows = [
        _quiz_row(
            is_correct=False,
            kp_id="kp_supervised",
            kp_name="Supervised learning",
            unit_id="u1",
            unit_title="Supervised recap",
        ),
        _quiz_row(
            is_correct=False,
            kp_id="kp_supervised",
            kp_name="Supervised learning",
            unit_id="u1",
            unit_title="Supervised recap",
        ),
        _quiz_row(
            is_correct=True,
            kp_id="kp_supervised",
            kp_name="Supervised learning",
            unit_id="u1",
            unit_title="Supervised recap",
        ),
        _quiz_row(
            is_correct=False,
            kp_id="kp_embeddings",
            kp_name="Embeddings",
            unit_id="u2",
            unit_title="Word vectors",
        ),
    ]
    session_rows = [
        _quiz_session(80.0, "2026-05-14T10:00:00", "Supervised recap"),
        _quiz_session(60.0, "2026-05-13T10:00:00", "Word vectors"),
        _quiz_session(40.0, "2026-05-12T10:00:00", "Word vectors"),
    ]

    payload = AgentUserLearningContextService._quiz_history_analysis_payload(
        rows,
        session_rows,
    )

    assert payload["total_answered"] == 4
    assert payload["correct_count"] == 1
    assert payload["accuracy_percent"] == 25.0
    assert payload["weakest_quiz_kps"][0]["kp_id"] == "kp_supervised"
    assert payload["weakest_quiz_kps"][0]["incorrect_count"] == 2
    assert payload["weakest_quiz_units"][0]["unit_title"] == "Supervised recap"
    assert payload["trend"]["direction"] == "improving"
    serialized = json.dumps(payload)
    assert "SHOULD_NOT_LEAK" not in serialized
    assert "answer_index" not in serialized
