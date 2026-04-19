"""Fixtures for KG loader integration tests."""

import uuid
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def db_with_seed(db_session: AsyncSession) -> AsyncSession:
    """Insert 2 modules, 6 topics, 12 KCs, and 12 published questions."""
    mod_cv_id = uuid.uuid4()
    mod_nlp_id = uuid.uuid4()

    await db_session.execute(
        sa.text(
            "INSERT INTO modules (id, name, slug, order_index, created_at, updated_at) "
            "VALUES (:cv_id, 'Mini CV', 'mini_cv', 901, now(), now()), "
            "       (:nlp_id, 'Mini NLP', 'mini_nlp', 902, now(), now())"
        ),
        {"cv_id": str(mod_cv_id), "nlp_id": str(mod_nlp_id)},
    )

    topic_ids: dict[str, uuid.UUID] = {}
    for module_id, module_key in ((mod_cv_id, "cv"), (mod_nlp_id, "nlp")):
        for index in range(1, 4):
            topic_id = uuid.uuid4()
            topic_slug = f"mini_{module_key}_t{index}"
            topic_ids[topic_slug] = topic_id
            await db_session.execute(
                sa.text(
                    "INSERT INTO topics "
                    "(id, module_id, name, slug, order_index, status, version, "
                    "created_at, updated_at) "
                    "VALUES (:id, :module_id, :name, :slug, :order_index, "
                    "'published', 1, now(), now())"
                ),
                {
                    "id": str(topic_id),
                    "module_id": str(module_id),
                    "name": f"Mini {module_key.upper()} T{index}",
                    "slug": topic_slug,
                    "order_index": index,
                },
            )

    kc_rows: list[tuple[str, uuid.UUID, uuid.UUID]] = []
    for topic_slug, topic_id in topic_ids.items():
        module_key = "cv" if "_cv_" in topic_slug else "nlp"
        topic_number = topic_slug.split("_t", maxsplit=1)[1]
        for index in range(1, 3):
            kc_id = uuid.uuid4()
            kc_slug = f"KC-mini-{module_key}-t{topic_number}-kc{index}"
            kc_rows.append((kc_slug, kc_id, topic_id))
            await db_session.execute(
                sa.text(
                    "INSERT INTO knowledge_components "
                    "(id, topic_id, name, slug, created_at, updated_at) "
                    "VALUES (:id, :topic_id, :name, :slug, now(), now())"
                ),
                {
                    "id": str(kc_id),
                    "topic_id": str(topic_id),
                    "name": f"Mini KC {kc_slug}",
                    "slug": kc_slug,
                },
            )

    for index, (kc_slug, _kc_id, topic_id) in enumerate(kc_rows, start=1):
        module_id = mod_cv_id if "-cv-" in kc_slug else mod_nlp_id
        await db_session.execute(
            sa.text(
                "INSERT INTO questions ("
                "  id, item_id, version, status, topic_id, module_id,"
                "  bloom_level, difficulty_bucket, stem_text,"
                "  option_a, option_b, option_c, option_d, correct_answer,"
                "  review_status, source, calibration_status,"
                "  created_at, updated_at"
                ") VALUES ("
                "  :id, :item_id, 1, 'active', :topic_id, :module_id,"
                "  'remember', 'easy', :stem,"
                "  'A', 'B', 'C', 'D', 'A',"
                "  'published', 'human', 'uncalibrated',"
                "  now(), now()"
                ")"
            ),
            {
                "id": str(uuid.uuid4()),
                "item_id": f"ITEM-MINI-{index:05d}",
                "topic_id": str(topic_id),
                "module_id": str(module_id),
                "stem": f"Mini question {index}?",
            },
        )

    await db_session.flush()
    return db_session


@pytest.fixture
def mini_bridges_path(tmp_path: Path) -> Path:
    """Copy mini_bridges.yaml into tmp_path/kg_bridges.yaml and return tmp_path."""
    src = Path(__file__).parent / "fixtures" / "mini_bridges.yaml"
    (tmp_path / "kg_bridges.yaml").write_bytes(src.read_bytes())
    return tmp_path
