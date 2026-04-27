# Onboarding Redesign + Placement Assessment (2PL IRT) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign 4-step onboarding thành 5-step goal-driven flow với placement assessment 2PL IRT per-topic để cá nhân hóa learning path ngay từ đầu, thêm Phase A/B hard gate vào recommendation engine.

**Architecture:** New table `placement_assessment_results` lưu per-topic score + decision; placement service chọn 5 items/unit theo `difficulty_prior` bucket (1 easy / 2 medium / 2 hard); recommendation engine đọc placement decisions để chia path thành Phase A (remediation, prereq-ordered) và Phase B (new learning, locked cho đến khi Phase A mastered ≥ 0.7 LCB); backward-compat với user cũ đã có `goal_preferences`.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic; Pydantic v2; Next.js 14 App Router + Zustand + Tailwind + existing components.

---

## File Map

### Backend — New files
| File | Responsibility |
|------|---------------|
| `alembic/versions/20260425_placement_asmnt.py` | CREATE `placement_assessment_results` table |
| `src/config/goal_course_map.py` | Static mapping `goal_id → canonical_course_id` |
| `src/models/placement.py` | `PlacementAssessmentResult` ORM model |
| `src/repositories/placement_assessment_repo.py` | DB CRUD cho `placement_assessment_results` |
| `src/services/placement_assessment_service.py` | Question selection (difficulty-bucketed) + scoring + decision |
| `src/routers/placement_assessment.py` | `POST /api/placement-assessment/start`, `/submit`, `GET /results` |

### Backend — Modified files
| File | Change |
|------|--------|
| `src/models/__init__.py` | Import `PlacementAssessmentResult` |
| `src/repositories/canonical_question_repo.py` | New method `get_items_for_placement_bucketed` |
| `src/schemas/auth.py` | Add `goal_ids: list[str]` to `OnboardingRequest` |
| `src/services/auth_service.py` | Map `goal_ids → selected_course_ids` via goal_course_map |
| `src/schemas/learning_path.py` | Add `phase_tag: str | None` + `is_locked: bool` to `PathItemResponse` |
| `src/services/recommendation_engine.py` | Phase A/B split + rationale log per Phase A node |
| `src/api/app.py` | Include `placement_assessment_router` |

### Frontend — New files
| File | Responsibility |
|------|---------------|
| `frontend/stores/onboardingStore.ts` | Wizard state (goal_ids, selected_unit_ids, placement answers, decisions) |
| `frontend/lib/placement-assessment-api.ts` | API calls cho placement start/submit/results |
| `frontend/components/onboarding/StepGoalSelection.tsx` | Step 1: multi-select `computer_vision` / `nlp` |
| `frontend/components/onboarding/StepKnownTopicsFiltered.tsx` | Step 2: units filtered by selected goals |
| `frontend/components/onboarding/StepPlacementTest.tsx` | Step 5: render questions, collect answers, submit |

### Frontend — Modified files
| File | Change |
|------|--------|
| `frontend/app/onboarding/page.tsx` | Redesign: 5 steps, goal-driven, new routing logic |
| `frontend/lib/onboarding-schema.ts` | Add `goal_ids`, relax `desired_section_ids` to optional |
| `frontend/types/index.ts` | Add `OnboardingPayload.goal_ids`, placement types |

---

## Task 1: DB Migration — `placement_assessment_results`

**Files:**
- Create: `alembic/versions/20260425_placement_asmnt.py`
- Modify: `tests/test_alembic_heads.py` (read-only verification, no changes needed)

- [ ] **Step 1: Write failing test**

```python
# tests/test_placement_assessment_migration.py
import subprocess
import unittest
from pathlib import Path


class PlacementAssessmentMigrationTests(unittest.TestCase):
    def test_migration_file_exists(self):
        files = list(Path("alembic/versions").glob("20260425_placement_asmnt.py"))
        self.assertEqual(len(files), 1, "Migration file 20260425_placement_asmnt.py not found")

    def test_revision_id_fits_varchar32(self):
        text = Path("alembic/versions/20260425_placement_asmnt.py").read_text()
        import ast
        for line in text.splitlines():
            if line.startswith("revision: str ="):
                rev_id = ast.literal_eval(line.split("=", 1)[1].strip())
                self.assertLessEqual(len(rev_id), 32, f"Revision ID too long: {rev_id}")
                break

    def test_alembic_single_head_after_migration(self):
        result = subprocess.run(
            [".venv/bin/alembic", "heads"],
            check=True, capture_output=True, text=True,
        )
        heads = [l for l in result.stdout.strip().splitlines() if l.strip()]
        self.assertEqual(len(heads), 1, f"Expected single head, got: {heads}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_placement_assessment_migration.py -v
```
Expected: FAIL — file does not exist.

- [ ] **Step 3: Write migration**

```python
# alembic/versions/20260425_placement_asmnt.py
"""Add placement_assessment_results table.

Revision ID: 20260425_placement_asmnt
Revises: 20260424_resume_state
Create Date: 2026-04-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260425_placement_asmnt"
down_revision: str | None = "20260424_resume_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "placement_assessment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_unit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("learning_units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("user_choice", sa.Text(), nullable=True),
        sa.Column("raw_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default="[]"),
        sa.Column("theta_estimate", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "decision IN ('skip', 'review', 'relearn')",
            name="ck_placement_results_decision",
        ),
        sa.CheckConstraint(
            "user_choice IS NULL OR user_choice IN ('skip', 'review')",
            name="ck_placement_results_user_choice",
        ),
        sa.CheckConstraint(
            "score_pct >= 0 AND score_pct <= 100",
            name="ck_placement_results_score_range",
        ),
    )
    op.create_index(
        "ix_placement_results_user_unit",
        "placement_assessment_results",
        ["user_id", "topic_unit_id"],
    )
    op.create_index(
        "ix_placement_results_user",
        "placement_assessment_results",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_placement_results_user", table_name="placement_assessment_results")
    op.drop_index("ix_placement_results_user_unit", table_name="placement_assessment_results")
    op.drop_table("placement_assessment_results")
```

- [ ] **Step 4: Run test to verify passes**

```bash
python -m pytest tests/test_placement_assessment_migration.py -v
python -m pytest tests/test_alembic_heads.py -v
```
Expected: PASS (single head, revision ID ≤ 32 chars).

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/20260425_placement_asmnt.py tests/test_placement_assessment_migration.py
git commit -m "feat(db): add placement_assessment_results table"
```

---

## Task 2: Config + ORM Model

**Files:**
- Create: `src/config/__init__.py` (empty)
- Create: `src/config/goal_course_map.py`
- Create: `src/models/placement.py`
- Modify: `src/models/__init__.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_placement_models.py
import unittest


class GoalCourseMapTests(unittest.TestCase):
    def test_goal_course_map_has_required_keys(self):
        from src.config.goal_course_map import GOAL_COURSE_MAP, GOAL_LABELS
        self.assertIn("computer_vision", GOAL_COURSE_MAP)
        self.assertIn("nlp", GOAL_COURSE_MAP)
        self.assertEqual(GOAL_COURSE_MAP["computer_vision"], "cs231n")
        self.assertEqual(GOAL_COURSE_MAP["nlp"], "cs224n")
        self.assertIn("computer_vision", GOAL_LABELS)
        self.assertIn("nlp", GOAL_LABELS)

    def test_placement_result_model_importable(self):
        from src.models.placement import PlacementAssessmentResult  # noqa
        self.assertTrue(hasattr(PlacementAssessmentResult, "__tablename__"))
        self.assertEqual(PlacementAssessmentResult.__tablename__, "placement_assessment_results")

    def test_placement_result_registered_in_init(self):
        import src.models as models
        self.assertTrue(hasattr(models, "PlacementAssessmentResult"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify fails**

```bash
python -m pytest tests/test_placement_models.py -v
```
Expected: FAIL — ImportError.

- [ ] **Step 3: Create `src/config/__init__.py`**

```python
# src/config/__init__.py
```

- [ ] **Step 4: Create `src/config/goal_course_map.py`**

```python
# src/config/goal_course_map.py
# Static mapping: onboarding goal_id → canonical course_id used by planner.
GOAL_COURSE_MAP: dict[str, str] = {
    "computer_vision": "cs231n",
    "nlp": "cs224n",
}

GOAL_LABELS: dict[str, str] = {
    "computer_vision": "Computer Vision (CS231n)",
    "nlp": "Natural Language Processing (CS224n)",
}

VALID_GOAL_IDS: frozenset[str] = frozenset(GOAL_COURSE_MAP.keys())
```

- [ ] **Step 5: Create `src/models/placement.py`**

```python
# src/models/placement.py
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.base import Base


class PlacementAssessmentResult(Base):
    """Per-topic result row after a user completes placement assessment."""

    __tablename__ = "placement_assessment_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    score_pct: Mapped[Decimal] = mapped_column(Numeric(precision=5, scale=2), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    user_choice: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_answers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    theta_estimate: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=8, scale=4), nullable=True
    )
    created_at: Mapped[uuid.UUID] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "decision IN ('skip', 'review', 'relearn')",
            name="ck_placement_results_decision",
        ),
        CheckConstraint(
            "user_choice IS NULL OR user_choice IN ('skip', 'review')",
            name="ck_placement_results_user_choice",
        ),
        CheckConstraint(
            "score_pct >= 0 AND score_pct <= 100",
            name="ck_placement_results_score_range",
        ),
        Index("ix_placement_results_user_unit", "user_id", "topic_unit_id"),
        Index("ix_placement_results_user", "user_id"),
    )
```

- [ ] **Step 6: Add import to `src/models/__init__.py`**

Add after the `from src.models.learning import (...)` block:

```python
from src.models.placement import PlacementAssessmentResult  # noqa: F401
```

Add `"PlacementAssessmentResult"` to `__all__`.

- [ ] **Step 7: Run tests to verify pass**

```bash
python -m pytest tests/test_placement_models.py -v
```
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/config/__init__.py src/config/goal_course_map.py src/models/placement.py src/models/__init__.py tests/test_placement_models.py
git commit -m "feat: add goal_course_map config and PlacementAssessmentResult ORM model"
```

---

## Task 3: Repository — Placement Assessment

**Files:**
- Modify: `src/repositories/canonical_question_repo.py`
- Create: `src/repositories/placement_assessment_repo.py`

- [ ] **Step 1: Write failing test**

```python
# tests/repositories/test_placement_assessment_repo.py
import pytest


@pytest.mark.asyncio
async def test_placement_repo_get_by_user_returns_empty(db_session):
    import uuid
    from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
    repo = PlacementAssessmentRepository(db_session)
    results = await repo.get_by_user_id(uuid.uuid4())
    assert results == []


@pytest.mark.asyncio
async def test_canonical_question_repo_bucketed_returns_list(db_session):
    from src.repositories.canonical_question_repo import CanonicalQuestionRepository
    repo = CanonicalQuestionRepository(db_session)
    result = await repo.get_items_for_placement_bucketed(
        canonical_unit_ids=["nonexistent_unit"],
        phase="placement_assessment",
    )
    # Empty list when no data — no exception
    assert isinstance(result, list)
```

- [ ] **Step 2: Run test to verify fails**

```bash
python -m pytest tests/repositories/test_placement_assessment_repo.py -v
```
Expected: FAIL — ImportError.

- [ ] **Step 3: Add `get_items_for_placement_bucketed` to `src/repositories/canonical_question_repo.py`**

Append after the existing `get_items_for_phase` method:

```python
    async def get_items_for_placement_bucketed(
        self,
        *,
        canonical_unit_ids: list[str],
        phase: str = "placement_assessment",
    ) -> list[tuple["QuestionBankItem", float | None]]:
        """
        Returns (item, difficulty_prior) pairs for all units, filtered by phase.
        Caller buckets into easy/medium/hard and selects 1/2/2 per unit.
        """
        from src.models.canonical import ItemCalibration

        if not canonical_unit_ids:
            return []

        stmt = (
            select(QuestionBankItem, ItemCalibration.difficulty_prior)
            .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
            .outerjoin(
                ItemCalibration, ItemCalibration.item_id == QuestionBankItem.item_id
            )
            .where(
                ItemPhaseMap.phase == phase,
                QuestionBankItem.unit_id.in_(canonical_unit_ids),
            )
            .order_by(QuestionBankItem.unit_id, ItemCalibration.difficulty_prior.asc().nulls_last())
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
```

Note: add `from sqlalchemy import select` import at top if not already present (it is already in the file).

- [ ] **Step 4: Create `src/repositories/placement_assessment_repo.py`**

```python
# src/repositories/placement_assessment_repo.py
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.placement import PlacementAssessmentResult


class PlacementAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[PlacementAssessmentResult]:
        stmt = select(PlacementAssessmentResult).where(
            PlacementAssessmentResult.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_unit(
        self, user_id: uuid.UUID, topic_unit_id: uuid.UUID
    ) -> PlacementAssessmentResult | None:
        stmt = select(PlacementAssessmentResult).where(
            PlacementAssessmentResult.user_id == user_id,
            PlacementAssessmentResult.topic_unit_id == topic_unit_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        topic_unit_id: uuid.UUID,
        score_pct: float,
        decision: str,
        raw_answers: list[dict],
        theta_estimate: float | None = None,
        user_choice: str | None = None,
    ) -> PlacementAssessmentResult:
        existing = await self.get_by_user_and_unit(user_id, topic_unit_id)
        if existing is not None:
            existing.score_pct = score_pct  # type: ignore[assignment]
            existing.decision = decision
            existing.raw_answers = raw_answers
            existing.theta_estimate = theta_estimate  # type: ignore[assignment]
            existing.user_choice = user_choice
            self.session.add(existing)
            return existing

        row = PlacementAssessmentResult(
            user_id=user_id,
            topic_unit_id=topic_unit_id,
            score_pct=score_pct,
            decision=decision,
            raw_answers=raw_answers,
            theta_estimate=theta_estimate,
            user_choice=user_choice,
        )
        self.session.add(row)
        await self.session.flush()
        return row
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/repositories/test_placement_assessment_repo.py -v
```
Expected: PASS (skipped if DB unavailable; otherwise PASS).

- [ ] **Step 6: Commit**

```bash
git add src/repositories/canonical_question_repo.py src/repositories/placement_assessment_repo.py tests/repositories/test_placement_assessment_repo.py
git commit -m "feat: add placement question repo (difficulty-bucketed) and PlacementAssessmentRepository"
```

---

## Task 4: Placement Assessment Service

**Files:**
- Create: `src/services/placement_assessment_service.py`
- Create: `src/schemas/placement_assessment.py`

- [ ] **Step 1: Write failing test**

```python
# tests/services/test_placement_assessment_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_item(item_id: str, unit_id: str, difficulty: float | None):
    item = MagicMock()
    item.item_id = item_id
    item.unit_id = unit_id
    item.question = f"Question {item_id}"
    item.choices = ["A", "B", "C", "D"]
    item.answer_index = 0
    item.difficulty = "medium"
    item.explanation = None
    return item, difficulty


class TestBucketSelection:
    def test_bucket_5_items_from_mixed_difficulties(self):
        from src.services.placement_assessment_service import _bucket_select_5

        pairs = [
            _make_item("i1", "u1", -1.0),   # easy
            _make_item("i2", "u1", -0.6),   # easy
            _make_item("i3", "u1", 0.0),    # medium
            _make_item("i4", "u1", 0.3),    # medium
            _make_item("i5", "u1", 0.5),    # medium (boundary — goes to medium)
            _make_item("i6", "u1", 0.8),    # hard
            _make_item("i7", "u1", 1.2),    # hard
        ]
        selected = _bucket_select_5(pairs)
        assert len(selected) == 5

    def test_classify_decision_skip(self):
        from src.services.placement_assessment_service import _classify_decision
        assert _classify_decision(75.0) == "skip"

    def test_classify_decision_review(self):
        from src.services.placement_assessment_service import _classify_decision
        assert _classify_decision(60.0) == "review"
        assert _classify_decision(50.0) == "review"

    def test_classify_decision_relearn(self):
        from src.services.placement_assessment_service import _classify_decision
        assert _classify_decision(49.9) == "relearn"
        assert _classify_decision(0.0) == "relearn"
```

- [ ] **Step 2: Run test to verify fails**

```bash
python -m pytest tests/services/test_placement_assessment_service.py -v
```
Expected: FAIL — ImportError.

- [ ] **Step 3: Create `src/schemas/placement_assessment.py`**

```python
# src/schemas/placement_assessment.py
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PlacementStartRequest(BaseModel):
    """POST /api/placement-assessment/start"""
    topic_unit_ids: list[uuid.UUID] = Field(
        min_length=1,
        description="learning_units.id values selected at onboarding Step 2",
    )


class PlacementQuestion(BaseModel):
    item_id: str
    canonical_unit_id: str
    topic_unit_id: uuid.UUID
    stem_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class PlacementStartResponse(BaseModel):
    session_id: uuid.UUID
    total_questions: int
    questions: list[PlacementQuestion]
    topic_unit_ids: list[uuid.UUID]


class PlacementAnswerInput(BaseModel):
    item_id: str
    selected_answer: str = Field(pattern="^[ABCD]$")
    topic_unit_id: uuid.UUID


class PlacementSubmitRequest(BaseModel):
    """POST /api/placement-assessment/submit"""
    session_id: uuid.UUID
    answers: list[PlacementAnswerInput]


class TopicDecision(BaseModel):
    topic_unit_id: uuid.UUID
    score_pct: float
    decision: str
    user_choice: str | None = None


class PlacementSubmitResponse(BaseModel):
    session_id: uuid.UUID
    topic_decisions: list[TopicDecision]
    skipped_count: int
    review_count: int
    relearn_count: int


class PlacementResultsResponse(BaseModel):
    results: list[TopicDecision]
    has_placement: bool


class TopicUserChoiceRequest(BaseModel):
    """PATCH /api/placement-assessment/topic-decision"""
    topic_unit_id: uuid.UUID
    user_choice: str = Field(pattern="^(skip|review)$")
```

- [ ] **Step 4: Create `src/services/placement_assessment_service.py`**

```python
# src/services/placement_assessment_service.py
"""
Placement assessment service — 2PL IRT bucketed question selection + scoring.

Per topic (learning_unit): selects 5 questions with distribution:
  - 1 Easy:   difficulty_prior <= -0.5
  - 2 Medium: -0.5 < difficulty_prior <= 0.5
  - 2 Hard:   difficulty_prior > 0.5
Falls back to any available questions if a bucket is empty.

Scoring gate (per topic):
  score_pct >= 70  → skip
  50 <= score_pct < 70 → review
  score_pct < 50   → relearn
"""
from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.models.canonical import QuestionBankItem
from src.models.course import LearningUnit
from src.models.learning import Session, SessionType
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
from src.schemas.placement_assessment import (
    PlacementAnswerInput,
    PlacementQuestion,
    PlacementStartResponse,
    PlacementSubmitResponse,
    TopicDecision,
)


def _bucket_select_5(
    pairs: list[tuple[QuestionBankItem, float | None]],
) -> list[tuple[QuestionBankItem, float | None]]:
    easy = [p for p in pairs if p[1] is not None and p[1] <= -0.5]
    medium = [p for p in pairs if p[1] is None or (-0.5 < p[1] <= 0.5)]
    hard = [p for p in pairs if p[1] is not None and p[1] > 0.5]

    selected: list[tuple[QuestionBankItem, float | None]] = []
    selected += easy[:1]
    selected += medium[:2]
    selected += hard[:2]

    # Fill gaps from remaining candidates if buckets were thin
    remaining = [p for p in pairs if p not in selected]
    while len(selected) < 5 and remaining:
        selected.append(remaining.pop(0))

    return selected[:5]


def _classify_decision(score_pct: float) -> str:
    if score_pct >= 70.0:
        return "skip"
    if score_pct >= 50.0:
        return "review"
    return "relearn"


def _item_to_placement_question(
    item: QuestionBankItem, topic_unit_id: uuid.UUID
) -> PlacementQuestion:
    choices = list(item.choices or [])
    padded = (choices + ["", "", "", ""])[:4]
    return PlacementQuestion(
        item_id=item.item_id,
        canonical_unit_id=item.unit_id,
        topic_unit_id=topic_unit_id,
        stem_text=item.question,
        option_a=str(padded[0]),
        option_b=str(padded[1]),
        option_c=str(padded[2]),
        option_d=str(padded[3]),
    )


async def start_placement_assessment(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    topic_unit_ids: list[uuid.UUID],
) -> PlacementStartResponse:
    from sqlalchemy import select

    result = await db.execute(
        select(LearningUnit).where(LearningUnit.id.in_(topic_unit_ids))
    )
    units = {u.id: u for u in result.scalars().all()}
    if not units:
        raise NotFoundError("None of the requested learning units were found.")

    question_repo = CanonicalQuestionRepository(db)
    all_questions: list[PlacementQuestion] = []

    for unit_id in topic_unit_ids:
        unit = units.get(unit_id)
        if unit is None or not unit.canonical_unit_id:
            continue
        pairs = await question_repo.get_items_for_placement_bucketed(
            canonical_unit_ids=[unit.canonical_unit_id],
            phase="placement_assessment",
        )
        selected = _bucket_select_5(pairs)
        all_questions += [_item_to_placement_question(item, unit_id) for item, _ in selected]

    if not all_questions:
        raise ValidationError(
            "No placement_assessment questions found for the selected topics. "
            "Ensure item_phase_map rows with phase='placement_assessment' exist."
        )

    session = Session(
        user_id=user_id,
        session_type=SessionType.assessment,
        canonical_phase="placement_assessment",
        total_questions=len(all_questions),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return PlacementStartResponse(
        session_id=session.id,
        total_questions=len(all_questions),
        questions=all_questions,
        topic_unit_ids=list(topic_unit_ids),
    )


async def submit_placement_assessment(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    answers: list[PlacementAnswerInput],
) -> PlacementSubmitResponse:
    from sqlalchemy import select
    from src.models.canonical import QuestionBankItem as QB

    # Load correct answers
    item_ids = [a.item_id for a in answers]
    result = await db.execute(select(QB).where(QB.item_id.in_(item_ids)))
    items_by_id = {item.item_id: item for item in result.scalars().all()}

    _ANSWER_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}

    # Group answers by topic_unit_id
    by_unit: dict[uuid.UUID, list[PlacementAnswerInput]] = defaultdict(list)
    for ans in answers:
        by_unit[ans.topic_unit_id].append(ans)

    placement_repo = PlacementAssessmentRepository(db)
    topic_decisions: list[TopicDecision] = []

    for topic_unit_id, unit_answers in by_unit.items():
        correct = sum(
            1
            for ans in unit_answers
            if (item := items_by_id.get(ans.item_id)) is not None
            and _ANSWER_INDEX.get(ans.selected_answer, -1) == item.answer_index
        )
        score_pct = (correct / len(unit_answers) * 100) if unit_answers else 0.0
        decision = _classify_decision(score_pct)
        raw_answers = [
            {"item_id": a.item_id, "selected": a.selected_answer}
            for a in unit_answers
        ]
        await placement_repo.upsert(
            user_id=user_id,
            topic_unit_id=topic_unit_id,
            score_pct=score_pct,
            decision=decision,
            raw_answers=raw_answers,
        )
        topic_decisions.append(
            TopicDecision(
                topic_unit_id=topic_unit_id,
                score_pct=score_pct,
                decision=decision,
            )
        )

    # Mark session complete
    from sqlalchemy import select as sel
    sess_result = await db.execute(sel(Session).where(Session.id == session_id))
    session = sess_result.scalar_one_or_none()
    if session and session.user_id == user_id:
        session.correct_count = sum(
            1 for a in answers
            if (item := items_by_id.get(a.item_id)) is not None
            and _ANSWER_INDEX.get(a.selected_answer, -1) == item.answer_index
        )
        session.score_percent = (
            session.correct_count / len(answers) * 100 if answers else 0.0
        )
        from datetime import UTC, datetime
        session.completed_at = datetime.now(UTC)
        db.add(session)

    await db.flush()

    skip_count = sum(1 for d in topic_decisions if d.decision == "skip")
    review_count = sum(1 for d in topic_decisions if d.decision == "review")
    relearn_count = sum(1 for d in topic_decisions if d.decision == "relearn")

    return PlacementSubmitResponse(
        session_id=session_id,
        topic_decisions=topic_decisions,
        skipped_count=skip_count,
        review_count=review_count,
        relearn_count=relearn_count,
    )
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/services/test_placement_assessment_service.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/schemas/placement_assessment.py src/services/placement_assessment_service.py tests/services/test_placement_assessment_service.py
git commit -m "feat: placement assessment service — bucketed question selection and scoring"
```

---

## Task 5: Placement Assessment Router + App Wiring

**Files:**
- Create: `src/routers/placement_assessment.py`
- Modify: `src/api/app.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_placement_assessment_router.py
import pytest


@pytest.mark.asyncio
async def test_placement_start_requires_auth(client):
    response = await client.post(
        "/api/placement-assessment/start",
        json={"topic_unit_ids": ["00000000-0000-0000-0000-000000000001"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_placement_results_requires_auth(client):
    response = await client.get("/api/placement-assessment/results")
    assert response.status_code == 401
```

- [ ] **Step 2: Run test to verify fails**

```bash
python -m pytest tests/test_placement_assessment_router.py -v
```
Expected: FAIL — 404 (route not registered yet).

- [ ] **Step 3: Create `src/routers/placement_assessment.py`**

```python
# src/routers/placement_assessment.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
from src.schemas.placement_assessment import (
    PlacementResultsResponse,
    PlacementStartRequest,
    PlacementStartResponse,
    PlacementSubmitRequest,
    PlacementSubmitResponse,
    TopicDecision,
    TopicUserChoiceRequest,
)
from src.services.placement_assessment_service import (
    start_placement_assessment,
    submit_placement_assessment,
)

placement_assessment_router = APIRouter(
    prefix="/api/placement-assessment",
    tags=["placement-assessment"],
)


@placement_assessment_router.post("/start", response_model=PlacementStartResponse)
async def start_placement(
    body: PlacementStartRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> PlacementStartResponse:
    return await start_placement_assessment(
        db,
        user_id=current_user.id,
        topic_unit_ids=body.topic_unit_ids,
    )


@placement_assessment_router.post("/submit", response_model=PlacementSubmitResponse)
async def submit_placement(
    body: PlacementSubmitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> PlacementSubmitResponse:
    result = await submit_placement_assessment(
        db,
        user_id=current_user.id,
        session_id=body.session_id,
        answers=body.answers,
    )
    await db.commit()
    return result


@placement_assessment_router.get("/results", response_model=PlacementResultsResponse)
async def get_placement_results(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> PlacementResultsResponse:
    repo = PlacementAssessmentRepository(db)
    rows = await repo.get_by_user_id(current_user.id)
    decisions = [
        TopicDecision(
            topic_unit_id=row.topic_unit_id,
            score_pct=float(row.score_pct),
            decision=row.decision,
            user_choice=row.user_choice,
        )
        for row in rows
    ]
    return PlacementResultsResponse(results=decisions, has_placement=len(decisions) > 0)


@placement_assessment_router.patch("/topic-decision", response_model=TopicDecision)
async def set_topic_user_choice(
    body: TopicUserChoiceRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> TopicDecision:
    repo = PlacementAssessmentRepository(db)
    row = await repo.get_by_user_and_unit(current_user.id, body.topic_unit_id)
    if row is None or row.decision != "review":
        from src.exceptions import NotFoundError
        raise NotFoundError("No reviewable placement result for this topic.")
    row.user_choice = body.user_choice
    db.add(row)
    await db.commit()
    return TopicDecision(
        topic_unit_id=row.topic_unit_id,
        score_pct=float(row.score_pct),
        decision=row.decision,
        user_choice=row.user_choice,
    )
```

- [ ] **Step 4: Register router in `src/api/app.py`**

Add import after existing router imports:
```python
from src.routers.placement_assessment import placement_assessment_router
```

Add inside the `app` setup (after existing `app.include_router(...)` calls):
```python
app.include_router(placement_assessment_router)
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/test_placement_assessment_router.py -v
```
Expected: PASS (401 responses from auth guard).

- [ ] **Step 6: Commit**

```bash
git add src/routers/placement_assessment.py src/api/app.py tests/test_placement_assessment_router.py
git commit -m "feat: placement assessment router — start/submit/results/topic-decision endpoints"
```

---

## Task 6: Onboarding Backend — goal_ids + OnboardingRequest Extension

**Files:**
- Modify: `src/schemas/auth.py`
- Modify: `src/services/auth_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_onboarding_goal_ids.py
import pytest


def test_onboarding_request_accepts_goal_ids():
    from src.schemas.auth import OnboardingRequest
    from datetime import date

    req = OnboardingRequest(
        goal_ids=["computer_vision", "nlp"],
        known_unit_ids=[],
        desired_section_ids=[],
        selected_course_ids=[],
        available_hours_per_week=5.0,
        target_deadline=date(2027, 1, 1),
        preferred_method="reading",
    )
    assert req.goal_ids == ["computer_vision", "nlp"]


def test_onboarding_request_invalid_goal_id_raises():
    from src.schemas.auth import OnboardingRequest
    from datetime import date
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        OnboardingRequest(
            goal_ids=["invalid_goal"],
            known_unit_ids=[],
            desired_section_ids=[],
            selected_course_ids=[],
            available_hours_per_week=5.0,
            target_deadline=date(2027, 1, 1),
            preferred_method="reading",
        )


def test_goal_ids_map_to_course_ids():
    from src.config.goal_course_map import GOAL_COURSE_MAP
    assert GOAL_COURSE_MAP.get("computer_vision") == "cs231n"
    assert GOAL_COURSE_MAP.get("nlp") == "cs224n"
```

- [ ] **Step 2: Run test to verify fails**

```bash
python -m pytest tests/test_onboarding_goal_ids.py -v
```
Expected: FAIL — `OnboardingRequest` has no `goal_ids` field.

- [ ] **Step 3: Modify `src/schemas/auth.py` — add `goal_ids` to `OnboardingRequest`**

Add after the existing imports:
```python
from src.config.goal_course_map import VALID_GOAL_IDS
```

Inside `OnboardingRequest`, add field:
```python
    goal_ids: list[str] = Field(
        default_factory=list,
        description="Onboarding goal identifiers: 'computer_vision' | 'nlp'",
    )

    @field_validator("goal_ids")
    @classmethod
    def validate_goal_ids(cls, v: list[str]) -> list[str]:
        invalid = [g for g in v if g not in VALID_GOAL_IDS]
        if invalid:
            raise ValueError(f"Unknown goal_ids: {invalid}. Valid: {sorted(VALID_GOAL_IDS)}")
        return v
```

- [ ] **Step 4: Modify `src/services/auth_service.py` — expand `_write_goal_preferences_if_enabled`**

After the existing `import` block at the top, add:
```python
from src.config.goal_course_map import GOAL_COURSE_MAP
```

Replace the `selected_course_ids=data.selected_course_ids or None` line in `_write_goal_preferences_if_enabled` with:

```python
    # Merge explicit selected_course_ids with those derived from goal_ids
    derived_from_goals = [
        GOAL_COURSE_MAP[g] for g in (data.goal_ids or []) if g in GOAL_COURSE_MAP
    ]
    merged_course_ids = list(
        dict.fromkeys((data.selected_course_ids or []) + derived_from_goals)
    )
    await repo.upsert_for_user(
        user_id=user.id,
        goal_weights_json=goal_weights_json,
        selected_course_ids=merged_course_ids or None,
        goal_embedding=None,
        goal_embedding_version=None,
        derived_from_course_set_hash=None,
        notes=notes,
    )
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/test_onboarding_goal_ids.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/schemas/auth.py src/services/auth_service.py tests/test_onboarding_goal_ids.py
git commit -m "feat: extend OnboardingRequest with goal_ids — mapped to selected_course_ids via goal_course_map"
```

---

## Task 7: Recommendation Engine — Phase A/B Split

**Files:**
- Modify: `src/schemas/learning_path.py`
- Modify: `src/services/recommendation_engine.py`

- [ ] **Step 1: Write failing test**

```python
# tests/services/test_recommendation_engine_phases.py
import pytest


def test_path_item_response_has_phase_tag_and_is_locked():
    from src.schemas.learning_path import PathItemResponse
    import uuid
    from src.models.learning import PathAction, PathStatus

    item = PathItemResponse(
        id=uuid.uuid4(),
        learning_unit_id=uuid.uuid4(),
        learning_unit_title="Test Unit",
        action=PathAction.deep_practice,
        estimated_hours=2.0,
        order_index=0,
        week_number=1,
        status=PathStatus.pending,
        phase_tag="A",
        is_locked=False,
    )
    assert item.phase_tag == "A"
    assert item.is_locked is False


def test_path_item_response_defaults_no_lock():
    from src.schemas.learning_path import PathItemResponse
    import uuid
    from src.models.learning import PathAction, PathStatus

    item = PathItemResponse(
        id=uuid.uuid4(),
        learning_unit_id=uuid.uuid4(),
        learning_unit_title="Test Unit",
        action=PathAction.standard_learn,
        estimated_hours=None,
        order_index=0,
        week_number=None,
        status=PathStatus.pending,
    )
    assert item.phase_tag is None
    assert item.is_locked is False
```

- [ ] **Step 2: Run test to verify fails**

```bash
python -m pytest tests/services/test_recommendation_engine_phases.py -v
```
Expected: FAIL — `PathItemResponse` has no `phase_tag` or `is_locked`.

- [ ] **Step 3: Modify `src/schemas/learning_path.py` — extend `PathItemResponse`**

Add two optional fields to `PathItemResponse`:

```python
    phase_tag: str | None = Field(
        default=None,
        description="'A' = remediation phase, 'B' = new learning phase, None = legacy path",
    )
    is_locked: bool = Field(
        default=False,
        description="True when Phase B is locked pending Phase A completion",
    )
```

- [ ] **Step 4: Modify `src/services/recommendation_engine.py` — Phase A/B logic**

Add import at top of file:
```python
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
```

Inside `_generate_canonical_learning_path`, after building `items` list (before `return`), replace the simple loop with Phase A/B classification. Insert after the existing `for order_index, unit in enumerate(units):` loop and before `return GeneratePathResponse(...)`:

```python
    # --- Phase A/B split if placement results exist ---
    placement_repo = PlacementAssessmentRepository(db)
    placement_rows = await placement_repo.get_by_user_id(user.id)
    placement_by_unit: dict[uuid.UUID, str] = {
        row.topic_unit_id: row.decision for row in placement_rows
    }

    if placement_by_unit:
        phase_a_ids = {uid for uid, dec in placement_by_unit.items() if dec != "skip"}
        for item in items:
            if item.learning_unit_id in phase_a_ids:
                item.phase_tag = "A"
            else:
                item.phase_tag = "B"
                item.is_locked = True

        # Sort: Phase A first (in existing prereq order), then Phase B
        phase_a_items = [i for i in items if i.phase_tag == "A"]
        phase_b_items = [i for i in items if i.phase_tag != "A"]
        items = phase_a_items + phase_b_items

        # Re-number order_index
        for idx, item in enumerate(items):
            item.order_index = idx
```

Also add `rationale_log` entries for Phase A nodes after writing `plan_history`. Inside the `for order_index, unit in enumerate(units):` loop, after `audit_repo.add_rationale_log(...)` calls (look for where `rationale_log` is written), add:

```python
        # Write Phase A rationale from placement decision
        placement_decision = placement_by_unit.get(unit.id) if placement_by_unit else None
        if placement_decision and placement_decision != "skip":
            score_row = next(
                (r for r in placement_rows if r.topic_unit_id == unit.id), None
            )
            score_text = f"{float(score_row.score_pct):.0f}%" if score_row else "unknown"
            # rationale_text added to existing audit call or as separate log
```

Note: Inspect the existing `audit_repo` call patterns in `recommendation_engine.py` to add `rationale_text=f"Phase A: placement {placement_decision} (score {score_text})"` to the relevant `add_rationale_log` call.

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/services/test_recommendation_engine_phases.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/schemas/learning_path.py src/services/recommendation_engine.py tests/services/test_recommendation_engine_phases.py
git commit -m "feat: recommendation engine Phase A/B split from placement decisions + rationale log"
```

---

## Task 8: Frontend — Onboarding Store + Schema

**Files:**
- Create: `frontend/stores/onboardingStore.ts`
- Modify: `frontend/lib/onboarding-schema.ts`
- Modify: `frontend/types/index.ts`
- Create: `frontend/lib/placement-assessment-api.ts`

- [ ] **Step 1: Create `frontend/stores/onboardingStore.ts`**

```typescript
// stores/onboardingStore.ts
// Wizard state for the 5-step onboarding flow.
// Kept separate from authStore to avoid coupling placement state to auth lifecycle.
import { create } from "zustand";

export type GoalId = "computer_vision" | "nlp";

export interface PlacementAnswer {
  item_id: string;
  selected_answer: "A" | "B" | "C" | "D";
  topic_unit_id: string;
}

export interface TopicDecision {
  topic_unit_id: string;
  score_pct: number;
  decision: "skip" | "review" | "relearn";
  user_choice?: "skip" | "review" | null;
}

interface OnboardingState {
  // Step 1: goals
  goal_ids: GoalId[];
  setGoalIds: (ids: GoalId[]) => void;

  // Step 2: known topics
  known_unit_ids: string[];
  setKnownUnitIds: (ids: string[]) => void;

  // Step 5: placement
  placement_session_id: string | null;
  placement_answers: PlacementAnswer[];
  placement_decisions: TopicDecision[];

  setPlacementSessionId: (id: string) => void;
  addAnswer: (answer: PlacementAnswer) => void;
  setPlacementDecisions: (decisions: TopicDecision[]) => void;

  // Reset
  reset: () => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  goal_ids: [],
  known_unit_ids: [],
  placement_session_id: null,
  placement_answers: [],
  placement_decisions: [],

  setGoalIds: (ids) => set({ goal_ids: ids }),
  setKnownUnitIds: (ids) => set({ known_unit_ids: ids }),
  setPlacementSessionId: (id) => set({ placement_session_id: id }),
  addAnswer: (answer) =>
    set((s) => ({
      placement_answers: [
        ...s.placement_answers.filter((a) => a.item_id !== answer.item_id),
        answer,
      ],
    })),
  setPlacementDecisions: (decisions) => set({ placement_decisions: decisions }),
  reset: () =>
    set({
      goal_ids: [],
      known_unit_ids: [],
      placement_session_id: null,
      placement_answers: [],
      placement_decisions: [],
    }),
}));
```

- [ ] **Step 2: Modify `frontend/lib/onboarding-schema.ts`**

Replace file content:

```typescript
// lib/onboarding-schema.ts
import { z } from "zod";

const VALID_GOAL_IDS = ["computer_vision", "nlp"] as const;

export const onboardingSchema = z.object({
  goal_ids: z
    .array(z.enum(VALID_GOAL_IDS))
    .min(1, "Chọn ít nhất 1 mục tiêu học"),

  known_unit_ids: z.array(z.string()).default([]),

  desired_section_ids: z.array(z.string()).default([]),

  selected_course_ids: z.array(z.string()).default([]),

  available_hours_per_week: z
    .number({ invalid_type_error: "Phải là số" })
    .min(1, "Ít nhất 1 giờ/tuần")
    .max(20, "Tối đa 20 giờ/tuần"),

  target_deadline: z
    .string()
    .min(1, "Vui lòng chọn ngày")
    .refine((d) => new Date(d) > new Date(), "Deadline phải sau ngày hôm nay"),

  preferred_method: z.enum(["reading", "video"], {
    required_error: "Vui lòng chọn phương pháp học",
  }),
});

export type OnboardingFormData = z.infer<typeof onboardingSchema>;
```

- [ ] **Step 3: Modify `frontend/types/index.ts`** — extend `OnboardingPayload` and add placement types

Replace `OnboardingPayload` interface:
```typescript
export interface OnboardingPayload {
  goal_ids: string[];
  known_unit_ids: string[];
  desired_section_ids: string[];
  selected_course_ids: string[];
  available_hours_per_week: number;
  target_deadline: string;
  preferred_method: "reading" | "video";
}
```

Add new placement types after existing interfaces:
```typescript
export interface PlacementQuestion {
  item_id: string;
  canonical_unit_id: string;
  topic_unit_id: string;
  stem_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
}

export interface PlacementStartResponse {
  session_id: string;
  total_questions: number;
  questions: PlacementQuestion[];
  topic_unit_ids: string[];
}

export interface PlacementDecision {
  topic_unit_id: string;
  score_pct: number;
  decision: "skip" | "review" | "relearn";
  user_choice?: string | null;
}

export interface PlacementSubmitResponse {
  session_id: string;
  topic_decisions: PlacementDecision[];
  skipped_count: number;
  review_count: number;
  relearn_count: number;
}
```

- [ ] **Step 4: Create `frontend/lib/placement-assessment-api.ts`**

```typescript
// lib/placement-assessment-api.ts
import api from "@/lib/api";
import type {
  PlacementStartResponse,
  PlacementSubmitResponse,
} from "@/types";

export interface PlacementAnswerInput {
  item_id: string;
  selected_answer: "A" | "B" | "C" | "D";
  topic_unit_id: string;
}

export const placementApi = {
  start: (topicUnitIds: string[]) =>
    api
      .post<PlacementStartResponse>("/api/placement-assessment/start", {
        topic_unit_ids: topicUnitIds,
      })
      .then((r) => r.data),

  submit: (sessionId: string, answers: PlacementAnswerInput[]) =>
    api
      .post<PlacementSubmitResponse>("/api/placement-assessment/submit", {
        session_id: sessionId,
        answers,
      })
      .then((r) => r.data),

  setUserChoice: (topicUnitId: string, userChoice: "skip" | "review") =>
    api
      .patch("/api/placement-assessment/topic-decision", {
        topic_unit_id: topicUnitId,
        user_choice: userChoice,
      })
      .then((r) => r.data),
};
```

- [ ] **Step 5: Commit**

```bash
git add frontend/stores/onboardingStore.ts frontend/lib/onboarding-schema.ts frontend/types/index.ts frontend/lib/placement-assessment-api.ts
git commit -m "feat(frontend): onboarding store, placement API client, extended types"
```

---

## Task 9: Frontend — Step Components (Goal Selection + Known Topics Filtered)

**Files:**
- Create: `frontend/components/onboarding/StepGoalSelection.tsx`
- Create: `frontend/components/onboarding/StepKnownTopicsFiltered.tsx`

- [ ] **Step 1: Create `frontend/components/onboarding/StepGoalSelection.tsx`**

```tsx
"use client";
// StepGoalSelection.tsx — Step 1: user picks 1 or 2 learning goals.

import { cn } from "@/lib/utils";
import type { GoalId } from "@/stores/onboardingStore";

const GOALS: { id: GoalId; title: string; subtitle: string; courseId: string }[] = [
  {
    id: "computer_vision",
    title: "Computer Vision",
    subtitle: "CS231n — Convolutional Networks, Object Detection, GANs",
    courseId: "cs231n",
  },
  {
    id: "nlp",
    title: "Natural Language Processing",
    subtitle: "CS224n — Transformers, LLMs, Sequence Models",
    courseId: "cs224n",
  },
];

interface Props {
  selectedGoals: GoalId[];
  onToggle: (id: GoalId) => void;
}

export default function StepGoalSelection({ selectedGoals, onToggle }: Props) {
  const selectedSet = new Set(selectedGoals);

  return (
    <div className="space-y-4">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Chọn mục tiêu bạn muốn chinh phục. Có thể chọn cả hai.
      </p>
      {GOALS.map((goal) => {
        const active = selectedSet.has(goal.id);
        return (
          <button
            key={goal.id}
            type="button"
            onClick={() => onToggle(goal.id)}
            className={cn(
              "w-full rounded-xl border-2 p-5 text-left transition-all",
              active
                ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                : "border-neutral-200 dark:border-neutral-700 hover:border-primary-300"
            )}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
                  {goal.title}
                </p>
                <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                  {goal.subtitle}
                </p>
              </div>
              {active && (
                <span className="ml-4 shrink-0 rounded-full bg-primary-500 p-1 text-white">
                  ✓
                </span>
              )}
            </div>
          </button>
        );
      })}
      {selectedGoals.length === 0 && (
        <p className="text-xs text-red-500">Vui lòng chọn ít nhất 1 mục tiêu.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/onboarding/StepKnownTopicsFiltered.tsx`**

```tsx
"use client";
// StepKnownTopicsFiltered.tsx — Step 2: pick known units filtered by selected goals.

import { cn } from "@/lib/utils";
import type { CourseSectionDetail } from "@/types";
import type { GoalId } from "@/stores/onboardingStore";

const GOAL_COURSE_SLUGS: Record<GoalId, string> = {
  computer_vision: "cs231n",
  nlp: "cs224n",
};

interface Props {
  sections: CourseSectionDetail[];
  selectedGoals: GoalId[];
  selectedUnitIds: string[];
  onToggle: (id: string) => void;
}

export default function StepKnownTopicsFiltered({
  sections,
  selectedGoals,
  selectedUnitIds,
  onToggle,
}: Props) {
  const allowedSlugs = new Set(selectedGoals.map((g) => GOAL_COURSE_SLUGS[g]));
  const filtered = sections.filter((s) => allowedSlugs.has(s.course_slug ?? ""));
  const selectedSet = new Set(selectedUnitIds);

  if (filtered.length === 0) {
    return (
      <p className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
        Không tìm thấy nội dung cho mục tiêu đã chọn.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Tick những units bạn đã biết. Bỏ qua nếu bạn mới bắt đầu — hệ thống sẽ đánh giá với{" "}
        <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
          5 câu hỏi/unit
        </span>
        .{" "}
        {selectedUnitIds.length > 0 && (
          <span className="ml-1 font-semibold text-primary-600">
            ({selectedUnitIds.length} unit · {selectedUnitIds.length * 5} câu)
          </span>
        )}
      </p>
      {filtered.map((section) => (
        <div key={section.id}>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide"
              style={{ color: "var(--text-muted)" }}>
            {section.title}
          </h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {section.learning_units.map((unit) => {
              const active = selectedSet.has(unit.id);
              return (
                <button
                  key={unit.id}
                  type="button"
                  onClick={() => onToggle(unit.id)}
                  className={cn(
                    "rounded-lg border px-3 py-2 text-left text-sm transition-all",
                    active
                      ? "border-primary-400 bg-primary-50 dark:bg-primary-900/20 font-medium"
                      : "border-neutral-200 dark:border-neutral-700 hover:border-primary-300"
                  )}
                >
                  {unit.title}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/onboarding/StepGoalSelection.tsx frontend/components/onboarding/StepKnownTopicsFiltered.tsx
git commit -m "feat(frontend): StepGoalSelection and StepKnownTopicsFiltered components"
```

---

## Task 10: Frontend — StepPlacementTest Component

**Files:**
- Create: `frontend/components/onboarding/StepPlacementTest.tsx`

- [ ] **Step 1: Create `frontend/components/onboarding/StepPlacementTest.tsx`**

```tsx
"use client";
// StepPlacementTest.tsx — Step 5: placement assessment test.
// Renders all questions (grouped by topic). User answers before proceeding.

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { PlacementQuestion } from "@/types";

const OPTIONS = ["A", "B", "C", "D"] as const;

interface Props {
  questions: PlacementQuestion[];
  onAnswersChange: (answers: Record<string, "A" | "B" | "C" | "D">) => void;
  answeredCount: number;
}

export default function StepPlacementTest({
  questions,
  onAnswersChange,
  answeredCount,
}: Props) {
  const [answers, setAnswers] = useState<Record<string, "A" | "B" | "C" | "D">>({});

  function handleSelect(itemId: string, choice: "A" | "B" | "C" | "D") {
    const updated = { ...answers, [itemId]: choice };
    setAnswers(updated);
    onAnswersChange(updated);
  }

  const topicGroups = groupByTopic(questions);

  return (
    <div className="space-y-8">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Trả lời {questions.length} câu hỏi để hệ thống đánh giá kiến thức của bạn.
        <span className="ml-2 font-semibold text-primary-600">
          ({answeredCount}/{questions.length} đã trả lời)
        </span>
      </p>
      {topicGroups.map(({ topicUnitId, items }) => (
        <div key={topicUnitId} className="space-y-4">
          {items.map((q, qIdx) => (
            <div key={q.item_id}
                 className="rounded-xl border border-neutral-200 dark:border-neutral-700 p-4">
              <p className="mb-3 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                {qIdx + 1}. {q.stem_text}
              </p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {OPTIONS.map((opt) => {
                  const label = q[`option_${opt.toLowerCase()}` as keyof PlacementQuestion] as string;
                  const chosen = answers[q.item_id] === opt;
                  return (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => handleSelect(q.item_id, opt)}
                      className={cn(
                        "rounded-lg border px-3 py-2 text-left text-sm transition-all",
                        chosen
                          ? "border-primary-500 bg-primary-50 dark:bg-primary-900/30 font-semibold"
                          : "border-neutral-200 dark:border-neutral-700 hover:border-primary-300"
                      )}
                    >
                      <span className="font-bold">{opt}.</span> {label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function groupByTopic(questions: PlacementQuestion[]) {
  const map = new Map<string, PlacementQuestion[]>();
  for (const q of questions) {
    const arr = map.get(q.topic_unit_id) ?? [];
    arr.push(q);
    map.set(q.topic_unit_id, arr);
  }
  return Array.from(map.entries()).map(([topicUnitId, items]) => ({ topicUnitId, items }));
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/onboarding/StepPlacementTest.tsx
git commit -m "feat(frontend): StepPlacementTest component — renders placement questions by topic"
```

---

## Task 11: Frontend — Onboarding Page Redesign (5-step flow)

**Files:**
- Modify: `frontend/app/onboarding/page.tsx`

- [ ] **Step 1: Replace `frontend/app/onboarding/page.tsx`**

```tsx
"use client";
// app/onboarding/page.tsx
// 5-step goal-driven onboarding:
//   0 — Goal selection (multi-select computer_vision / nlp)
//   1 — Known topics (filtered by selected goals, optional)
//   2 — Time & deadline
//   3 — Learning method
//   4 — Placement assessment (only if known_unit_ids selected)

import { Suspense, useCallback, useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Brain, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";

import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import StepGoalSelection from "@/components/onboarding/StepGoalSelection";
import StepKnownTopicsFiltered from "@/components/onboarding/StepKnownTopicsFiltered";
import StepTimeSchedule from "@/components/onboarding/StepTimeSchedule";
import StepLearningMethod from "@/components/onboarding/StepLearningMethod";
import StepPlacementTest from "@/components/onboarding/StepPlacementTest";

import { canonicalSectionApi } from "@/lib/api";
import { placementApi } from "@/lib/placement-assessment-api";
import { onboardingSchema, type OnboardingFormData } from "@/lib/onboarding-schema";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import {
  useOnboardingStore,
  type GoalId,
} from "@/stores/onboardingStore";
import type { CourseSectionDetail, PlacementQuestion } from "@/types";

const GOAL_COURSE_MAP: Record<GoalId, string> = {
  computer_vision: "cs231n",
  nlp: "cs224n",
};

const STEP_LABELS = [
  { title: "Mục tiêu học", subtitle: "Bạn muốn chinh phục gì?" },
  { title: "Kiến thức hiện có", subtitle: "Bạn đã biết gì rồi?" },
  { title: "Thời gian", subtitle: "Lên lịch học phù hợp" },
  { title: "Phương pháp", subtitle: "Cách bạn học tốt nhất" },
  { title: "Kiểm tra đầu vào", subtitle: "Đánh giá nhanh kiến thức" },
] as const;

const STEP_VALIDATION_FIELDS: (keyof OnboardingFormData)[][] = [
  ["goal_ids"],                                          // Step 0
  [],                                                    // Step 1: optional
  ["available_hours_per_week", "target_deadline"],       // Step 2
  ["preferred_method"],                                  // Step 3
  [],                                                    // Step 4: handled separately
];

function OnboardingPageInner() {
  const router = useRouter();
  const { onboard, isLoading, error, clearError } = useAuthStore();
  const { goal_ids, known_unit_ids, setGoalIds, setKnownUnitIds,
          setPlacementSessionId, setPlacementDecisions, reset } = useOnboardingStore();

  const [step, setStep] = useState(0);
  const [sections, setSections] = useState<CourseSectionDetail[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // Placement state (Step 4)
  const [placementQuestions, setPlacementQuestions] = useState<PlacementQuestion[]>([]);
  const [placementAnswers, setPlacementAnswers] = useState<Record<string, "A" | "B" | "C" | "D">>({});
  const [placementSessionId, setLocalSessionId] = useState<string | null>(null);
  const [placementLoading, setPlacementLoading] = useState(false);

  const totalSteps = known_unit_ids.length > 0 ? 5 : 4;

  const form = useForm<OnboardingFormData>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: {
      goal_ids: [],
      known_unit_ids: [],
      desired_section_ids: [],
      selected_course_ids: [],
      available_hours_per_week: 5,
      target_deadline: "",
      preferred_method: undefined,
    },
  });

  const { handleSubmit, setValue, watch, trigger, control, formState: { errors } } = form;
  const watchedGoalIds = watch("goal_ids");

  // Load sections on mount
  useEffect(() => {
    canonicalSectionApi
      .list()
      .then((data) => setSections(Array.isArray(data) ? data : []))
      .catch(() => setSections([]))
      .finally(() => setLoadingData(false));
  }, []);

  // Sync goal_ids → selected_course_ids + onboarding store
  const handleGoalToggle = useCallback(
    (id: GoalId) => {
      const current = watch("goal_ids") as GoalId[];
      const next = current.includes(id)
        ? current.filter((g) => g !== id)
        : [...current, id];
      setValue("goal_ids", next);
      setGoalIds(next);
      const courseIds = next.map((g) => GOAL_COURSE_MAP[g]);
      setValue("selected_course_ids", courseIds);
    },
    [watch, setValue, setGoalIds]
  );

  const handleUnitToggle = useCallback(
    (id: string) => {
      const next = known_unit_ids.includes(id)
        ? known_unit_ids.filter((u) => u !== id)
        : [...known_unit_ids, id];
      setKnownUnitIds(next);
      setValue("known_unit_ids", next);
    },
    [known_unit_ids, setKnownUnitIds, setValue]
  );

  // Step 3 → Step 4: load placement questions if topics selected
  const enterPlacementStep = useCallback(async () => {
    if (known_unit_ids.length === 0) return; // bypass placement
    setPlacementLoading(true);
    try {
      const res = await placementApi.start(known_unit_ids);
      setPlacementQuestions(res.questions);
      setLocalSessionId(res.session_id);
      setPlacementSessionId(res.session_id);
    } finally {
      setPlacementLoading(false);
    }
  }, [known_unit_ids, setPlacementSessionId]);

  const advanceStep = useCallback(async () => {
    const fields = STEP_VALIDATION_FIELDS[step];
    if (fields.length > 0 && !(await trigger(fields as any))) return;

    // Entering placement step
    if (step === 3 && known_unit_ids.length > 0) {
      await enterPlacementStep();
      setStep(4);
      return;
    }
    setStep((s) => Math.min(s + 1, totalSteps - 1));
  }, [step, trigger, known_unit_ids, totalSteps, enterPlacementStep]);

  const onSubmit = handleSubmit(async (data) => {
    // Submit placement answers if on Step 4
    if (step === 4 && placementSessionId && known_unit_ids.length > 0) {
      const answers = Object.entries(placementAnswers).map(([item_id, selected_answer]) => ({
        item_id,
        selected_answer,
        topic_unit_id: placementQuestions.find((q) => q.item_id === item_id)?.topic_unit_id ?? "",
      }));
      const result = await placementApi.submit(placementSessionId, answers);
      setPlacementDecisions(result.topic_decisions as any);
    }

    // Submit onboarding
    await onboard({
      goal_ids: data.goal_ids,
      known_unit_ids: data.known_unit_ids,
      desired_section_ids: data.desired_section_ids,
      selected_course_ids: data.selected_course_ids,
      available_hours_per_week: data.available_hours_per_week,
      target_deadline: data.target_deadline,
      preferred_method: data.preferred_method,
    });
    reset();
    router.push("/dashboard");
  });

  const isLastStep = step === totalSteps - 1;

  if (loadingData) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      {/* Header */}
      <div className="mb-8 flex items-center gap-3">
        <Brain className="h-8 w-8 text-primary-500" />
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            Thiết lập hành trình học
          </h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {STEP_LABELS[step].subtitle}
          </p>
        </div>
      </div>

      {/* Progress */}
      <div className="mb-8 flex gap-2">
        {Array.from({ length: totalSteps }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-1 flex-1 rounded-full transition-all",
              i <= step ? "bg-primary-500" : "bg-neutral-200 dark:bg-neutral-700"
            )}
          />
        ))}
      </div>

      {/* Step label */}
      <h2 className="mb-6 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
        {STEP_LABELS[step].title}
      </h2>

      {/* Step content */}
      <form onSubmit={onSubmit}>
        {step === 0 && (
          <StepGoalSelection
            selectedGoals={watchedGoalIds as GoalId[]}
            onToggle={handleGoalToggle}
          />
        )}
        {step === 1 && (
          <StepKnownTopicsFiltered
            sections={sections}
            selectedGoals={watchedGoalIds as GoalId[]}
            selectedUnitIds={known_unit_ids}
            onToggle={handleUnitToggle}
          />
        )}
        {step === 2 && (
          <StepTimeSchedule register={form.register} errors={errors} control={control} />
        )}
        {step === 3 && (
          <Controller
            name="preferred_method"
            control={control}
            render={({ field }) => (
              <StepLearningMethod value={field.value} onChange={field.onChange} error={errors.preferred_method?.message} />
            )}
          />
        )}
        {step === 4 && (
          placementLoading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : (
            <StepPlacementTest
              questions={placementQuestions}
              onAnswersChange={setPlacementAnswers}
              answeredCount={Object.keys(placementAnswers).length}
            />
          )
        )}

        {error && (
          <p className="mt-4 text-sm text-red-500">{error}</p>
        )}

        {/* Navigation */}
        <div className="mt-8 flex justify-between">
          {step > 0 ? (
            <Button
              type="button"
              variant="ghost"
              onClick={() => { clearError(); setStep((s) => s - 1); }}
            >
              <ChevronLeft className="mr-1 h-4 w-4" /> Quay lại
            </Button>
          ) : (
            <div />
          )}

          {isLastStep ? (
            <Button type="submit" disabled={isLoading}>
              {isLoading ? <LoadingSpinner size="sm" /> : (
                <><Sparkles className="mr-1 h-4 w-4" /> Tạo lộ trình học</>
              )}
            </Button>
          ) : (
            <Button type="button" onClick={advanceStep}>
              Tiếp theo <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><LoadingSpinner /></div>}>
      <OnboardingPageInner />
    </Suspense>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors (or only pre-existing unrelated errors).

- [ ] **Step 3: Verify dev server starts and onboarding page loads**

```bash
cd frontend && npm run dev
```
Open `http://localhost:3000/onboarding` — should show Goal Selection step with CS231n and CS224n cards.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/onboarding/page.tsx
git commit -m "feat(frontend): redesign onboarding to 5-step goal-driven flow with placement assessment"
```

---

## Self-Review: Spec Coverage Check

| Spec Requirement | Task |
|---|---|
| Step 1: Goal selection multi-select (computer_vision / nlp) | Task 9, 11 |
| Step 2: Known topics filtered by goal, group by section | Task 9 |
| Step 3: Time & deadline (unchanged) | Task 11 (reuses StepTimeSchedule) |
| Step 4: Learning method (unchanged) | Task 11 (reuses StepLearningMethod) |
| Step 5: Placement 5 questions/unit — 1 easy / 2 medium / 2 hard | Task 4 (`_bucket_select_5`) |
| Filter by `item_phase_map.phase = 'placement_assessment'` | Task 3, 4 |
| Skip Step 5 if no topics selected | Task 11 (`known_unit_ids.length === 0` bypass) |
| Decision gate: ≥70 skip, 50-70 review, <50 relearn | Task 4 (`_classify_decision`) |
| Phase A: topics with decision ≠ skip | Task 7 |
| Phase B: new units, locked until Phase A mastered | Task 7 (`is_locked=True`) |
| Audit: rationale_log for Phase A nodes | Task 7 |
| Backward-compat: old users keep working | Tasks 6, 7 (existing path unaffected if no placement rows) |
| DB migration additive only | Task 1 (CREATE TABLE, no DROP) |
| goal_ids → selected_course_ids via goal_course_map | Task 2, 6 |
| `placement_assessment_results` table with schema | Task 1, 2 |
| `topic-decision` endpoint for user_choice override | Task 5 |
| async SQLAlchemy throughout | All backend tasks |
| Zustand store for wizard state | Task 8 |
| Only Tailwind + existing components | Tasks 9, 10, 11 |
