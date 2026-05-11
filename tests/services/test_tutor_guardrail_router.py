from src.services.guardrail_router import GuardrailDecision
from src.services.llm_service import build_tutor_guardrail_event


def test_tutor_guardrail_event_redirects_off_topic_in_english():
    decision = GuardrailDecision(
        safety_label="SAFE",
        topic_label="OFF_TOPIC",
        action="SOFT_REFUSE_REDIRECT",
        attack_type="none",
        selected_kp_ids=[],
    )

    event = build_tutor_guardrail_event(decision)

    assert event == {
        "blocked": True,
        "message": "That question is outside the current lesson scope. Please ask about the current lesson.",
        "guardrail": {
            "blocked": True,
            "action": "SOFT_REFUSE_REDIRECT",
            "safety_label": "SAFE",
            "topic_label": "OFF_TOPIC",
            "attack_type": "none",
            "selected_kp_ids": [],
        },
    }


def test_tutor_guardrail_event_allows_on_topic_questions():
    decision = GuardrailDecision(
        safety_label="SAFE",
        topic_label="ON_TOPIC",
        action="ALLOW_LESSON_ANSWER",
        attack_type="none",
        selected_kp_ids=["kp_error_analysis"],
    )

    assert build_tutor_guardrail_event(decision) is None
