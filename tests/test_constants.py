"""
tests/test_constants.py
-----------------------
RED phase: Verify src/constants.py tồn tại và có đúng các giá trị.
"""
import pytest


def test_constants_module_exists():
    """src/constants.py phải tồn tại và importable."""
    import src.constants  # noqa: F401


def test_quiz_difficulty_slots():
    from src.constants import QUIZ_DIFFICULTY_SLOTS
    from src.models.content import DifficultyBucket

    total_questions = sum(count for _, count in QUIZ_DIFFICULTY_SLOTS)
    assert total_questions == 10, f"Quiz phải có 10 câu hỏi, nhưng có {total_questions}"

    difficulties = [d for d, _ in QUIZ_DIFFICULTY_SLOTS]
    assert DifficultyBucket.easy in difficulties
    assert DifficultyBucket.medium in difficulties
    assert DifficultyBucket.hard in difficulties


def test_module_test_slots():
    from src.constants import MODULE_TEST_SLOTS

    total_questions = sum(count for _, count in MODULE_TEST_SLOTS)
    assert total_questions == 5, f"Module test phải có 5 câu/topic, nhưng có {total_questions}"


def test_assessment_bloom_slots():
    from src.constants import ASSESSMENT_BLOOM_SLOTS

    total_questions = sum(count for _, count in ASSESSMENT_BLOOM_SLOTS)
    assert total_questions == 5, f"Assessment phải có 5 câu/topic, nhưng có {total_questions}"


def test_irt_defaults():
    from src.constants import IRT_DEFAULT_DISCRIMINATION, IRT_BUCKET_DIFFICULTY, IRT_CANDIDATE_MULTIPLIER

    assert IRT_DEFAULT_DISCRIMINATION == 1.0
    assert IRT_BUCKET_DIFFICULTY["easy"] < 0
    assert IRT_BUCKET_DIFFICULTY["medium"] == 0.0
    assert IRT_BUCKET_DIFFICULTY["hard"] > 0
    assert IRT_CANDIDATE_MULTIPLIER >= 3


def test_mastery_constants():
    from src.constants import BLOOM_POINTS, QUIZ_EMA_ALPHA, MASTERY_THRESHOLDS
    from src.models.content import BloomLevel

    assert BloomLevel.remember in BLOOM_POINTS
    assert BloomLevel.analyze in BLOOM_POINTS
    assert BLOOM_POINTS[BloomLevel.analyze] > BLOOM_POINTS[BloomLevel.remember], \
        "Analyze phải có điểm cao hơn Remember"

    assert 0 < QUIZ_EMA_ALPHA < 1, "EMA alpha phải nằm trong (0, 1)"

    assert "novice" in MASTERY_THRESHOLDS
    assert "developing" in MASTERY_THRESHOLDS
    assert "proficient" in MASTERY_THRESHOLDS


def test_recent_assessment_lookback():
    from src.constants import RECENT_ASSESSMENT_LOOKBACK

    assert isinstance(RECENT_ASSESSMENT_LOOKBACK, int)
    assert RECENT_ASSESSMENT_LOOKBACK >= 1

# bot-test: iteration 1 at 2026-04-18T23:58:16.131688

# bot-test: iteration 1 at 2026-04-19T00:00:57.069807

# bot-test: iteration 1 at 2026-04-19T00:04:01.735603
