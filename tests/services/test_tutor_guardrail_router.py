from src.services.guardrail_router import GuardrailDecision
from src.services.language_normalization import LanguageNormalizationResult
from src.services.llm_service import build_tutor_guardrail_event, normalize_tutor_question_for_model


class FakeTutorLanguageNormalizer:
    async def normalize(self, text):
        if text == "Explique les mécanismes d’attention.":
            return LanguageNormalizationResult(
                original_text=text,
                normalized_text="Explain attention mechanisms.",
                detected_language="other",
                target_language="en",
                translated=True,
            )
        return LanguageNormalizationResult(
            original_text=text,
            normalized_text=text,
            detected_language="vi" if "Giải thích" in text else "en",
            target_language="vi" if "Giải thích" in text else "en",
            translated=False,
        )


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


def test_tutor_question_normalization_keeps_english_and_vietnamese():
    normalizer = FakeTutorLanguageNormalizer()

    english = normalize_tutor_question_for_model("Explain attention.", normalizer=normalizer)
    vietnamese = normalize_tutor_question_for_model("Giải thích attention.", normalizer=normalizer)

    assert english.normalized_text == "Explain attention."
    assert english.target_language == "en"
    assert english.translated is False
    assert vietnamese.normalized_text == "Giải thích attention."
    assert vietnamese.target_language == "vi"
    assert vietnamese.translated is False


def test_tutor_question_normalization_translates_third_language_to_english():
    result = normalize_tutor_question_for_model(
        "Explique les mécanismes d’attention.",
        normalizer=FakeTutorLanguageNormalizer(),
    )

    assert result.normalized_text == "Explain attention mechanisms."
    assert result.detected_language == "other"
    assert result.target_language == "en"
    assert result.translated is True
