from src.services.item_calibration_service import (
    CalibrationObservation,
    CalibrationReadinessPolicy,
    summarize_calibration_readiness,
)


def test_summarize_calibration_readiness_requires_real_response_volume():
    observations = [
        CalibrationObservation(
            user_id=f"user-{index}",
            session_id=f"session-{index}",
            item_id="item-attention-1",
            kp_id="kp_attention",
            is_correct=index % 2 == 0,
            phase="mini_quiz",
            item_weight=0.7,
            difficulty_prior=0.2,
            discrimination_prior=1.1,
            guessing_prior=0.25,
            is_synthetic=False,
        )
        for index in range(29)
    ]

    report = summarize_calibration_readiness(
        observations,
        policy=CalibrationReadinessPolicy(min_real_responses_per_item=30, min_distinct_users=10),
    )

    assert report["items"]["item-attention-1"]["status"] == "insufficient_real_data"
    assert report["items"]["item-attention-1"]["real_response_count"] == 29


def test_summarize_calibration_readiness_separates_synthetic_from_real_truth():
    observations = [
        CalibrationObservation(
            user_id=f"user-{index % 12}",
            session_id=f"session-{index}",
            item_id="item-attention-1",
            kp_id="kp_attention",
            is_correct=index % 2 == 0,
            phase="review",
            item_weight=0.7,
            difficulty_prior=0.2,
            discrimination_prior=1.1,
            guessing_prior=0.25,
            is_synthetic=False,
        )
        for index in range(30)
    ]
    observations.append(
        CalibrationObservation(
            user_id="synthetic-user-1",
            session_id="synthetic-session-1",
            item_id="item-attention-1",
            kp_id="kp_attention",
            is_correct=True,
            phase="review",
            item_weight=0.7,
            difficulty_prior=0.2,
            discrimination_prior=1.1,
            guessing_prior=0.25,
            is_synthetic=True,
        )
    )

    report = summarize_calibration_readiness(
        observations,
        policy=CalibrationReadinessPolicy(min_real_responses_per_item=30, min_distinct_users=10),
    )

    item_report = report["items"]["item-attention-1"]
    assert item_report["status"] == "ready_for_real_calibration"
    assert item_report["real_response_count"] == 30
    assert item_report["synthetic_response_count"] == 1
