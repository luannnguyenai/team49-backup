"""Calibration boundary for future real/synthetic IRT fitting.

This module intentionally does not fit item parameters yet. It defines the
input contract and readiness checks so production code can distinguish real
calibration from bootstrap or synthetic-only experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CalibrationObservation:
    user_id: str
    session_id: str
    item_id: str
    kp_id: str
    is_correct: bool
    phase: str
    item_weight: float
    difficulty_prior: float | None = None
    discrimination_prior: float | None = None
    guessing_prior: float | None = None
    response_time_ms: int | None = None
    is_synthetic: bool = False


@dataclass(frozen=True)
class CalibrationReadinessPolicy:
    min_real_responses_per_item: int = 30
    min_distinct_users: int = 10


def summarize_calibration_readiness(
    observations: list[CalibrationObservation],
    *,
    policy: CalibrationReadinessPolicy = CalibrationReadinessPolicy(),
) -> dict[str, Any]:
    by_item: dict[str, list[CalibrationObservation]] = {}
    for observation in observations:
        by_item.setdefault(observation.item_id, []).append(observation)

    item_reports: dict[str, dict[str, Any]] = {}
    ready_count = 0
    for item_id, item_observations in sorted(by_item.items()):
        real_observations = [row for row in item_observations if not row.is_synthetic]
        synthetic_observations = [row for row in item_observations if row.is_synthetic]
        distinct_real_users = {row.user_id for row in real_observations}
        status = (
            "ready_for_real_calibration"
            if len(real_observations) >= policy.min_real_responses_per_item
            and len(distinct_real_users) >= policy.min_distinct_users
            else "insufficient_real_data"
        )
        if status == "ready_for_real_calibration":
            ready_count += 1

        item_reports[item_id] = {
            "status": status,
            "real_response_count": len(real_observations),
            "synthetic_response_count": len(synthetic_observations),
            "distinct_real_user_count": len(distinct_real_users),
            "correct_rate_real": _correct_rate(real_observations),
            "phases": sorted({row.phase for row in item_observations}),
            "kp_ids": sorted({row.kp_id for row in item_observations}),
        }

    return {
        "status": "ready" if ready_count else "insufficient_real_data",
        "policy": {
            "min_real_responses_per_item": policy.min_real_responses_per_item,
            "min_distinct_users": policy.min_distinct_users,
        },
        "ready_item_count": ready_count,
        "item_count": len(item_reports),
        "items": item_reports,
        "synthetic_policy": (
            "Synthetic observations may be used for demo stress tests or bootstrap experiments, "
            "but they do not satisfy real calibration readiness."
        ),
    }


def _correct_rate(observations: list[CalibrationObservation]) -> float | None:
    if not observations:
        return None
    return sum(1 for row in observations if row.is_correct) / len(observations)
