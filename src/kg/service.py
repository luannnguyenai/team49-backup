"""Read and recommendation services for the Knowledge Graph."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import settings
from src.kg.providers import MasteryProvider
from src.kg.repository import KGRepository
from src.kg.schemas import (
    KGEdge,
    KCNode,
    LearningPath,
    PathTopic,
    PathWeek,
    RankedCandidate,
    TopicContext,
    TopicNode,
)

_CONTEXT_CACHE_TTL_SECONDS = 600.0
_CONTEXT_CACHE: dict[tuple[int, str, int], tuple[float, TopicContext]] = {}


class KGService:
    """High-level KG read service for context, paths, and recommendations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None,
        mastery: MasteryProvider,
        repo: KGRepository | None,
    ) -> None:
        self.session_factory = session_factory
        self.mastery = mastery
        self.repo = repo

    async def get_topic_context(self, topic_slug: str, hops: int = 2) -> TopicContext:
        """Return topic context with cached 10-minute TTL."""
        cache_key = (id(self), topic_slug, max(0, hops))
        now = time.monotonic()
        cached = _CONTEXT_CACHE.get(cache_key)
        if cached is not None and cached[0] > now:
            return cached[1]

        context = await self._build_topic_context(topic_slug, max(0, hops))
        _CONTEXT_CACHE[cache_key] = (now + _CONTEXT_CACHE_TTL_SECONDS, context)
        return context

    async def build_path(
        self,
        user_id: uuid.UUID,
        target_topics: list[str],
        hours_per_week: float,
    ) -> LearningPath:
        """Build a prerequisite-aware learning path with transfer shortcuts."""
        topics = await self._load_topics_map()
        kcs = await self._load_kcs()
        edges = await self._load_edges()
        topic_mastery = await self.mastery.get_topic_mastery(user_id)
        kc_mastery = await self.mastery.get_kc_mastery(user_id)

        ordered_slugs = self._expand_and_sort_topics(target_topics, topics)
        topic_kcs = _group_kcs_by_topic(kcs)
        kc_by_slug = {kc.slug: kc for kc in kcs}
        align_edges = [edge for edge in edges if edge.type == "ALIGNS_WITH"]
        scheduled: list[PathTopic] = []

        for slug in ordered_slugs:
            topic = topics[slug]
            mastery_value = _clamp01(topic_mastery.get(slug, 0.0))
            if mastery_value >= settings.kg_mastery_skip_threshold:
                continue

            if mastery_value >= settings.kg_mastery_review_threshold:
                mode = "review"
                hours = topic.estimated_hours_review
            else:
                mode = "learn"
                hours = topic.estimated_hours_beginner

            shortcut_labels = self._find_shortcuts_for_topic(
                topic,
                topic_kcs.get(slug, []),
                kc_by_slug,
                kc_mastery,
                align_edges,
            )
            if shortcut_labels:
                mode = "review"
                hours *= settings.kg_shortcut_hours_factor

            scheduled.append(
                PathTopic(
                    slug=slug,
                    mode=mode,
                    hours=round(float(hours), 4),
                    mastery=mastery_value,
                    shortcuts=tuple(shortcut_labels),
                )
            )

        return LearningPath(weeks=tuple(_pack_weeks(scheduled, hours_per_week)))

    async def rank_next(
        self,
        user_id: uuid.UUID,
        candidate_limit: int = 20,
    ) -> list[RankedCandidate]:
        """Rank next topics using deterministic Phase 0 features."""
        topics = await self._load_topics_map()
        kcs = await self._load_kcs()
        edges = await self._load_edges()
        recent_topics = await self._load_recent_topic_slugs(user_id)
        topic_mastery = await self.mastery.get_topic_mastery(user_id)
        kc_mastery = await self.mastery.get_kc_mastery(user_id)

        topic_kcs = _group_kcs_by_topic(kcs)
        mastered_topics = {
            slug
            for slug, score in topic_mastery.items()
            if score >= settings.kg_mastery_skip_threshold
        }
        mastered_kcs = {
            slug
            for slug, score in kc_mastery.items()
            if score >= settings.kg_shortcut_mastery_threshold
        }
        weights = settings.kg_recsys_weights
        distances = _distance_to_terminal_topics(topics)
        candidates: list[RankedCandidate] = []

        for slug, topic in topics.items():
            if topic_mastery.get(slug, 0.0) >= settings.kg_mastery_skip_threshold:
                continue
            mastery_gap = 1.0 - _clamp01(topic_mastery.get(slug, 0.0))
            prereq_ready = _prereq_ready(topic, topic_mastery)
            transfer_boost = _transfer_boost(
                topic,
                topic_kcs.get(slug, []),
                edges,
                mastered_topics,
                mastered_kcs,
            )
            goal_distance = float(distances.get(slug, 0))
            freshness_penalty = 1.0 if slug in recent_topics else 0.0
            score = (
                weights.get("mastery_gap", 0.0) * mastery_gap
                + weights.get("prereq_ready", 0.0) * prereq_ready
                + weights.get("transfer_boost", 0.0) * transfer_boost
                - weights.get("goal_distance", 0.0) * goal_distance
                - weights.get("freshness", 0.0) * freshness_penalty
            )
            candidates.append(
                RankedCandidate(
                    topic_slug=slug,
                    score=round(score, 6),
                    mastery_gap=round(mastery_gap, 6),
                    prereq_ready=round(prereq_ready, 6),
                    transfer_boost=round(transfer_boost, 6),
                    goal_distance=goal_distance,
                    freshness_penalty=freshness_penalty,
                )
            )

        return sorted(candidates, key=lambda item: (-item.score, item.topic_slug))[
            : max(0, candidate_limit)
        ]

    async def _build_topic_context(self, topic_slug: str, hops: int) -> TopicContext:
        if self.session_factory is not None:
            return await self._fetch_topic_context_cte(topic_slug, hops)
        return await self._build_topic_context_in_memory(topic_slug, hops)

    async def _build_topic_context_in_memory(self, topic_slug: str, hops: int) -> TopicContext:
        topics = await self._load_topics_map()
        if topic_slug not in topics:
            raise KeyError(topic_slug)

        kcs = await self._load_kcs()
        edges = await self._load_edges()
        prereq_slugs = _prereq_closure(topic_slug, topics, hops)
        topic_kcs = [kc for kc in kcs if kc.topic_slug == topic_slug]
        topic_kc_slugs = {kc.slug for kc in topic_kcs}
        sibling_slugs = _sibling_kc_slugs(topic_kc_slugs, edges)
        siblings = sorted(
            (
                kc
                for kc in kcs
                if kc.slug in sibling_slugs
                and kc.topic_slug != topic_slug
            ),
            key=lambda kc: (kc.module_slug, kc.topic_slug, kc.slug),
        )
        transfers = tuple(
            sorted(
                (
                    edge
                    for edge in edges
                    if edge.type == "TRANSFERS_TO"
                    and (
                        edge.src_ref == topic_slug
                        or edge.dst_ref == topic_slug
                    )
                ),
                key=lambda edge: (edge.src_kind, edge.src_ref, edge.dst_kind, edge.dst_ref),
            )
        )
        return TopicContext(
            topic=topics[topic_slug],
            prereqs=tuple(topics[slug] for slug in prereq_slugs),
            kcs=tuple(sorted(topic_kcs, key=lambda kc: kc.slug)),
            sibling_kcs=tuple(siblings),
            transfers=transfers,
        )

    async def _fetch_topic_context_cte(self, topic_slug: str, hops: int) -> TopicContext:
        if self.session_factory is None:
            raise RuntimeError("session_factory is required for DB-backed KGService")

        async with self.session_factory() as session:
            result = await session.execute(
                sa.text(
                    """
                    WITH RECURSIVE published_topics AS (
                        SELECT
                            t.id,
                            t.slug,
                            t.name,
                            m.slug AS module_slug,
                            COALESCE(t.estimated_hours_beginner, 1.0) AS estimated_hours_beginner,
                            COALESCE(t.estimated_hours_review, 0.5) AS estimated_hours_review,
                            COALESCE(
                                ARRAY(
                                    SELECT pt.slug
                                    FROM jsonb_array_elements_text(
                                        COALESCE(t.prerequisite_topic_ids::jsonb, '[]'::jsonb)
                                    ) AS prereq(topic_id)
                                    JOIN topics pt ON pt.id::text = prereq.topic_id
                                    WHERE pt.slug IS NOT NULL
                                    ORDER BY pt.slug
                                ),
                                ARRAY[]::text[]
                            ) AS prerequisite_topic_slugs
                        FROM topics t
                        JOIN modules m ON m.id = t.module_id
                        WHERE t.status = 'published'
                          AND t.slug IS NOT NULL
                          AND m.slug IS NOT NULL
                    ),
                    prereq_tree AS (
                        SELECT pt.*, 0 AS depth
                        FROM published_topics pt
                        WHERE pt.slug = :topic_slug

                        UNION ALL

                        SELECT prereq.*, tree.depth + 1 AS depth
                        FROM prereq_tree tree
                        JOIN LATERAL unnest(tree.prerequisite_topic_slugs) AS p(slug) ON true
                        JOIN published_topics prereq ON prereq.slug = p.slug
                        WHERE tree.depth < :hops
                    ),
                    target_kcs AS (
                        SELECT
                            kc.slug,
                            t.slug AS topic_slug,
                            m.slug AS module_slug,
                            kc.name,
                            kc.description
                        FROM knowledge_components kc
                        JOIN topics t ON t.id = kc.topic_id
                        JOIN modules m ON m.id = t.module_id
                        WHERE t.slug = :topic_slug
                          AND t.status = 'published'
                          AND kc.slug IS NOT NULL
                          AND m.slug IS NOT NULL
                    ),
                    target_concepts AS (
                        SELECT DISTINCT edge.src_ref AS concept_ref
                        FROM kg_edges edge
                        JOIN target_kcs kc ON kc.slug = edge.dst_ref
                        WHERE edge.type = 'INSTANCE_OF'
                          AND edge.src_kind = 'concept'
                          AND edge.dst_kind = 'kc'
                          AND edge.deleted_at IS NULL
                    ),
                    sibling_kcs AS (
                        SELECT DISTINCT
                            kc.slug,
                            t.slug AS topic_slug,
                            m.slug AS module_slug,
                            kc.name,
                            kc.description
                        FROM knowledge_components kc
                        JOIN topics t ON t.id = kc.topic_id
                        JOIN modules m ON m.id = t.module_id
                        JOIN kg_edges edge ON edge.dst_ref = kc.slug
                        JOIN target_concepts concept ON concept.concept_ref = edge.src_ref
                        WHERE edge.type = 'INSTANCE_OF'
                          AND edge.src_kind = 'concept'
                          AND edge.dst_kind = 'kc'
                          AND edge.deleted_at IS NULL
                          AND t.slug <> :topic_slug
                          AND t.status = 'published'
                          AND kc.slug IS NOT NULL
                          AND m.slug IS NOT NULL
                    ),
                    transfers AS (
                        SELECT src_kind, src_ref, dst_kind, dst_ref, type, weight, source, meta
                        FROM kg_edges
                        WHERE type = 'TRANSFERS_TO'
                          AND deleted_at IS NULL
                          AND (src_ref = :topic_slug OR dst_ref = :topic_slug)
                    )
                    SELECT
                        CASE WHEN depth = 0 THEN 'topic' ELSE 'prereq' END AS row_kind,
                        slug AS topic_slug,
                        module_slug,
                        name AS topic_name,
                        prerequisite_topic_slugs,
                        estimated_hours_beginner,
                        estimated_hours_review,
                        NULL::text AS kc_slug,
                        NULL::text AS kc_topic_slug,
                        NULL::text AS kc_module_slug,
                        NULL::text AS kc_name,
                        NULL::text AS kc_description,
                        NULL::text AS edge_src_kind,
                        NULL::text AS edge_src_ref,
                        NULL::text AS edge_dst_kind,
                        NULL::text AS edge_dst_ref,
                        NULL::text AS edge_type,
                        NULL::float AS edge_weight,
                        NULL::text AS edge_source,
                        NULL::jsonb AS edge_meta
                    FROM prereq_tree

                    UNION ALL

                    SELECT
                        'kc' AS row_kind,
                        NULL::text AS topic_slug,
                        NULL::text AS module_slug,
                        NULL::text AS topic_name,
                        NULL::text[] AS prerequisite_topic_slugs,
                        NULL::float AS estimated_hours_beginner,
                        NULL::float AS estimated_hours_review,
                        slug AS kc_slug,
                        topic_slug AS kc_topic_slug,
                        module_slug AS kc_module_slug,
                        name AS kc_name,
                        description AS kc_description,
                        NULL::text AS edge_src_kind,
                        NULL::text AS edge_src_ref,
                        NULL::text AS edge_dst_kind,
                        NULL::text AS edge_dst_ref,
                        NULL::text AS edge_type,
                        NULL::float AS edge_weight,
                        NULL::text AS edge_source,
                        NULL::jsonb AS edge_meta
                    FROM target_kcs

                    UNION ALL

                    SELECT
                        'sibling_kc' AS row_kind,
                        NULL::text AS topic_slug,
                        NULL::text AS module_slug,
                        NULL::text AS topic_name,
                        NULL::text[] AS prerequisite_topic_slugs,
                        NULL::float AS estimated_hours_beginner,
                        NULL::float AS estimated_hours_review,
                        slug AS kc_slug,
                        topic_slug AS kc_topic_slug,
                        module_slug AS kc_module_slug,
                        name AS kc_name,
                        description AS kc_description,
                        NULL::text AS edge_src_kind,
                        NULL::text AS edge_src_ref,
                        NULL::text AS edge_dst_kind,
                        NULL::text AS edge_dst_ref,
                        NULL::text AS edge_type,
                        NULL::float AS edge_weight,
                        NULL::text AS edge_source,
                        NULL::jsonb AS edge_meta
                    FROM sibling_kcs

                    UNION ALL

                    SELECT
                        'transfer' AS row_kind,
                        NULL::text AS topic_slug,
                        NULL::text AS module_slug,
                        NULL::text AS topic_name,
                        NULL::text[] AS prerequisite_topic_slugs,
                        NULL::float AS estimated_hours_beginner,
                        NULL::float AS estimated_hours_review,
                        NULL::text AS kc_slug,
                        NULL::text AS kc_topic_slug,
                        NULL::text AS kc_module_slug,
                        NULL::text AS kc_name,
                        NULL::text AS kc_description,
                        src_kind AS edge_src_kind,
                        src_ref AS edge_src_ref,
                        dst_kind AS edge_dst_kind,
                        dst_ref AS edge_dst_ref,
                        type AS edge_type,
                        weight AS edge_weight,
                        source AS edge_source,
                        meta AS edge_meta
                    FROM transfers
                    ORDER BY row_kind, topic_slug, kc_slug, edge_src_ref, edge_dst_ref
                    """
                ),
                {"topic_slug": topic_slug, "hops": hops},
            )
            rows = result.mappings().all()

        topic: TopicNode | None = None
        prereqs: list[TopicNode] = []
        kcs: list[KCNode] = []
        sibling_kcs: list[KCNode] = []
        transfers: list[KGEdge] = []

        for row in rows:
            row_kind = row["row_kind"]
            if row_kind in {"topic", "prereq"}:
                node = TopicNode(
                    slug=str(row["topic_slug"]),
                    module_slug=str(row["module_slug"]),
                    name=str(row["topic_name"]),
                    prerequisite_topic_slugs=tuple(row["prerequisite_topic_slugs"] or []),
                    estimated_hours_beginner=float(row["estimated_hours_beginner"] or 1.0),
                    estimated_hours_review=float(row["estimated_hours_review"] or 0.5),
                )
                if row_kind == "topic":
                    topic = node
                else:
                    prereqs.append(node)
            elif row_kind in {"kc", "sibling_kc"}:
                node = KCNode(
                    slug=str(row["kc_slug"]),
                    topic_slug=str(row["kc_topic_slug"]),
                    module_slug=str(row["kc_module_slug"]),
                    name=str(row["kc_name"]),
                    description=row["kc_description"],
                )
                if row_kind == "kc":
                    kcs.append(node)
                else:
                    sibling_kcs.append(node)
            elif row_kind == "transfer":
                transfers.append(
                    KGEdge(
                        src_kind=row["edge_src_kind"],
                        src_ref=row["edge_src_ref"],
                        dst_kind=row["edge_dst_kind"],
                        dst_ref=row["edge_dst_ref"],
                        type=row["edge_type"],
                        weight=float(row["edge_weight"]),
                        source=row["edge_source"],
                        meta=row["edge_meta"],
                    )
                )

        if topic is None:
            raise KeyError(topic_slug)
        return TopicContext(
            topic=topic,
            prereqs=tuple(sorted(prereqs, key=lambda item: item.slug)),
            kcs=tuple(sorted(kcs, key=lambda item: item.slug)),
            sibling_kcs=tuple(sorted(sibling_kcs, key=lambda item: item.slug)),
            transfers=tuple(
                sorted(transfers, key=lambda edge: (edge.src_ref, edge.dst_ref, edge.type))
            ),
        )

    def _expand_and_sort_topics(
        self,
        target_topics: list[str],
        topics: dict[str, TopicNode],
    ) -> list[str]:
        slugs = _expand_targets(target_topics, topics)
        ordered = _kahn_sort(slugs, topics)
        return _normalize_order_to_targets(ordered, target_topics, topics)

    async def _load_topics_map(self) -> dict[str, TopicNode]:
        if self.session_factory is None:
            raise RuntimeError("session_factory is required for DB-backed KGService")

        async with self.session_factory() as session:
            result = await session.execute(
                sa.text(
                    "SELECT t.id, t.slug, t.name, t.prerequisite_topic_ids, "
                    "       t.estimated_hours_beginner, t.estimated_hours_review, "
                    "       m.slug AS module_slug "
                    "FROM topics t "
                    "JOIN modules m ON m.id = t.module_id "
                    "WHERE t.status = 'published' "
                    "  AND t.slug IS NOT NULL "
                    "  AND m.slug IS NOT NULL "
                    "ORDER BY m.order_index, t.order_index, t.slug"
                )
            )
            rows = result.mappings().all()

        id_to_slug = {str(row["id"]): str(row["slug"]) for row in rows}
        return {
            str(row["slug"]): TopicNode(
                slug=str(row["slug"]),
                module_slug=str(row["module_slug"]),
                name=str(row["name"]),
                prerequisite_topic_slugs=tuple(
                    id_to_slug.get(str(topic_id), str(topic_id))
                    for topic_id in (row["prerequisite_topic_ids"] or [])
                ),
                estimated_hours_beginner=float(row["estimated_hours_beginner"] or 1.0),
                estimated_hours_review=float(row["estimated_hours_review"] or 0.5),
            )
            for row in rows
        }

    async def _load_kcs(self) -> list[KCNode]:
        if self.session_factory is None:
            raise RuntimeError("session_factory is required for DB-backed KGService")

        async with self.session_factory() as session:
            result = await session.execute(
                sa.text(
                    "SELECT kc.slug AS kc_slug, kc.name AS kc_name, "
                    "       kc.description AS kc_description, "
                    "       t.slug AS topic_slug, m.slug AS module_slug "
                    "FROM knowledge_components kc "
                    "JOIN topics t ON t.id = kc.topic_id "
                    "JOIN modules m ON m.id = t.module_id "
                    "WHERE t.status = 'published' "
                    "  AND kc.slug IS NOT NULL "
                    "  AND t.slug IS NOT NULL "
                    "  AND m.slug IS NOT NULL "
                    "ORDER BY m.order_index, t.order_index, kc.name, kc.slug"
                )
            )
            rows = result.mappings().all()

        return [
            KCNode(
                slug=str(row["kc_slug"]),
                topic_slug=str(row["topic_slug"]),
                module_slug=str(row["module_slug"]),
                name=str(row["kc_name"]),
                description=row["kc_description"],
            )
            for row in rows
        ]

    async def _load_edges(self) -> list[KGEdge]:
        if self.repo is not None:
            return [
                KGEdge(
                    src_kind=edge.src_kind,
                    src_ref=edge.src_ref,
                    dst_kind=edge.dst_kind,
                    dst_ref=edge.dst_ref,
                    type=edge.type,
                    weight=edge.weight,
                    source=edge.source,
                    meta=edge.meta,
                )
                for edge in await self.repo.list_edges()
            ]
        if self.session_factory is None:
            raise RuntimeError("session_factory or repo is required for DB-backed KGService")

        async with self.session_factory() as session:
            result = await session.execute(
                sa.text(
                    "SELECT src_kind, src_ref, dst_kind, dst_ref, type, weight, source, meta "
                    "FROM kg_edges "
                    "WHERE deleted_at IS NULL "
                    "ORDER BY type, src_kind, src_ref, dst_kind, dst_ref"
                )
            )
            rows = result.mappings().all()

        return [
            KGEdge(
                src_kind=row["src_kind"],
                src_ref=row["src_ref"],
                dst_kind=row["dst_kind"],
                dst_ref=row["dst_ref"],
                type=row["type"],
                weight=float(row["weight"]),
                source=row["source"],
                meta=row["meta"],
            )
            for row in rows
        ]

    async def _load_recent_topic_slugs(self, user_id: uuid.UUID) -> set[str]:
        if self.session_factory is None:
            return set()

        async with self.session_factory() as session:
            result = await session.execute(
                sa.text(
                    "SELECT DISTINCT t.slug "
                    "FROM user_responses ur "
                    "JOIN questions q ON q.id = ur.question_id "
                    "JOIN topics t ON t.id = q.topic_id "
                    "WHERE ur.user_id = :user_id "
                    "  AND ur.created_at >= now() - interval '1 day' "
                    "  AND t.slug IS NOT NULL"
                ),
                {"user_id": user_id},
            )
            return {str(row["slug"]) for row in result.mappings().all()}

    def _find_shortcuts_for_topic(
        self,
        topic: TopicNode,
        topic_kcs: list[KCNode],
        kc_by_slug: dict[str, KCNode],
        kc_mastery: dict[str, float],
        align_edges: list[KGEdge],
    ) -> list[str]:
        topic_kc_slugs = {kc.slug for kc in topic_kcs}
        mastered_kcs = {
            slug
            for slug, score in kc_mastery.items()
            if score >= settings.kg_shortcut_mastery_threshold
        }
        labels: set[str] = set()

        for edge in align_edges:
            pairs = ((edge.src_ref, edge.dst_ref), (edge.dst_ref, edge.src_ref))
            for mastered_slug, target_slug in pairs:
                if mastered_slug not in mastered_kcs or target_slug not in topic_kc_slugs:
                    continue
                mastered_kc = kc_by_slug.get(mastered_slug)
                target_kc = kc_by_slug.get(target_slug)
                if mastered_kc is None or target_kc is None:
                    continue
                if mastered_kc.module_slug == topic.module_slug:
                    continue
                labels.add(f"{mastered_slug} -> {target_slug}")

        return sorted(labels)


def _group_kcs_by_topic(kcs: list[KCNode]) -> dict[str, list[KCNode]]:
    grouped: dict[str, list[KCNode]] = defaultdict(list)
    for kc in kcs:
        grouped[kc.topic_slug].append(kc)
    return grouped


def _pack_weeks(topics: list[PathTopic], hours_per_week: float) -> list[PathWeek]:
    capacity = max(0.0, hours_per_week) * (1.0 + settings.kg_path_week_buffer)
    if capacity <= 0:
        capacity = float("inf")

    weeks: list[PathWeek] = []
    current_topics: list[PathTopic] = []
    current_hours = 0.0
    current_shortcuts: list[str] = []

    for topic in topics:
        if current_topics and current_hours + topic.hours > capacity:
            weeks.append(
                PathWeek(
                    week_number=len(weeks) + 1,
                    topics=tuple(current_topics),
                    total_hours=round(current_hours, 4),
                    shortcuts=tuple(current_shortcuts),
                )
            )
            current_topics = []
            current_hours = 0.0
            current_shortcuts = []

        current_topics.append(topic)
        current_hours += topic.hours
        current_shortcuts.extend(topic.shortcuts)

    if current_topics:
        weeks.append(
            PathWeek(
                week_number=len(weeks) + 1,
                topics=tuple(current_topics),
                total_hours=round(current_hours, 4),
                shortcuts=tuple(current_shortcuts),
            )
        )
    return weeks


def _prereq_closure(
    topic_slug: str,
    topics: dict[str, TopicNode],
    hops: int | None = None,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    def visit(slug: str, depth: int) -> None:
        if hops is not None and depth > hops:
            return
        for prereq in topics[slug].prerequisite_topic_slugs:
            if prereq not in topics or prereq in seen:
                continue
            seen.add(prereq)
            visit(prereq, depth + 1)
            result.append(prereq)

    visit(topic_slug, 1)
    return result


def _sibling_kc_slugs(topic_kc_slugs: set[str], edges: list[KGEdge]) -> set[str]:
    concept_to_kcs: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge.type != "INSTANCE_OF" or edge.src_kind != "concept" or edge.dst_kind != "kc":
            continue
        concept_to_kcs[edge.src_ref].add(edge.dst_ref)

    siblings: set[str] = set()
    for kc_slugs in concept_to_kcs.values():
        if kc_slugs & topic_kc_slugs:
            siblings.update(kc_slugs - topic_kc_slugs)
    return siblings


def _prereq_ready(topic: TopicNode, topic_mastery: dict[str, float]) -> float:
    prereqs = topic.prerequisite_topic_slugs
    if not prereqs:
        return 1.0
    ready = sum(
        1
        for slug in prereqs
        if topic_mastery.get(slug, 0.0) >= settings.kg_mastery_skip_threshold
    )
    return ready / len(prereqs)


def _transfer_boost(
    topic: TopicNode,
    topic_kcs: list[KCNode],
    edges: list[KGEdge],
    mastered_topics: set[str],
    mastered_kcs: set[str],
) -> float:
    topic_kc_slugs = {kc.slug for kc in topic_kcs}
    boost = 0.0
    for edge in edges:
        if edge.type == "TRANSFERS_TO":
            if edge.dst_ref == topic.slug and edge.src_ref in mastered_topics:
                boost = max(boost, edge.weight)
            if edge.src_ref == topic.slug and edge.dst_ref in mastered_topics:
                boost = max(boost, edge.weight)
        elif edge.type == "ALIGNS_WITH":
            if edge.dst_ref in topic_kc_slugs and edge.src_ref in mastered_kcs:
                boost = max(boost, edge.weight)
            if edge.src_ref in topic_kc_slugs and edge.dst_ref in mastered_kcs:
                boost = max(boost, edge.weight)
    return boost


def _distance_to_terminal_topics(topics: dict[str, TopicNode]) -> dict[str, int]:
    children: dict[str, list[str]] = defaultdict(list)
    for topic in topics.values():
        for prereq in topic.prerequisite_topic_slugs:
            if prereq in topics:
                children[prereq].append(topic.slug)

    terminals = [slug for slug in topics if not children.get(slug)]
    distances = {slug: 0 for slug in terminals}
    queue: deque[str] = deque(terminals)
    reverse_children: dict[str, list[str]] = defaultdict(list)
    for parent, child_slugs in children.items():
        for child in child_slugs:
            reverse_children[child].append(parent)

    while queue:
        slug = queue.popleft()
        for parent in reverse_children.get(slug, []):
            next_distance = distances[slug] + 1
            if parent not in distances or next_distance < distances[parent]:
                distances[parent] = next_distance
                queue.append(parent)
    return distances


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _kahn_sort(
    slugs: set[str],
    topics: dict[str, TopicNode],
) -> list[str]:
    indegree = {slug: 0 for slug in slugs}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for slug in slugs:
        for prereq in topics[slug].prerequisite_topic_slugs:
            if prereq in slugs:
                indegree[slug] += 1
                outgoing[prereq].append(slug)

    queue = deque(sorted(slug for slug, count in indegree.items() if count == 0))
    ordered: list[str] = []
    while queue:
        slug = queue.popleft()
        ordered.append(slug)
        for child in sorted(outgoing.get(slug, [])):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    if len(ordered) != len(slugs):
        missing = sorted(slugs - set(ordered))
        raise ValueError(f"Cycle in topic prerequisites: {' -> '.join(missing)}")
    return ordered


def _expand_targets(target_topics: list[str], topics: dict[str, TopicNode]) -> set[str]:
    slugs: set[str] = set()
    for target in target_topics:
        if target not in topics:
            raise KeyError(target)
        slugs.add(target)
        slugs.update(_prereq_closure(target, topics, hops=None))
    return slugs


def _sort_key_for_targets(target_topics: list[str]):
    target_rank = {slug: index for index, slug in enumerate(target_topics)}
    return lambda slug: (target_rank.get(slug, len(target_rank)), slug)


def _normalize_order_to_targets(
    ordered: list[str],
    target_topics: list[str],
    topics: dict[str, TopicNode],
) -> list[str]:
    target_set = set(target_topics)
    non_targets = [slug for slug in ordered if slug not in target_set]
    targets = sorted([slug for slug in ordered if slug in target_set], key=_sort_key_for_targets(target_topics))
    if len(targets) <= 1:
        return ordered

    final: list[str] = []
    placed: set[str] = set()
    for target in targets:
        needed = set(_prereq_closure(target, topics, hops=None)) | {target}
        for slug in ordered:
            if slug in needed and slug not in placed:
                final.append(slug)
                placed.add(slug)
    for slug in non_targets:
        if slug not in placed:
            final.append(slug)
    return final
