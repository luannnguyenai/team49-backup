#!/usr/bin/env python3
"""
Load modules and topics from data/*.json into database.
Run: python scripts/seed_data.py
"""

import asyncio
import json
import uuid
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_engine, AsyncSessionLocal
from src.models.content import Module, Topic, KnowledgeComponent


async def load_modules_and_topics():
    """Load modules and topics from JSON files into database."""

    # Read JSON files
    modules_file = Path("data/modules.json")
    topics_file = Path("data/topics.json")

    if not modules_file.exists() or not topics_file.exists():
        print(f"Error: {modules_file} or {topics_file} not found")
        return

    with open(modules_file) as f:
        modules_data = json.load(f)
    with open(topics_file) as f:
        topics_data = json.load(f)

    async with AsyncSessionLocal() as session:
        # Clear existing data (optional)
        from sqlalchemy import text
        await session.execute(text("DELETE FROM topics CASCADE"))
        await session.execute(text("DELETE FROM modules CASCADE"))
        await session.commit()

        # Map slug → UUID for modules
        slug_to_module_id: dict[str, str] = {}

        # Create modules
        for m in modules_data:
            module_id = str(uuid.uuid4())
            slug_to_module_id[m["slug"]] = module_id

            # Resolve prerequisite module slugs to UUIDs
            prereq_ids = None
            if m.get("prerequisite_module_slugs"):
                prereq_ids = [slug_to_module_id[s] for s in m["prerequisite_module_slugs"] if s in slug_to_module_id]

            module = Module(
                id=module_id,
                name=m["name"],
                description=m.get("description"),
                order_index=m["order_index"],
                prerequisite_module_ids=prereq_ids,
            )
            session.add(module)
            print(f"✓ Created module: {m['name']}")

        await session.commit()

        # Map slug → UUID for topics
        slug_to_topic_id: dict[str, str] = {}

        # Create topics
        for t in topics_data:
            topic_id = str(uuid.uuid4())
            slug_to_topic_id[t["slug"]] = topic_id

            module_id = slug_to_module_id.get(t["module_slug"])
            if not module_id:
                print(f"⚠ Skipping topic {t['slug']}: module {t['module_slug']} not found")
                continue

            topic = Topic(
                id=topic_id,
                module_id=module_id,
                name=t["name"],
                description=t.get("description"),
                order_index=t["order_index"],
                content_markdown=t.get("content_markdown"),
                video_url=t.get("video_url"),
                estimated_hours_beginner=t.get("estimated_hours_beginner"),
                estimated_hours_intermediate=t.get("estimated_hours_intermediate"),
                estimated_hours_review=t.get("estimated_hours_review"),
            )
            session.add(topic)
            print(f"✓ Created topic: {t['name']}")

        await session.commit()

        # Create knowledge components for topics
        for t in topics_data:
            topic_id = slug_to_topic_id.get(t["slug"])
            if not topic_id:
                continue

            kcs = t.get("knowledge_components", [])
            for kc in kcs:
                knowledge_component = KnowledgeComponent(
                    id=str(uuid.uuid4()),
                    topic_id=topic_id,
                    name=kc["name"],
                    slug=kc.get("slug"),
                )
                session.add(knowledge_component)
                print(f"  ✓ Created KC: {kc['name']}")

        await session.commit()
        print("\n✅ Data seeding complete!")


if __name__ == "__main__":
    asyncio.run(load_modules_and_topics())
