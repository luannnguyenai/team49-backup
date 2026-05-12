from src.services.guardrail_router import GuardrailDecision
from src.services.language_normalization import LanguageNormalizationResult
from src.api.app import AskRequest
from src.services.llm_service import (
    build_tutor_guardrail_event,
    build_tutor_guardrail_scope,
    enforce_tutor_response_language,
    normalize_tutor_question_for_model,
)


class FakeTranslator:
    async def translate_to_english(self, text):
        return "Attention lets the model focus on relevant tokens."


class FakeTutorLanguageNormalizer:
    translator = FakeTranslator()

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

    def detect(self, text):
        return "vi" if "trọng số" in text else "en"


def test_tutor_ask_request_limits_question_to_1500_chars():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AskRequest(lecture_id="lecture-1", current_timestamp=0, question="x" * 1501)


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


def test_tutor_response_language_enforces_english_target_for_direct_answers():
    result = enforce_tutor_response_language(
        "Attention là cơ chế tính trọng số cho token liên quan.",
        LanguageNormalizationResult(
            original_text="Explain attention.",
            normalized_text="Explain attention.",
            detected_language="en",
            target_language="en",
            translated=False,
        ),
        normalizer=FakeTutorLanguageNormalizer(),
    )

    assert result == "Attention lets the model focus on relevant tokens."


def test_tutor_guardrail_scope_uses_unit_summary_without_history():
    scope = build_tutor_guardrail_scope(
        lecture_id="lecture-1",
        lecture_title="Lecture 1: Introduction",
        context_summary="- Overview: intro summary\n- Old unrelated history should not appear",
        current_chapter="Overview",
        lecture_scope={"core_topics": ["CNN"], "scope_keywords": ["vision"]},
        context_binding_id="ctx_unit_1",
    )

    assert scope.allowed_scope_summary == (
        "Unit summary: - Overview: intro summary\n"
        "- Old unrelated history should not appear\n"
        "Current chapter: Overview"
    )
    assert scope.recent_context == []
    assert scope.candidate_kps == []
    assert scope.selected_text == ""
