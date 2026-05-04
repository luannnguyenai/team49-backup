from src.core.observability import (
    TUTOR_STREAM_FIRST_ANSWER_SECONDS,
    TUTOR_STREAM_FIRST_STATUS_SECONDS,
    TUTOR_STREAM_TOTAL_SECONDS,
    observe_tutor_stream_first_answer,
    observe_tutor_stream_first_status,
    observe_tutor_stream_total,
)


def _sample_value(metric, sample_name: str, labels: dict[str, str]) -> float:
    for collected_metric in metric.collect():
        for sample in collected_metric.samples:
            if sample.name == sample_name and sample.labels == labels:
                return float(sample.value)
    return 0.0


def test_tutor_stream_metrics_record_expected_labels():
    labels = {"route_type": "complex", "has_image": "true"}
    before_status_count = _sample_value(
        TUTOR_STREAM_FIRST_STATUS_SECONDS,
        "tutor_stream_first_status_seconds_count",
        labels,
    )
    before_answer_count = _sample_value(
        TUTOR_STREAM_FIRST_ANSWER_SECONDS,
        "tutor_stream_first_answer_seconds_count",
        labels,
    )
    before_total_count = _sample_value(
        TUTOR_STREAM_TOTAL_SECONDS,
        "tutor_stream_total_seconds_count",
        labels,
    )

    observe_tutor_stream_first_status(0.12, route_type="COMPLEX", has_image=True)
    observe_tutor_stream_first_answer(0.48, route_type="COMPLEX", has_image=True)
    observe_tutor_stream_total(1.25, route_type="COMPLEX", has_image=True)

    assert (
        _sample_value(
            TUTOR_STREAM_FIRST_STATUS_SECONDS,
            "tutor_stream_first_status_seconds_count",
            labels,
        )
        == before_status_count + 1
    )
    assert (
        _sample_value(
            TUTOR_STREAM_FIRST_ANSWER_SECONDS,
            "tutor_stream_first_answer_seconds_count",
            labels,
        )
        == before_answer_count + 1
    )
    assert (
        _sample_value(
            TUTOR_STREAM_TOTAL_SECONDS,
            "tutor_stream_total_seconds_count",
            labels,
        )
        == before_total_count + 1
    )


def test_tutor_stream_metrics_fallback_to_unknown_route_label():
    labels = {"route_type": "unknown", "has_image": "false"}
    before_total_count = _sample_value(
        TUTOR_STREAM_TOTAL_SECONDS,
        "tutor_stream_total_seconds_count",
        labels,
    )

    observe_tutor_stream_total(0.35, route_type="unexpected-route", has_image=False)

    assert (
        _sample_value(
            TUTOR_STREAM_TOTAL_SECONDS,
            "tutor_stream_total_seconds_count",
            labels,
        )
        == before_total_count + 1
    )
