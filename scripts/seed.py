"""
scripts/seed.py
---------------
Seed curriculum data from JSON files into the PostgreSQL database.

Data files (relative to project root):
    data/modules.json       — Module definitions
    data/topics.json        — Topic definitions (with KnowledgeComponents)
    data/question_bank.json — MCQ questions

Run from project root:
    python scripts/seed.py                   # seed everything
    python scripts/seed.py --clear           # drop + re-seed (destructive!)
    python scripts/seed.py --dry-run         # validate JSON without touching DB

Idempotent: re-running without --clear skips already-existing records.
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path when running as a script
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from src.config import settings  # noqa: E402
from src.database import async_session  # noqa: E402
from src.models.content import (  # noqa: E402
    BloomLevel,
    CorrectAnswer,
    DifficultyBucket,
    KnowledgeComponent,
    Module,
    Question,
    QuestionStatus,
    Topic,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
MODULES_FILE = DATA_DIR / "modules.json"
TOPICS_FILE = DATA_DIR / "topics.json"
QUESTIONS_FILE = DATA_DIR / "question_bank.json"


# ===========================================================================
# Loaders
# ===========================================================================


def load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_files() -> None:
    for path in (MODULES_FILE, TOPICS_FILE, QUESTIONS_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Missing data file: {path}")
    print("✓ All JSON files found")


# ===========================================================================
# Seeding logic
# ===========================================================================


async def seed_modules(
    db: AsyncSession,
    module_data: list[dict],
) -> dict[str, uuid.UUID]:
    """Insert modules and return slug → UUID mapping."""
    slug_to_uuid: dict[str, uuid.UUID] = {}

    for m in module_data:
        slug = m["slug"]

        # Check existing by name (idempotent)
        existing = (
            await db.execute(select(Module).where(Module.name == m["name"]))
        ).scalar_one_or_none()

        if existing:
            slug_to_uuid[slug] = existing.id
            print(f"  skip module '{m['name']}' (already exists)")
            continue

        module = Module(
            name=m["name"],
            description=m.get("description"),
            order_index=m["order_index"],
            prerequisite_module_ids=None,  # resolved in second pass
        )
        db.add(module)
        await db.flush()
        await db.refresh(module)
        slug_to_uuid[slug] = module.id
        print(f"  + module '{m['name']}' → {module.id}")

    return slug_to_uuid


async def resolve_module_prerequisites(
    db: AsyncSession,
    module_data: list[dict],
    module_slug_to_uuid: dict[str, uuid.UUID],
) -> None:
    """Second pass: set prerequisite_module_ids now that all UUIDs are known."""
    for m in module_data:
        prereq_slugs = m.get("prerequisite_module_slugs", [])
        if not prereq_slugs:
            continue

        module_id = module_slug_to_uuid[m["slug"]]
        module = (await db.execute(select(Module).where(Module.id == module_id))).scalar_one()

        module.prerequisite_module_ids = [str(module_slug_to_uuid[s]) for s in prereq_slugs]
        db.add(module)

    await db.flush()


async def seed_topics(
    db: AsyncSession,
    topic_data: list[dict],
    module_slug_to_uuid: dict[str, uuid.UUID],
) -> tuple[dict[str, uuid.UUID], dict[str, uuid.UUID]]:
    """
    Insert topics and KnowledgeComponents.
    Returns (topic_slug → UUID, kc_slug → UUID).
    """
    topic_slug_to_uuid: dict[str, uuid.UUID] = {}
    kc_slug_to_uuid: dict[str, uuid.UUID] = {}

    for t in topic_data:
        slug = t["slug"]
        module_id = module_slug_to_uuid[t["module_slug"]]

        # Idempotent check by name + module
        existing = (
            await db.execute(
                select(Topic).where(
                    Topic.module_id == module_id,
                    Topic.name == t["name"],
                )
            )
        ).scalar_one_or_none()

        if existing:
            topic_slug_to_uuid[slug] = existing.id
            # Still need KC mappings
            for kc_def in t.get("knowledge_components", []):
                existing_kc = (
                    await db.execute(
                        select(KnowledgeComponent).where(
                            KnowledgeComponent.topic_id == existing.id,
                            KnowledgeComponent.name == kc_def["name"],
                        )
                    )
                ).scalar_one_or_none()
                if existing_kc:
                    kc_slug_to_uuid[kc_def["slug"]] = existing_kc.id
            print(f"  skip topic '{t['name']}' (already exists)")
            continue

        topic = Topic(
            module_id=module_id,
            name=t["name"],
            description=t.get("description"),
            order_index=t["order_index"],
            prerequisite_topic_ids=None,  # second pass
            estimated_hours_beginner=t.get("estimated_hours_beginner"),
            estimated_hours_intermediate=t.get("estimated_hours_intermediate"),
            estimated_hours_review=t.get("estimated_hours_review"),
            content_markdown=t.get("content_markdown"),
            video_url=t.get("video_url"),
        )
        db.add(topic)
        await db.flush()
        await db.refresh(topic)
        topic_slug_to_uuid[slug] = topic.id
        print(f"  + topic '{t['name']}' → {topic.id}")

        # Seed KnowledgeComponents
        for kc_def in t.get("knowledge_components", []):
            kc = KnowledgeComponent(
                topic_id=topic.id,
                name=kc_def["name"],
                description=kc_def.get("description"),
            )
            db.add(kc)
            await db.flush()
            await db.refresh(kc)
            kc_slug_to_uuid[kc_def["slug"]] = kc.id
            print(f"    + kc '{kc_def['name']}' → {kc.id}")

    return topic_slug_to_uuid, kc_slug_to_uuid


async def resolve_topic_prerequisites(
    db: AsyncSession,
    topic_data: list[dict],
    topic_slug_to_uuid: dict[str, uuid.UUID],
) -> None:
    """Second pass: set prerequisite_topic_ids now that all UUIDs are known."""
    for t in topic_data:
        prereq_slugs = t.get("prerequisite_topic_slugs", [])
        if not prereq_slugs:
            continue

        topic_id = topic_slug_to_uuid[t["slug"]]
        topic = (await db.execute(select(Topic).where(Topic.id == topic_id))).scalar_one()

        topic.prerequisite_topic_ids = [str(topic_slug_to_uuid[s]) for s in prereq_slugs]
        db.add(topic)

    await db.flush()


async def seed_questions(
    db: AsyncSession,
    question_data: list[dict],
    topic_slug_to_uuid: dict[str, uuid.UUID],
    module_slug_to_uuid: dict[str, uuid.UUID],
    kc_slug_to_uuid: dict[str, uuid.UUID],
) -> None:
    """Insert questions, skipping any with duplicate item_id."""
    for q in question_data:
        item_id = q["item_id"]

        # Idempotent check
        existing = (
            await db.execute(select(Question).where(Question.item_id == item_id))
        ).scalar_one_or_none()
        if existing:
            print(f"  skip question '{item_id}' (already exists)")
            continue

        topic_id = topic_slug_to_uuid.get(q["topic_slug"])
        module_id = module_slug_to_uuid.get(q["module_slug"])

        if topic_id is None or module_id is None:
            print(f"  WARN: question '{item_id}' references unknown topic/module slug — skipped")
            continue

        # Resolve KC slugs → UUIDs (best-effort)
        kc_ids: list[str] = []
        for kc_slug in q.get("kc_slugs", []):
            kc_uuid = kc_slug_to_uuid.get(kc_slug)
            if kc_uuid:
                kc_ids.append(str(kc_uuid))
            else:
                print(f"  WARN: KC slug '{kc_slug}' not found, skipping KC link")

        question = Question(
            item_id=item_id,
            version=q.get("version", 1),
            status=QuestionStatus.active,
            topic_id=topic_id,
            module_id=module_id,
            bloom_level=BloomLevel(q["bloom_level"]),
            difficulty_bucket=DifficultyBucket(q["difficulty_bucket"]),
            stem_text=q["stem_text"],
            stem_media=None,
            option_a=q["option_a"],
            option_b=q["option_b"],
            option_c=q["option_c"],
            option_d=q["option_d"],
            correct_answer=CorrectAnswer(q["correct_answer"]),
            distractor_a_rationale=q.get("distractor_a_rationale"),
            distractor_b_rationale=q.get("distractor_b_rationale"),
            distractor_c_rationale=q.get("distractor_c_rationale"),
            distractor_d_rationale=q.get("distractor_d_rationale"),
            explanation_text=q.get("explanation_text"),
            time_expected_seconds=q.get("time_expected_seconds"),
            usage_context=q.get("usage_context"),
            kc_ids=kc_ids if kc_ids else None,
            total_responses=0,
        )
        db.add(question)

        print(f"  + question '{item_id}'")

    await db.flush()


# ===========================================================================
# Clear helpers
# ===========================================================================


async def clear_curriculum(db: AsyncSession) -> None:
    """Delete all curriculum data in FK-safe order."""
    print("Clearing curriculum data...")
    for model in (Question, KnowledgeComponent, Topic, Module):
        await db.execute(delete(model))
    await db.flush()
    print("✓ Cleared")


# ===========================================================================
# Entry point
# ===========================================================================


async def run_seed(clear: bool = False, dry_run: bool = False) -> None:
    print(f"\n{'DRY RUN — ' if dry_run else ''}Seeding database: {settings.database_url}\n")

    validate_files()

    module_data = load_json(MODULES_FILE)
    topic_data = load_json(TOPICS_FILE)
    question_data = load_json(QUESTIONS_FILE)

    print(
        f"Loaded: {len(module_data)} modules, "
        f"{len(topic_data)} topics, "
        f"{len(question_data)} questions\n"
    )

    if dry_run:
        print("Dry run complete — no DB changes.")
        return

    async with async_session() as db:
        try:
            if clear:
                await clear_curriculum(db)

            print("--- Seeding Modules ---")
            module_slug_to_uuid = await seed_modules(db, module_data)
            await resolve_module_prerequisites(db, module_data, module_slug_to_uuid)

            print("\n--- Seeding Topics & KnowledgeComponents ---")
            topic_slug_to_uuid, kc_slug_to_uuid = await seed_topics(
                db, topic_data, module_slug_to_uuid
            )
            await resolve_topic_prerequisites(db, topic_data, topic_slug_to_uuid)

            print("\n--- Seeding Questions ---")
            await seed_questions(
                db,
                question_data,
                topic_slug_to_uuid,
                module_slug_to_uuid,
                kc_slug_to_uuid,
            )

            await db.commit()
            print("\n✓ Seed complete!")

        except Exception:
            await db.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed curriculum data into the database")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing curriculum data before seeding (destructive!)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate JSON files without touching the database",
    )
    args = parser.parse_args()
    asyncio.run(run_seed(clear=args.clear, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
