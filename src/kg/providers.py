"""Mastery providers for KG services."""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Protocol

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import settings


class MasteryProvider(Protocol):
    """Read mastery signals for KG planning and recommendations."""

    async def get_topic_mastery(self, user_id: uuid.UUID) -> dict[str, float]:
        """Return topic_slug -> mastery in [0, 1]."""
        ...

    async def get_kc_mastery(self, user_id: uuid.UUID) -> dict[str, float]:
        """Return kc_slug -> mastery in [0, 1]."""
        ...


class DBMasteryProvider:
    """SQL-backed mastery provider for Phase 0/1 KG services."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        bucket_weights: dict[str, float] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.bucket_weights = bucket_weights or settings.kg_bucket_weights

    async def get_topic_mastery(self, user_id: uuid.UUID) -> dict[str, float]:
        """Read user_mastery, preferring theta when available."""
        async with self.session_factory() as session:
            result = await session.execute(
                sa.text(
                    "SELECT t.slug AS topic_slug, um.mastery_score, um.theta, um.theta_se "
                    "FROM topics t "
                    "LEFT JOIN user_mastery um "
                    "  ON um.topic_slug = t.slug AND um.user_id = :user_id "
                    "WHERE t.status = 'published' "
                    "  AND t.slug IS NOT NULL"
                ),
                {"user_id": user_id},
            )
            rows = result.mappings().all()

        mastery: dict[str, float] = {}
        for row in rows:
            if row["theta"] is not None and row["theta_se"] not in (None, 0):
                value = _sigmoid(float(row["theta"]) / float(row["theta_se"]))
            else:
                value = float(row["mastery_score"] or 0.0)
            mastery[str(row["topic_slug"])] = _clamp01(value)
        return mastery

    async def get_kc_mastery(self, user_id: uuid.UUID) -> dict[str, float]:
        """Aggregate recent correctness over KCs using question difficulty weights."""
        since = datetime.now(UTC) - timedelta(days=30)
        async with self.session_factory() as session:
            kc_rows = (
                await session.execute(
                    sa.text(
                        "SELECT id, slug "
                        "FROM knowledge_components "
                        "WHERE slug IS NOT NULL"
                    )
                )
            ).mappings().all()
            kc_id_to_slug = {str(row["id"]): str(row["slug"]) for row in kc_rows}

            response_rows = (
                await session.execute(
                    sa.text(
                        "SELECT q.kc_ids, q.difficulty_bucket, ur.is_correct "
                        "FROM user_responses ur "
                        "JOIN questions q ON q.id = ur.question_id "
                        "WHERE ur.user_id = :user_id "
                        "  AND ur.created_at >= :since"
                    ),
                    {"user_id": user_id, "since": since},
                )
            ).mappings().all()

        correct_weight = defaultdict(float)
        total_weight = defaultdict(float)
        for row in response_rows:
            weight = self._bucket_weight(row["difficulty_bucket"])
            is_correct = bool(row["is_correct"])
            for kc_id in row["kc_ids"] or []:
                slug = kc_id_to_slug.get(str(kc_id))
                if slug is None:
                    continue
                total_weight[slug] += weight
                if is_correct:
                    correct_weight[slug] += weight

        mastery = {slug: 0.0 for slug in kc_id_to_slug.values()}
        mastery.update(
            {
                slug: _clamp01(correct_weight[slug] / total)
                for slug, total in total_weight.items()
                if total > 0
            }
        )
        return mastery

    def _bucket_weight(self, bucket: object) -> float:
        key = getattr(bucket, "value", bucket)
        return float(self.bucket_weights.get(str(key).lower(), 1.0))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
