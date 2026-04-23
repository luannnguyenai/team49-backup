# Canonical Runtime Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move backend runtime reads/writes from legacy `topics/questions/mastery_scores/learning_paths` toward canonical `units/question_bank/item_kp_map/learner_mastery_kp/prerequisite_edges`, without touching frontend/UI and without deleting old data before parity is proven.

**Architecture:** Use an additive cutover. First add explicit bridge keys between product tables and canonical tables, then add canonical repositories/selectors, then write learner/planner state to the new tables behind feature flags. Legacy tables stay readable until parity reports prove the new paths are equivalent or intentionally different.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async ORM, Alembic, PostgreSQL, pytest, canonical JSONL already materialized through `src/models/canonical.py`.

---

## Non-Negotiables

- No frontend/UI edits.
- No truncating, dropping, or clearing old DB tables during this plan.
- No fabricated mapping from `topic_id` to `kp_id`.
- No fabricated mapping from legacy `question_id` to canonical `item_id`.
- New read paths must be feature-flagged until import/backfill/parity checks pass.
- Each task ends with a commit.

## Current Baseline

Already done:

- Canonical content tables exist: `concepts_kp`, `units`, `unit_kp_map`, `question_bank`, `item_calibration`, `item_phase_map`, `item_kp_map`, `prerequisite_edges`, `pruned_edges`.
- Canonical importer exists: `src/scripts/pipeline/import_canonical_artifacts_to_db.py`.
- Learner/planner target tables exist: `learner_mastery_kp`, `goal_preferences`, `waived_units`, `plan_history`, `rationale_log`, `planner_session_state`.
- Safe sidecar writes exist for onboarding goal snapshots and legacy planner audit snapshots.

Still not done:

- Runtime assessment still selects from legacy `questions`.
- Runtime interactions store legacy `question_id`, not canonical `question_bank.item_id`.
- Runtime mastery still writes `mastery_scores`, not `learner_mastery_kp`.
- Runtime planner still reads `topics/mastery_scores/prerequisite_topic_ids`, not canonical units/KP graph.

## File Structure

Expected new files:

- `src/repositories/canonical_question_repo.py`
- `src/repositories/canonical_content_repo.py`
- `src/services/canonical_question_selector.py`
- `src/services/canonical_mastery_service.py`
- `src/services/canonical_planner_service.py`
- `src/scripts/pipeline/backfill_product_canonical_links.py`
- `src/scripts/pipeline/check_canonical_runtime_parity.py`
- `alembic/versions/20260423_runtime_canonical_bridge_columns.py`
- `tests/repositories/test_canonical_question_repo.py`
- `tests/repositories/test_canonical_content_repo.py`
- `tests/services/test_canonical_question_selector.py`
- `tests/services/test_canonical_mastery_service.py`
- `tests/services/test_canonical_planner_service.py`
- `tests/pipeline/test_backfill_product_canonical_links.py`
- `tests/pipeline/test_check_canonical_runtime_parity.py`

Expected modified files:

- `src/config.py`
- `src/models/course.py`
- `src/models/learning.py`
- `src/models/__init__.py`
- `src/repositories/__init__.py`
- `src/services/assessment_service.py`
- `src/services/recommendation_engine.py`
- `src/schemas/assessment.py`
- `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`
- `docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md`
- `docs/WORKLOG.md`
- `docs/JOURNAL.md`

---

## Task 1: Add Runtime-Canonical Bridge Columns

**Purpose:** Make product/runtime rows point to canonical rows explicitly, before changing any read path.

**Files:**

- Modify: `src/models/course.py`
- Modify: `src/models/learning.py`
- Modify: `src/config.py`
- Create: `alembic/versions/20260423_runtime_canonical_bridge_columns.py`
- Test: `tests/test_runtime_canonical_bridge_models.py`
- Test: `tests/test_config.py`

- [x] **Step 1: Add failing model tests**

Create `tests/test_runtime_canonical_bridge_models.py`:

```python
from src.models.course import Course, LearningUnit
from src.models.learning import Interaction, Session


def test_product_tables_have_canonical_bridge_columns():
    assert hasattr(Course, "canonical_course_id")
    assert hasattr(LearningUnit, "canonical_unit_id")


def test_runtime_learning_tables_have_canonical_bridge_columns():
    assert hasattr(Session, "canonical_phase")
    assert hasattr(Interaction, "canonical_item_id")
```

Add to `tests/test_config.py`:

```python
def test_runtime_canonical_cutover_flags_default_to_false():
    settings = Settings()

    assert settings.read_canonical_questions_enabled is False
    assert settings.write_canonical_interactions_enabled is False
    assert settings.read_canonical_planner_enabled is False
```

- [x] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/test_runtime_canonical_bridge_models.py tests/test_config.py -q
```

Expected:

- fails because bridge columns/flags do not exist yet.

- [x] **Step 3: Add bridge columns to ORM**

In `src/models/course.py`, add:

```python
class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    # existing columns...
    canonical_course_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
```

In `LearningUnit`, add:

```python
class LearningUnit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    # existing columns...
    canonical_unit_id: Mapped[str | None] = mapped_column(String(220), nullable=True, index=True)
```

In `src/models/learning.py`, add to `Session`:

```python
canonical_phase: Mapped[str | None] = mapped_column(String(80), nullable=True)
```

Add to `Interaction`:

```python
canonical_item_id: Mapped[str | None] = mapped_column(
    String(180),
    ForeignKey("question_bank.item_id", ondelete="RESTRICT"),
    nullable=True,
)
```

Add index:

```python
Index("ix_interactions_canonical_item_id", "canonical_item_id")
```

- [x] **Step 4: Add cutover flags**

In `src/config.py`, add:

```python
read_canonical_questions_enabled: bool = Field(
    default=False,
    description="Read assessment/quiz items from canonical question_bank during runtime cutover.",
)
write_canonical_interactions_enabled: bool = Field(
    default=False,
    description="Write canonical question item IDs into interactions during runtime cutover.",
)
read_canonical_planner_enabled: bool = Field(
    default=False,
    description="Read planner candidates from canonical learning units and prerequisite graph.",
)
```

- [x] **Step 5: Add Alembic migration**

Create `alembic/versions/20260423_runtime_canonical_bridge_columns.py`:

```python
"""add runtime canonical bridge columns

Revision ID: 20260423_runtime_bridge
Revises: 20260423_canonical_content
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_runtime_bridge"
down_revision = "20260423_canonical_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("canonical_course_id", sa.String(length=80), nullable=True))
    op.create_index("ix_courses_canonical_course_id", "courses", ["canonical_course_id"])

    op.add_column("learning_units", sa.Column("canonical_unit_id", sa.String(length=220), nullable=True))
    op.create_index("ix_learning_units_canonical_unit_id", "learning_units", ["canonical_unit_id"])

    op.add_column("sessions", sa.Column("canonical_phase", sa.String(length=80), nullable=True))

    op.add_column("interactions", sa.Column("canonical_item_id", sa.String(length=180), nullable=True))
    op.create_foreign_key(
        "fk_interactions_canonical_item_id_question_bank",
        "interactions",
        "question_bank",
        ["canonical_item_id"],
        ["item_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_interactions_canonical_item_id", "interactions", ["canonical_item_id"])


def downgrade() -> None:
    op.drop_index("ix_interactions_canonical_item_id", table_name="interactions")
    op.drop_constraint("fk_interactions_canonical_item_id_question_bank", "interactions", type_="foreignkey")
    op.drop_column("interactions", "canonical_item_id")

    op.drop_column("sessions", "canonical_phase")

    op.drop_index("ix_learning_units_canonical_unit_id", table_name="learning_units")
    op.drop_column("learning_units", "canonical_unit_id")

    op.drop_index("ix_courses_canonical_course_id", table_name="courses")
    op.drop_column("courses", "canonical_course_id")
```

- [x] **Step 6: Run tests**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/test_runtime_canonical_bridge_models.py tests/test_config.py tests/test_alembic_heads.py -q
```

Expected:

- pass.

- [x] **Step 7: Commit**

```bash
git add src/models/course.py src/models/learning.py src/config.py alembic/versions/20260423_runtime_canonical_bridge_columns.py tests/test_runtime_canonical_bridge_models.py tests/test_config.py
git commit -m "feat: add runtime canonical bridge columns"
```

---

## Task 2: Backfill Product/Course Links to Canonical Units

**Purpose:** Link `courses` and `learning_units` to canonical `course_id` / `unit_id` without guessing at runtime.

**Files:**

- Create: `src/scripts/pipeline/backfill_product_canonical_links.py`
- Test: `tests/pipeline/test_backfill_product_canonical_links.py`

- [x] **Step 1: Add failing tests**

Create `tests/pipeline/test_backfill_product_canonical_links.py`:

```python
from types import SimpleNamespace

import pytest

from src.scripts.pipeline import backfill_product_canonical_links as script


def test_normalize_course_slug_to_canonical_id():
    assert script.canonical_course_id_from_slug("cs224n") == "CS224n"
    assert script.canonical_course_id_from_slug("cs231n") == "CS231n"


def test_match_learning_unit_to_canonical_unit_by_course_and_lecture():
    product_unit = SimpleNamespace(slug="lecture-01-wordvecs", title="Word Vectors", sort_order=1)
    canonical_units = [
        SimpleNamespace(unit_id="local::lecture01-wordvecs::seg2", course_id="CS224n", lecture_id="lecture-01"),
    ]

    match = script.match_canonical_unit(product_unit, "CS224n", canonical_units)

    assert match == "local::lecture01-wordvecs::seg2"


def test_match_learning_unit_returns_none_when_no_safe_match():
    product_unit = SimpleNamespace(slug="unrelated", title="Unrelated", sort_order=99)
    canonical_units = [
        SimpleNamespace(unit_id="local::lecture01-wordvecs::seg2", course_id="CS224n", lecture_id="lecture-01"),
    ]

    assert script.match_canonical_unit(product_unit, "CS224n", canonical_units) is None
```

- [x] **Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/pipeline/test_backfill_product_canonical_links.py -q
```

Expected:

- fails because script does not exist.

- [x] **Step 3: Implement deterministic matching script**

Create `src/scripts/pipeline/backfill_product_canonical_links.py` with:

```python
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session
from src.models.canonical import CanonicalUnit
from src.models.course import Course, LearningUnit

_LECTURE_RE = re.compile(r"(?:lecture|lec)[-_ ]?0*(\\d+)", re.IGNORECASE)


def canonical_course_id_from_slug(slug: str) -> str | None:
    normalized = slug.strip().lower()
    if normalized == "cs224n":
        return "CS224n"
    if normalized == "cs231n":
        return "CS231n"
    return None


def _lecture_number(value: str | None) -> int | None:
    if not value:
        return None
    match = _LECTURE_RE.search(value)
    return int(match.group(1)) if match else None


def match_canonical_unit(product_unit, canonical_course_id: str, canonical_units: Iterable) -> str | None:
    product_lecture = _lecture_number(getattr(product_unit, "slug", None)) or _lecture_number(getattr(product_unit, "title", None))
    if product_lecture is None:
        return None

    candidates = []
    for unit in canonical_units:
        if getattr(unit, "course_id", None) != canonical_course_id:
            continue
        canonical_lecture = _lecture_number(getattr(unit, "lecture_id", None)) or _lecture_number(getattr(unit, "unit_id", None))
        if canonical_lecture == product_lecture:
            candidates.append(unit)

    if len(candidates) != 1:
        return None
    return candidates[0].unit_id


async def backfill_links(session: AsyncSession, *, dry_run: bool = True) -> dict[str, int]:
    courses = (await session.execute(select(Course))).scalars().all()
    canonical_units = (await session.execute(select(CanonicalUnit))).scalars().all()

    updated_courses = 0
    updated_units = 0
    unmatched_units = 0

    for course in courses:
        canonical_course_id = canonical_course_id_from_slug(course.slug)
        if canonical_course_id and course.canonical_course_id != canonical_course_id:
            updated_courses += 1
            if not dry_run:
                course.canonical_course_id = canonical_course_id

        if not canonical_course_id:
            continue

        for unit in course.learning_units:
            canonical_unit_id = match_canonical_unit(unit, canonical_course_id, canonical_units)
            if canonical_unit_id is None:
                unmatched_units += 1
                continue
            if unit.canonical_unit_id != canonical_unit_id:
                updated_units += 1
                if not dry_run:
                    unit.canonical_unit_id = canonical_unit_id

    if not dry_run:
        await session.flush()

    return {
        "updated_courses": updated_courses,
        "updated_units": updated_units,
        "unmatched_units": unmatched_units,
    }


async def _run(dry_run: bool) -> dict[str, int]:
    async with async_session() as session:
        result = await backfill_links(session, dry_run=dry_run)
        if not dry_run:
            await session.commit()
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    import asyncio

    result = asyncio.run(_run(dry_run=not args.apply))
    print(result)


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/pipeline/test_backfill_product_canonical_links.py -q
```

Expected:

- pass.

- [x] **Step 5: Run dry-run locally**

```bash
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/backfill_product_canonical_links.py
```

Expected:

- prints counts.
- does not write DB unless `--apply` is passed.
- if the target DB has not run `alembic upgrade head`, dry-run fails before writing with missing bridge columns.

- [x] **Step 6: Commit**

```bash
git add src/scripts/pipeline/backfill_product_canonical_links.py tests/pipeline/test_backfill_product_canonical_links.py
git commit -m "feat: backfill product canonical links"
```

---

## Task 3: Add Canonical Question Repository and Selector

**Purpose:** Query `question_bank` by active phase, lecture/unit ownership, and KP mapping without using legacy `questions`.

**Files:**

- Create: `src/repositories/canonical_question_repo.py`
- Create: `src/services/canonical_question_selector.py`
- Modify: `src/repositories/__init__.py`
- Test: `tests/repositories/test_canonical_question_repo.py`
- Test: `tests/services/test_canonical_question_selector.py`

- [x] **Step 1: Add repository tests**

Create `tests/repositories/test_canonical_question_repo.py`:

```python
from unittest.mock import AsyncMock

import pytest

from src.repositories.canonical_question_repo import CanonicalQuestionRepository


@pytest.mark.asyncio
async def test_get_items_for_phase_executes_join_query():
    session = AsyncMock()
    result = AsyncMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    repo = CanonicalQuestionRepository(session)
    rows = await repo.get_items_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=["unit-a"],
        limit=5,
    )

    assert rows == []
    assert session.execute.await_count == 1
```

- [x] **Step 2: Add selector tests**

Create `tests/services/test_canonical_question_selector.py`:

```python
from dataclasses import dataclass

import pytest

from src.services.canonical_question_selector import CanonicalQuestionSelector


@dataclass
class FakeItem:
    item_id: str
    difficulty: str
    question_intent: str


class FakeRepo:
    async def get_items_for_phase(self, *, phase, canonical_unit_ids, kp_ids=None, limit=50):
        return [
            FakeItem("q-hard", "hard", "application"),
            FakeItem("q-easy", "easy", "conceptual"),
            FakeItem("q-medium", "medium", "diagnostic"),
        ]


@pytest.mark.asyncio
async def test_selector_balances_difficulty_for_phase():
    selector = CanonicalQuestionSelector(FakeRepo())

    selected = await selector.select_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=["unit-a"],
        count=2,
    )

    assert [item.item_id for item in selected] == ["q-medium", "q-easy"]
```

- [x] **Step 3: Implement repository**

Create `src/repositories/canonical_question_repo.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import ItemKPMap, ItemPhaseMap, QuestionBankItem


class CanonicalQuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_items_for_phase(
        self,
        *,
        phase: str,
        canonical_unit_ids: list[str],
        kp_ids: list[str] | None = None,
        limit: int = 50,
    ) -> list[QuestionBankItem]:
        stmt = (
            select(QuestionBankItem)
            .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
            .where(
                ItemPhaseMap.phase == phase,
                QuestionBankItem.unit_id.in_(canonical_unit_ids),
            )
            .limit(limit)
        )
        if kp_ids:
            stmt = stmt.join(ItemKPMap, ItemKPMap.item_id == QuestionBankItem.item_id).where(
                ItemKPMap.kp_id.in_(kp_ids)
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

- [x] **Step 4: Implement selector**

Create `src/services/canonical_question_selector.py`:

```python
_DIFFICULTY_ORDER = {"medium": 0, "easy": 1, "hard": 2}


class CanonicalQuestionSelector:
    def __init__(self, repo):
        self.repo = repo

    async def select_for_phase(
        self,
        *,
        phase: str,
        canonical_unit_ids: list[str],
        kp_ids: list[str] | None = None,
        count: int = 5,
    ):
        candidates = await self.repo.get_items_for_phase(
            phase=phase,
            canonical_unit_ids=canonical_unit_ids,
            kp_ids=kp_ids,
            limit=max(count * 4, count),
        )
        ranked = sorted(
            candidates,
            key=lambda item: (
                _DIFFICULTY_ORDER.get(str(getattr(item, "difficulty", "medium")), 1),
                str(getattr(item, "item_id", "")),
            ),
        )
        return ranked[:count]
```

- [x] **Step 5: Export repository**

In `src/repositories/__init__.py`, export:

```python
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
```

- [x] **Step 6: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/repositories/test_canonical_question_repo.py tests/services/test_canonical_question_selector.py -q
```

Expected:

- pass.

- [x] **Step 7: Commit**

```bash
git add src/repositories/canonical_question_repo.py src/services/canonical_question_selector.py src/repositories/__init__.py tests/repositories/test_canonical_question_repo.py tests/services/test_canonical_question_selector.py
git commit -m "feat: add canonical question selection layer"
```

---

## Task 4: Cut Assessment Selection to Canonical Question Bank Behind Flags

**Purpose:** Allow assessment start/submit to use canonical `question_bank` while preserving old API compatibility and old question selection path when flags are off.

**Files:**

- Modify: `src/schemas/assessment.py`
- Modify: `src/services/assessment_service.py`
- Test: `tests/services/test_assessment_canonical_cutover.py`
- Test: `tests/test_assessment_question_selector_integration.py`

- [x] **Step 1: Add failing tests**

Create `tests/services/test_assessment_canonical_cutover.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services import assessment_service


@pytest.mark.asyncio
async def test_start_assessment_uses_canonical_selector_when_flag_enabled(monkeypatch):
    captured = {}
    selected = SimpleNamespace(
        item_id="lecture01-q1",
        question="What is NLP?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        difficulty="medium",
        unit_id="local::lecture01::seg1",
    )

    class FakeSelector:
        def __init__(self, repo):
            captured["repo"] = repo

        async def select_for_phase(self, *, phase, canonical_unit_ids, kp_ids=None, count=5):
            captured["phase"] = phase
            captured["canonical_unit_ids"] = canonical_unit_ids
            return [selected]

    monkeypatch.setattr(assessment_service.settings, "read_canonical_questions_enabled", True)
    monkeypatch.setattr(assessment_service, "CanonicalQuestionSelector", FakeSelector)
    monkeypatch.setattr(assessment_service, "CanonicalQuestionRepository", lambda db: "canonical-repo")

    result = await assessment_service._select_canonical_questions_for_units(
        db=object(),
        canonical_unit_ids=["local::lecture01::seg1"],
        phase="placement",
        count=1,
    )

    assert result == [selected]
    assert captured["phase"] == "placement"
```

- [x] **Step 2: Run test and verify it fails**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/services/test_assessment_canonical_cutover.py -q
```

Expected:

- fails because helper/imports do not exist.

- [x] **Step 3: Extend assessment schema without breaking old fields**

In `src/schemas/assessment.py`, keep old fields and add canonical optional fields:

```python
class QuestionForAssessment(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID | None = None
    item_id: str
    canonical_item_id: str | None = None
    canonical_unit_id: str | None = None
    topic_id: uuid.UUID | None = None
    bloom_level: BloomLevel | None = None
    difficulty_bucket: DifficultyBucket | None = None
    stem_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    time_expected_seconds: int | None = None
```

Update `AnswerInput` to support both old and canonical IDs:

```python
class AnswerInput(BaseModel):
    question_id: uuid.UUID | None = None
    canonical_item_id: str | None = None
    selected_answer: SelectedAnswer
    response_time_ms: int | None = Field(default=None, ge=0)
```

Add validation in service, not schema, so old clients remain accepted.

- [x] **Step 4: Add canonical helper to assessment service**

In `src/services/assessment_service.py`, import:

```python
from src.config import settings
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.services.canonical_question_selector import CanonicalQuestionSelector
```

Add:

```python
async def _select_canonical_questions_for_units(
    db: AsyncSession,
    canonical_unit_ids: list[str],
    phase: str,
    count: int,
):
    selector = CanonicalQuestionSelector(CanonicalQuestionRepository(db))
    return await selector.select_for_phase(
        phase=phase,
        canonical_unit_ids=canonical_unit_ids,
        count=count,
    )
```

- [x] **Step 5: Preserve legacy path while adding canonical branch**

In `start_assessment`, do not remove the existing topic path. Add a canonical branch only when `settings.read_canonical_questions_enabled` is true and the request has canonical unit IDs available.

If current `AssessmentStartRequest` does not yet include `canonical_unit_ids`, add:

```python
canonical_unit_ids: list[str] | None = Field(default=None, max_length=50)
phase: str = Field(default="placement")
```

Branch:

```python
if settings.read_canonical_questions_enabled and request.canonical_unit_ids:
    canonical_items = await _select_canonical_questions_for_units(
        db=db,
        canonical_unit_ids=request.canonical_unit_ids,
        phase=request.phase,
        count=5,
    )
    # Build QuestionForAssessment manually from canonical item fields.
```

- [x] **Step 6: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/services/test_assessment_canonical_cutover.py tests/test_assessment_question_selector_integration.py -q
```

Expected:

- pass.

- [x] **Step 7: Commit**

```bash
git add src/schemas/assessment.py src/services/assessment_service.py tests/services/test_assessment_canonical_cutover.py tests/test_assessment_question_selector_integration.py
git commit -m "feat: route assessment selection to canonical questions"
```

---

## Task 5: Write Canonical Interactions and Learner KP Mastery

**Purpose:** Record canonical item evidence and update `learner_mastery_kp` from `item_kp_map` and `item_calibration`.

**Files:**

- Create: `src/services/canonical_mastery_service.py`
- Create: `alembic/versions/20260423_nullable_interaction_question.py`
- Modify: `src/models/learning.py`
- Modify: `src/services/assessment_service.py`
- Test: `tests/services/test_canonical_mastery_service.py`
- Test: `tests/services/test_assessment_canonical_mastery_cutover.py`

- [x] **Step 1: Add mastery service tests**

Create `tests/services/test_canonical_mastery_service.py`:

```python
import pytest

from src.services.canonical_mastery_service import estimate_mastery_mean, next_theta_mu


def test_estimate_mastery_mean_increases_with_theta():
    assert estimate_mastery_mean(theta_mu=1.0, theta_sigma=0.5) > estimate_mastery_mean(theta_mu=-1.0, theta_sigma=0.5)


def test_next_theta_mu_rewards_correct_answer():
    assert next_theta_mu(current_theta=0.0, is_correct=True, item_weight=0.7) > 0.0
    assert next_theta_mu(current_theta=0.0, is_correct=False, item_weight=0.7) < 0.0
```

- [x] **Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/services/test_canonical_mastery_service.py -q
```

Expected:

- fails because service does not exist.

- [x] **Step 3: Implement simple bounded bootstrap mastery update**

Create `src/services/canonical_mastery_service.py`:

```python
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
```

- [x] **Step 4: Wire assessment submit behind flags**

In `submit_assessment`, when grading a canonical answer:

```python
if settings.write_canonical_interactions_enabled and answer.canonical_item_id:
    interaction.canonical_item_id = answer.canonical_item_id

if settings.write_learner_mastery_kp_enabled and answer.canonical_item_id:
    await update_kp_mastery_from_item(
        db,
        user_id=user_id,
        canonical_item_id=answer.canonical_item_id,
        is_correct=is_correct,
    )
```

Keep legacy `_upsert_mastery_scores` during transition.

Canonical-only interactions require `interactions.question_id` to be nullable while `interactions.canonical_item_id` carries the evidence key. Legacy submissions still populate `question_id`.

- [x] **Step 5: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/services/test_canonical_mastery_service.py tests/services/test_assessment_canonical_mastery_cutover.py tests/repositories/test_learner_mastery_kp_repo.py -q
```

Expected:

- pass.

- [x] **Step 6: Commit**

```bash
git add src/services/canonical_mastery_service.py src/services/assessment_service.py src/models/learning.py alembic/versions/20260423_nullable_interaction_question.py tests/services/test_canonical_mastery_service.py tests/services/test_assessment_canonical_mastery_cutover.py
git commit -m "feat: write canonical learner mastery from assessment evidence"
```

---

## Task 6: Add Canonical Planner Read Model

**Purpose:** Build unit-grain planner candidates from `learning_units + unit_kp_map + prerequisite_edges + learner_mastery_kp`.

**Files:**

- Create: `src/repositories/canonical_content_repo.py`
- Create: `src/services/canonical_planner_service.py`
- Test: `tests/repositories/test_canonical_content_repo.py`
- Test: `tests/services/test_canonical_planner_service.py`

- [x] **Step 1: Add service tests**

Create `tests/services/test_canonical_planner_service.py`:

```python
from dataclasses import dataclass

import pytest

from src.services.canonical_planner_service import classify_unit_action


def test_classify_unit_action_uses_mastery_lcb():
    assert classify_unit_action(mastery_lcb=0.85) == "skip"
    assert classify_unit_action(mastery_lcb=0.55) == "quick_review"
    assert classify_unit_action(mastery_lcb=0.25) == "deep_practice"
```

- [x] **Step 2: Implement planner classifier**

Create `src/services/canonical_planner_service.py`:

```python
def classify_unit_action(mastery_lcb: float) -> str:
    if mastery_lcb >= 0.8:
        return "skip"
    if mastery_lcb >= 0.5:
        return "quick_review"
    return "deep_practice"
```

- [x] **Step 3: Add content repository**

Create `src/repositories/canonical_content_repo.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import PrerequisiteEdge, UnitKPMap
from src.models.course import LearningUnit


class CanonicalContentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_linked_learning_units(self, course_ids):
        result = await self.session.execute(
            select(LearningUnit).where(
                LearningUnit.course_id.in_(course_ids),
                LearningUnit.canonical_unit_id.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def get_unit_kp_rows(self, canonical_unit_ids: list[str]):
        result = await self.session.execute(
            select(UnitKPMap).where(UnitKPMap.unit_id.in_(canonical_unit_ids))
        )
        return list(result.scalars().all())

    async def get_prerequisite_edges_for_kps(self, kp_ids: list[str]):
        result = await self.session.execute(
            select(PrerequisiteEdge).where(
                PrerequisiteEdge.source_kp_id.in_(kp_ids) | PrerequisiteEdge.target_kp_id.in_(kp_ids)
            )
        )
        return list(result.scalars().all())
```

- [x] **Step 4: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/services/test_canonical_planner_service.py tests/repositories/test_canonical_content_repo.py -q
```

Expected:

- pass.

- [x] **Step 5: Commit**

```bash
git add src/repositories/canonical_content_repo.py src/services/canonical_planner_service.py tests/repositories/test_canonical_content_repo.py tests/services/test_canonical_planner_service.py
git commit -m "feat: add canonical planner read model"
```

---

## Task 7: Cut Planner to Canonical Unit-Grain Path Behind Flag

**Purpose:** Replace topic-grain planner reads with unit-grain canonical reads when `read_canonical_planner_enabled=true`, while preserving legacy response compatibility.

**Files:**

- Modify: `src/schemas/learning_path.py`
- Modify: `src/services/recommendation_engine.py`
- Test: `tests/services/test_recommendation_engine_canonical_cutover.py`

- [x] **Step 1: Add failing test**

Create `tests/services/test_recommendation_engine_canonical_cutover.py`:

```python
import pytest

from src.services import recommendation_engine


@pytest.mark.asyncio
async def test_generate_learning_path_uses_canonical_branch_when_flag_enabled(monkeypatch):
    captured = {}

    async def fake_generate_canonical_path(db, user, request):
        captured["called"] = True
        return "canonical-response"

    monkeypatch.setattr(recommendation_engine.settings, "read_canonical_planner_enabled", True)
    monkeypatch.setattr(recommendation_engine, "_generate_canonical_learning_path", fake_generate_canonical_path)

    result = await recommendation_engine.generate_learning_path(object(), object(), object())

    assert result == "canonical-response"
    assert captured["called"] is True
```

- [x] **Step 2: Add branch in `generate_learning_path`**

At top of `generate_learning_path`:

```python
if settings.read_canonical_planner_enabled:
    return await _generate_canonical_learning_path(db, user, request)
```

- [x] **Step 3: Extend response schema backward-compatibly**

In `src/schemas/learning_path.py`, update `PathItemResponse` so old topic paths and new unit paths can coexist:

```python
class PathItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    topic_id: uuid.UUID | None = None
    topic_name: str
    module_name: str
    action: PathAction
    estimated_hours: float | None
    order_index: int
    week_number: int | None
    status: PathStatus
    learning_unit_id: uuid.UUID | None = None
    canonical_unit_id: str | None = None
```

No frontend file changes are required in this task; existing topic-grain responses still populate `topic_id/topic_name/module_name`.

- [x] **Step 4: Implement unit-grain response builder**

Add helper in `src/services/recommendation_engine.py`:

```python
async def _generate_canonical_learning_path(db: AsyncSession, user: User, request: GeneratePathRequest) -> GeneratePathResponse:
    content_repo = CanonicalContentRepository(db)
    audit_repo = PlannerAuditRepository(db)

    goal_repo = GoalPreferenceRepository(db)
    goal = await goal_repo.get_by_user(user.id)
    if goal is None or not goal.selected_course_ids:
        raise ValidationError("Canonical planner requires goal_preferences.selected_course_ids.")

    units = await content_repo.get_linked_learning_units(goal.selected_course_ids)
    if not units:
        raise NotFoundError("No linked canonical learning units found for selected courses.")

    canonical_unit_ids = [unit.canonical_unit_id for unit in units if unit.canonical_unit_id]
    unit_kp_rows = await content_repo.get_unit_kp_rows(canonical_unit_ids)
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})

    mastery_repo = LearnerMasteryKPRepository(db)
    mastery_by_kp = await mastery_repo.get_many_for_user(user.id, kp_ids)

    generated_at = datetime.now(UTC)
    items: list[PathItemResponse] = []
    recommended_path_json = []

    for order_index, unit in enumerate(units):
        unit_kps = [row.kp_id for row in unit_kp_rows if row.unit_id == unit.canonical_unit_id]
        mastery_values = [
            mastery_by_kp[kp_id].mastery_mean_cached
            for kp_id in unit_kps
            if kp_id in mastery_by_kp
        ]
        mastery_lcb = min(mastery_values) if mastery_values else 0.0
        action_value = classify_unit_action(mastery_lcb)
        action = PathAction(action_value)
        estimated_hours = 0.0 if action == PathAction.skip else ((unit.estimated_minutes or 30) / 60.0)

        item = PathItemResponse(
            id=unit.id,
            topic_id=None,
            topic_name=unit.title,
            module_name="canonical_unit",
            action=action,
            estimated_hours=estimated_hours if estimated_hours > 0 else None,
            order_index=order_index,
            week_number=None,
            status=PathStatus.pending,
            learning_unit_id=unit.id,
            canonical_unit_id=unit.canonical_unit_id,
        )
        items.append(item)
        recommended_path_json.append(
            {
                "learning_unit_id": str(unit.id),
                "canonical_unit_id": unit.canonical_unit_id,
                "action": action.value,
                "estimated_hours": estimated_hours,
                "order_index": order_index,
                "kp_ids": unit_kps,
                "mastery_lcb": mastery_lcb,
            }
        )

    total_hours = sum(item.estimated_hours or 0.0 for item in items)
    plan = await audit_repo.create_plan(
        user_id=user.id,
        trigger="generate_canonical_learning_path",
        recommended_path_json=recommended_path_json,
        goal_snapshot_json={
            "selected_course_ids": goal.selected_course_ids,
            "derived_from_course_set_hash": goal.derived_from_course_set_hash,
        },
        weights_used_json={"planner": "canonical_unit_bootstrap"},
    )

    for rank, item in enumerate(items, start=1):
        await audit_repo.add_rationale(
            plan_history_id=plan.id,
            learning_unit_id=item.learning_unit_id,
            rank=rank,
            reason_code=f"canonical_unit_{item.action.value}",
            term_breakdown_json={
                "canonical_unit_id": item.canonical_unit_id,
                "estimated_hours": item.estimated_hours,
            },
            rationale_text=f"Canonical planner selected unit `{item.topic_name}` as `{item.action.value}`.",
        )

    await audit_repo.upsert_session_state(
        user_id=user.id,
        session_id="canonical-learning-path",
        last_plan_history_id=plan.id,
        bridge_chain_depth=0,
        consecutive_bridge_count=0,
        state_json={
            "canonical_runtime": True,
            "generated_at": generated_at.isoformat(),
            "unit_count": len(items),
        },
    )

    return GeneratePathResponse(
        generated_at=generated_at,
        total_topics=len(items),
        total_hours=total_hours,
        required_hours_per_week=None,
        warnings=[],
        items=items,
    )
```

- [x] **Step 5: Write planner audit with real `learning_unit_id`**

For each canonical planner row:

```python
await repo.add_rationale(
    plan_history_id=plan.id,
    learning_unit_id=unit.id,
    rank=rank,
    reason_code=f"canonical_unit_{action}",
    term_breakdown_json={
        "canonical_unit_id": unit.canonical_unit_id,
        "kp_ids": kp_ids,
        "mastery_lcb": mastery_lcb,
        "prereq_blocked": prereq_blocked,
    },
)
```

- [x] **Step 6: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/services/test_recommendation_engine_canonical_cutover.py tests/services/test_recommendation_engine_cutover.py -q
```

Expected:

- pass.

- [x] **Step 7: Commit**

```bash
git add src/schemas/learning_path.py src/services/recommendation_engine.py tests/services/test_recommendation_engine_canonical_cutover.py
git commit -m "feat: route planner to canonical units behind flag"
```

---

## Task 8: Add Parity Report and Freeze Policy

**Purpose:** Prove whether canonical runtime paths are ready before freezing/deleting old data.

**Files:**

- Create: `src/scripts/pipeline/check_canonical_runtime_parity.py`
- Test: `tests/pipeline/test_check_canonical_runtime_parity.py`
- Modify: `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`

- [x] **Step 1: Add parity test**

Create `tests/pipeline/test_check_canonical_runtime_parity.py`:

```python
from src.scripts.pipeline.check_canonical_runtime_parity import classify_parity_status


def test_classify_parity_status_blocks_when_missing_links():
    assert classify_parity_status(unlinked_units=1, missing_question_phase_maps=0) == "blocked"


def test_classify_parity_status_ready_when_clean():
    assert classify_parity_status(unlinked_units=0, missing_question_phase_maps=0) == "ready"
```

- [x] **Step 2: Implement parity helper**

Create `src/scripts/pipeline/check_canonical_runtime_parity.py`:

```python
def classify_parity_status(*, unlinked_units: int, missing_question_phase_maps: int) -> str:
    if unlinked_units > 0 or missing_question_phase_maps > 0:
        return "blocked"
    return "ready"
```

Then extend script with DB queries:

- count `learning_units` where `canonical_unit_id is null`
- count `question_bank` items missing `item_phase_map`
- count `question_bank` items missing `item_kp_map`
- count interactions missing `canonical_item_id` after canonical write flag is enabled

- [x] **Step 3: Document freeze policy**

In `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`, add:

```markdown
## Freeze/Delete Policy

Old tables may only be frozen after parity status is `ready` for two consecutive runs.

Freeze means:
- no new feature writes to `questions`, `mastery_scores`, or `learning_paths`
- old rows remain for audit/backward compatibility

Delete/drop is a separate migration and requires explicit approval.
```

- [x] **Step 4: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest tests/pipeline/test_check_canonical_runtime_parity.py -q
```

Expected:

- pass.

- [x] **Step 5: Commit**

```bash
git add src/scripts/pipeline/check_canonical_runtime_parity.py tests/pipeline/test_check_canonical_runtime_parity.py docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md
git commit -m "feat: add canonical runtime parity checks"
```

---

## Task 9: Final Verification Sweep

**Purpose:** Verify the cutover implementation without changing UI.

**Files:**

- Review only unless tests expose bug.

- [ ] **Step 1: Run focused test suite**

```bash
PYTHONPATH=. .venv/bin/pytest --noconftest \
  tests/test_runtime_canonical_bridge_models.py \
  tests/test_config.py \
  tests/test_alembic_heads.py \
  tests/repositories/test_canonical_question_repo.py \
  tests/repositories/test_canonical_content_repo.py \
  tests/services/test_canonical_question_selector.py \
  tests/services/test_canonical_mastery_service.py \
  tests/services/test_canonical_planner_service.py \
  tests/services/test_assessment_canonical_cutover.py \
  tests/services/test_assessment_canonical_mastery_cutover.py \
  tests/services/test_recommendation_engine_canonical_cutover.py \
  tests/pipeline/test_backfill_product_canonical_links.py \
  tests/pipeline/test_check_canonical_runtime_parity.py \
  tests/pipeline/test_import_canonical_artifacts_to_db.py \
  -q
```

Expected:

- all pass.

- [ ] **Step 2: Validate canonical import**

```bash
PYTHONPATH=. .venv/bin/python src/scripts/pipeline/import_canonical_artifacts_to_db.py --validate-only
```

Expected:

- counts match canonical manifest.

- [ ] **Step 3: Verify no frontend files changed**

```bash
git diff --name-only HEAD~1..HEAD
```

Expected:

- no files under frontend/UI paths.
- no changes under `src/api/static/`.

- [ ] **Step 4: Commit docs if verification notes changed**

```bash
git add docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md docs/WORKLOG.md docs/JOURNAL.md
git commit -m "docs: record canonical runtime cutover verification"
```

---

## Execution Recommendation

Do not implement all tasks in one commit.

Recommended order:

1. Task 1 bridge columns
2. Task 2 backfill links
3. Task 3 canonical question repo/selector
4. Task 4 assessment selection cutover
5. Task 5 learner KP mastery writes
6. Task 6 canonical planner read model
7. Task 7 planner cutover branch
8. Task 8 parity/freeze checks
9. Task 9 verification sweep

The old data should only be frozen after Task 8 reports `ready`. Deleting or truncating old data is explicitly out of scope for this plan and must be a separate approved migration.
