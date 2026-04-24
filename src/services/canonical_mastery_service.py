import math
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import ItemKPMap
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository


class MasteryReadModel(Protocol):
    theta_mu: float
    theta_sigma: float
    updated_at: datetime


def estimate_mastery_mean(theta_mu: float, theta_sigma: float) -> float:
    adjusted = theta_mu / math.sqrt(1.0 + theta_sigma * theta_sigma)
    return 1.0 / (1.0 + math.exp(-adjusted))


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


def next_theta_mu(current_theta: float, is_correct: bool, item_weight: float) -> float:
    delta = 0.25 * max(0.0, min(item_weight, 1.0))
    value = current_theta + delta if is_correct else current_theta - delta
    return max(-3.0, min(3.0, value))


async def update_kp_mastery_from_item(
    db: AsyncSession,
    *,
    user_id: UUID,
    canonical_item_id: str,
    is_correct: bool,
) -> list[str]:
    result = await db.execute(select(ItemKPMap).where(ItemKPMap.item_id == canonical_item_id))
    mappings = result.scalars().all()
    repo = LearnerMasteryKPRepository(db)
    updated: list[str] = []

    for mapping in mappings:
        existing = await repo.get_by_user_kp(user_id, mapping.kp_id)
        current_theta = existing.theta_mu if existing else 0.0
        current_sigma = existing.theta_sigma if existing else 1.0
        weight = mapping.weight if mapping.weight is not None else 0.7
        theta_mu = next_theta_mu(current_theta, is_correct, weight)
        theta_sigma = max(0.25, current_sigma * 0.95)
        await repo.upsert(
            user_id=user_id,
            kp_id=mapping.kp_id,
            theta_mu=theta_mu,
            theta_sigma=theta_sigma,
            mastery_mean_cached=estimate_mastery_mean(theta_mu, theta_sigma),
            n_items_observed=(existing.n_items_observed if existing else 0) + 1,
            updated_by="canonical_assessor_bootstrap",
        )
        updated.append(mapping.kp_id)

    return updated
