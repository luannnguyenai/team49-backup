"""Knowledge Graph data loader.

Loads published curriculum data from the database and human-authored bridges
YAML, validates referential integrity, and returns immutable loader schemas.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import sqlalchemy as sa
import yaml
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.kg.schemas import BridgesDoc, KCRef, KGConcept, KGEdge, LoadedSources, TopicRef

_KG_NAMESPACE = uuid.UUID("20260419-beef-cafe-0000-000000000000")


class _ConceptEntry(BaseModel):
    """YAML concept entry using a stable string id such as CON-self-attention."""

    id: str
    name: str
    description: str | None = None
    canonical_kc_slug: str | None = None


class _InstanceOfEntry(BaseModel):
    """YAML KC-to-concept bridge entry."""

    kc_slug: str
    concept_id: str


class _TransferEntry(BaseModel):
    """YAML topic-to-topic transfer entry."""

    from_topic: str
    to_topic: str
    weight: float
    reason: str = ""


class _BridgesYAML(BaseModel):
    """Private schema matching the human-readable kg_bridges.yaml shape."""

    concepts: list[_ConceptEntry] = Field(default_factory=list)
    instance_of: list[_InstanceOfEntry] = Field(default_factory=list)
    transfers_to: list[_TransferEntry] = Field(default_factory=list)


def _parse_bridges_yaml(path: Path) -> _BridgesYAML:
    """Parse and validate a kg_bridges.yaml file.

    Args:
        path: Path to the YAML document.

    Returns:
        Validated private YAML schema.

    Raises:
        yaml.YAMLError: If the YAML syntax is invalid.
        ValidationError: If the parsed document does not match the schema.
    """
    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream) or {}
    return _BridgesYAML.model_validate(raw)


def _build_bridges_doc(raw: _BridgesYAML) -> BridgesDoc:
    """Transform parsed YAML entries into the public BridgesDoc schema."""
    concepts = [
        KGConcept(
            id=uuid.uuid5(_KG_NAMESPACE, concept.id),
            name=concept.name,
            description=concept.description,
            canonical_kc_slug=concept.canonical_kc_slug,
            source="manual",
        )
        for concept in raw.concepts
    ]

    instance_of = [
        KGEdge(
            src_kind="concept",
            src_ref=edge.concept_id,
            dst_kind="kc",
            dst_ref=edge.kc_slug,
            type="INSTANCE_OF",
            weight=1.0,
            source="schema",
        )
        for edge in raw.instance_of
    ]

    transfers_to = [
        KGEdge(
            src_kind="topic",
            src_ref=edge.from_topic,
            dst_kind="topic",
            dst_ref=edge.to_topic,
            type="TRANSFERS_TO",
            weight=edge.weight,
            source="schema",
            meta={"reason": edge.reason} if edge.reason else None,
        )
        for edge in raw.transfers_to
    ]

    return BridgesDoc(concepts=concepts, instance_of=instance_of, transfers_to=transfers_to)


def _error(loc: tuple[str, int, str], value: str, message: str) -> dict[str, Any]:
    """Build one pydantic-core error payload."""
    return {
        "type": "value_error",
        "loc": loc,
        "input": value,
        "ctx": {"error": ValueError(message)},
    }


def _raise_integrity_errors(errors: list[dict[str, Any]]) -> None:
    """Raise pydantic.ValidationError when integrity validation failed."""
    if errors:
        raise ValidationError.from_exception_data("kg_bridges.yaml", errors)


def _validate_references(
    raw: _BridgesYAML,
    *,
    topic_slugs: set[str],
    kc_slugs: set[str],
) -> None:
    """Validate YAML references against DB-backed topic and KC slugs.

    Args:
        raw: Parsed bridges YAML.
        topic_slugs: Published topic slugs loaded from the database.
        kc_slugs: Knowledge component slugs loaded from the database.

    Raises:
        ValidationError: If any YAML reference points to a missing topic,
            missing KC, missing canonical KC, or undeclared concept id.
    """
    concept_ids = {concept.id for concept in raw.concepts}
    errors: list[dict[str, Any]] = []

    for index, concept in enumerate(raw.concepts):
        if concept.canonical_kc_slug and concept.canonical_kc_slug not in kc_slugs:
            errors.append(
                _error(
                    ("concepts", index, "canonical_kc_slug"),
                    concept.canonical_kc_slug,
                    "canonical_kc_slug not found in knowledge_components: "
                    f"{concept.canonical_kc_slug}",
                )
            )

    for index, edge in enumerate(raw.instance_of):
        if edge.kc_slug not in kc_slugs:
            errors.append(
                _error(
                    ("instance_of", index, "kc_slug"),
                    edge.kc_slug,
                    f"instance_of kc_slug not found in knowledge_components: {edge.kc_slug}",
                )
            )
        if edge.concept_id not in concept_ids:
            errors.append(
                _error(
                    ("instance_of", index, "concept_id"),
                    edge.concept_id,
                    f"instance_of concept_id not declared in concepts: {edge.concept_id}",
                )
            )

    for index, edge in enumerate(raw.transfers_to):
        if edge.from_topic not in topic_slugs:
            errors.append(
                _error(
                    ("transfers_to", index, "from_topic"),
                    edge.from_topic,
                    f"transfers_to from_topic not found in topics: {edge.from_topic}",
                )
            )
        if edge.to_topic not in topic_slugs:
            errors.append(
                _error(
                    ("transfers_to", index, "to_topic"),
                    edge.to_topic,
                    f"transfers_to to_topic not found in topics: {edge.to_topic}",
                )
            )

    _raise_integrity_errors(errors)


async def _load_topics(session: AsyncSession) -> tuple[list[TopicRef], dict[str, str]]:
    """Load published topic refs and return topic UUID-to-slug mapping."""
    result = await session.execute(
        sa.text(
            "SELECT t.id AS topic_id, t.slug AS topic_slug, t.name AS topic_name, "
            "       t.prerequisite_topic_ids AS prerequisite_topic_ids, "
            "       m.slug AS module_slug "
            "FROM topics t "
            "JOIN modules m ON m.id = t.module_id "
            "WHERE t.status = 'published' "
            "  AND t.slug IS NOT NULL "
            "  AND m.slug IS NOT NULL "
            "ORDER BY m.order_index, t.order_index, t.slug"
        )
    )
    rows = list(result.mappings().all())
    topic_id_to_slug = {str(row["topic_id"]): row["topic_slug"] for row in rows}

    topics = [
        TopicRef(
            slug=row["topic_slug"],
            module_slug=row["module_slug"],
            name=row["topic_name"],
            prerequisite_topic_slugs=tuple(
                topic_id_to_slug.get(str(topic_id), str(topic_id))
                for topic_id in (row["prerequisite_topic_ids"] or [])
            ),
        )
        for row in rows
    ]
    return topics, topic_id_to_slug


async def _load_kcs(session: AsyncSession) -> list[KCRef]:
    """Load KCs that belong to published, slugged topics."""
    result = await session.execute(
        sa.text(
            "SELECT kc.slug AS kc_slug, kc.name AS kc_name, kc.description AS kc_description, "
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
    return [
        KCRef(
            slug=row["kc_slug"],
            topic_slug=row["topic_slug"],
            module_slug=row["module_slug"],
            name=row["kc_name"],
            description=row["kc_description"],
        )
        for row in result.mappings().all()
    ]


async def _load_questions(session: AsyncSession) -> tuple[dict[str, Any], ...]:
    """Load published questions as plain dictionaries for builder input."""
    result = await session.execute(
        sa.text(
            "SELECT q.id AS question_id, q.item_id AS item_id, "
            "       t.slug AS topic_slug, m.slug AS module_slug, q.kc_ids AS kc_ids "
            "FROM questions q "
            "JOIN topics t ON t.id = q.topic_id "
            "JOIN modules m ON m.id = q.module_id "
            "WHERE q.review_status = 'published' "
            "  AND t.status = 'published' "
            "  AND t.slug IS NOT NULL "
            "  AND m.slug IS NOT NULL "
            "ORDER BY q.item_id"
        )
    )
    return tuple(
        {
            "id": str(row["question_id"]),
            "item_id": row["item_id"],
            "topic_slug": row["topic_slug"],
            "module_slug": row["module_slug"],
            "kc_ids": row["kc_ids"] or [],
        }
        for row in result.mappings().all()
    )


async def load_sources(session: AsyncSession, data_dir: Path) -> LoadedSources:
    """Load published DB sources and validated bridges YAML.

    Args:
        session: Active SQLAlchemy async session.
        data_dir: Directory containing ``kg_bridges.yaml``.

    Returns:
        Immutable LoadedSources assembled from DB rows and bridges YAML.

    Raises:
        yaml.YAMLError: If ``kg_bridges.yaml`` is syntactically invalid.
        ValidationError: If YAML shape or referential integrity is invalid.
    """
    topics, _topic_id_to_slug = await _load_topics(session)
    kcs = await _load_kcs(session)
    questions = await _load_questions(session)

    raw_bridges = _parse_bridges_yaml(data_dir / "kg_bridges.yaml")
    _validate_references(
        raw_bridges,
        topic_slugs={topic.slug for topic in topics},
        kc_slugs={kc.slug for kc in kcs},
    )
    bridges = _build_bridges_doc(raw_bridges)

    return LoadedSources(topics=topics, kcs=kcs, questions=questions, bridges=bridges)
