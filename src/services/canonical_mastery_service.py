import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import ItemKPMap
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository


def estimate_mastery_mean(theta_mu: float, theta_sigma: float) -> float:
    adjusted = theta_mu / math.sqrt(1.0 + theta_sigma * theta_sigma)
    return 1.0 / (1.0 + math.exp(-adjusted))


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
