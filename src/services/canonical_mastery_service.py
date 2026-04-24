import math
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import ItemCalibration, ItemKPMap
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository


class MasteryReadModel(Protocol):
    theta_mu: float
    theta_sigma: float
    updated_at: datetime


@dataclass(frozen=True)
class ItemScoringParameters:
    difficulty: float = 0.0
    discrimination: float = 1.0
    guessing: float = 0.25
    method: str = "fallback_prior"


@dataclass(frozen=True)
class MasteryUpdateResult:
    theta_mu: float
    theta_sigma: float
    mastery_mean_cached: float
    predicted_probability: float
    residual: float
    method: str


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def estimate_mastery_mean(theta_mu: float, theta_sigma: float) -> float:
    adjusted = theta_mu / math.sqrt(1.0 + theta_sigma * theta_sigma)
    return _sigmoid(adjusted)


def estimate_mastery_lcb(
    theta_mu: float,
    theta_sigma: float,
    *,
    lambda_lcb: float = 1.0,
) -> float:
    """Conservative mastery estimate for planner gates and waive decisions."""
    adjusted = (theta_mu - lambda_lcb * theta_sigma) / math.sqrt(1.0 + theta_sigma * theta_sigma)
    return _sigmoid(adjusted)


def decay_mastery_for_read(
    *,
    theta_mu: float,
    theta_sigma: float,
    last_updated: datetime,
    now: datetime,
    sigma_forgetting_rate: float = 0.02,
    mu_decay_rate: float = 0.0,
) -> tuple[float, float]:
    """Apply non-destructive staleness adjustment for planner/assessor reads."""
    age_days = max(0.0, (now - last_updated).total_seconds() / 86_400)
    if age_days < 1:
        return theta_mu, theta_sigma
    sigma = math.sqrt(theta_sigma * theta_sigma + age_days * sigma_forgetting_rate)
    mu = theta_mu * math.exp(-age_days * mu_decay_rate)
    return mu, sigma


def estimate_mastery_mean_on_read(
    mastery: MasteryReadModel,
    *,
    now: datetime,
) -> float:
    theta_mu, theta_sigma = decay_mastery_for_read(
        theta_mu=mastery.theta_mu,
        theta_sigma=mastery.theta_sigma,
        last_updated=mastery.updated_at,
        now=now,
    )
    return estimate_mastery_mean(theta_mu, theta_sigma)


def estimate_mastery_lcb_on_read(
    mastery: MasteryReadModel,
    *,
    now: datetime,
    lambda_lcb: float = 1.0,
) -> float:
    theta_mu, theta_sigma = decay_mastery_for_read(
        theta_mu=mastery.theta_mu,
        theta_sigma=mastery.theta_sigma,
        last_updated=mastery.updated_at,
        now=now,
    )
    return estimate_mastery_lcb(theta_mu, theta_sigma, lambda_lcb=lambda_lcb)


def next_theta_mu(current_theta: float, is_correct: bool, item_weight: float) -> float:
    """Legacy compatibility helper for older tests/plans; runtime uses calculate_mastery_update."""
    delta = 0.25 * max(0.0, min(item_weight, 1.0))
    value = current_theta + delta if is_correct else current_theta - delta
    return max(-3.0, min(3.0, value))


def item_parameters_from_calibration(calibration: ItemCalibration | None) -> ItemScoringParameters:
    if calibration is None:
        return ItemScoringParameters()

    use_calibrated = bool(getattr(calibration, "is_calibrated", False))
    difficulty = (
        calibration.difficulty_b
        if use_calibrated and calibration.difficulty_b is not None
        else calibration.difficulty_prior
    )
    discrimination = (
        calibration.discrimination_a
        if use_calibrated and calibration.discrimination_a is not None
        else calibration.discrimination_prior
    )
    guessing = (
        calibration.guessing_c
        if use_calibrated and calibration.guessing_c is not None
        else calibration.guessing_prior
    )

    method = "irt_calibrated" if use_calibrated else "2pl_lite_prior"
    return ItemScoringParameters(
        difficulty=float(difficulty if difficulty is not None else 0.0),
        discrimination=_clamp(float(discrimination if discrimination is not None else 1.0), 0.25, 3.0),
        guessing=_clamp(float(guessing if guessing is not None else 0.25), 0.0, 0.35),
        method=method,
    )


def calculate_mastery_update(
    *,
    theta_mu: float,
    theta_sigma: float,
    is_correct: bool,
    item_weight: float,
    item_parameters: ItemScoringParameters | None = None,
) -> MasteryUpdateResult:
    """Phase-1 KP mastery update using 2PL-lite priors, not fitted production IRT."""
    params = item_parameters or ItemScoringParameters()
    weight = _clamp(item_weight, 0.0, 1.0)
    predicted = params.guessing + (1.0 - params.guessing) * _sigmoid(
        params.discrimination * (theta_mu - params.difficulty)
    )
    observed = 1.0 if is_correct else 0.0
    residual = observed - predicted

    delta = _clamp(0.5 * weight * params.discrimination * residual, -0.45, 0.45)
    next_mu = _clamp(theta_mu + delta, -3.0, 3.0)

    information = weight * params.discrimination * abs(residual)
    shrink_factor = 1.0 - min(0.18, 0.04 + 0.08 * information)
    next_sigma = max(0.25, theta_sigma * shrink_factor)

    return MasteryUpdateResult(
        theta_mu=next_mu,
        theta_sigma=next_sigma,
        mastery_mean_cached=estimate_mastery_mean(next_mu, next_sigma),
        predicted_probability=predicted,
        residual=residual,
        method=params.method,
    )


async def update_kp_mastery_from_item(
    db: AsyncSession,
    *,
    user_id: UUID,
    canonical_item_id: str,
    is_correct: bool,
) -> list[str]:
    result = await db.execute(select(ItemKPMap).where(ItemKPMap.item_id == canonical_item_id))
    mappings = result.scalars().all()
    calibration_result = await db.execute(
        select(ItemCalibration).where(ItemCalibration.item_id == canonical_item_id)
    )
    item_parameters = item_parameters_from_calibration(calibration_result.scalar_one_or_none())
    repo = LearnerMasteryKPRepository(db)
    updated: list[str] = []

    for mapping in mappings:
        existing = await repo.get_by_user_kp(user_id, mapping.kp_id)
        current_theta = existing.theta_mu if existing else 0.0
        current_sigma = existing.theta_sigma if existing else 1.0
        weight = mapping.weight if mapping.weight is not None else 0.7
        update = calculate_mastery_update(
            theta_mu=current_theta,
            theta_sigma=current_sigma,
            is_correct=is_correct,
            item_weight=weight,
            item_parameters=item_parameters,
        )
        await repo.upsert(
            user_id=user_id,
            kp_id=mapping.kp_id,
            theta_mu=update.theta_mu,
            theta_sigma=update.theta_sigma,
            mastery_mean_cached=update.mastery_mean_cached,
            n_items_observed=(existing.n_items_observed if existing else 0) + 1,
            updated_by=f"canonical_assessor_{update.method}",
        )
        updated.append(mapping.kp_id)

    return updated
