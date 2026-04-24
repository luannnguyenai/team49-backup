# Schema v1 Migration Implementation Plan

> **Historical plan:** This document is preserved for implementation history only. It describes a pre-canonical schema using now-dropped runtime tables; use `README.md` and `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md` as the active production contract.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the question-bank backend to Schema v1 forward-compatible design — adding new fields/tables that allow Phase 0 (rule-based) to Phase 1 (IRT + embeddings + FSRS) transition via data-only UPDATE jobs, with zero `ALTER TABLE` or code changes at transition time.

**Architecture:** Extend existing tables (questions, modules, topics, knowledge_components) with nullable/defaulted columns. Add five new companion tables (user_responses, user_mastery, review_schedule, tutor_sessions, embeddings). A Postgres trigger keeps `questions.num_shown` / `num_correct` in sync with `user_responses` inserts. A new idempotent UPSERT seed loader protects production-state fields on re-seed.

**Tech Stack:** PostgreSQL 14+ + pgvector extension, FastAPI, SQLAlchemy 2.0 async (`Mapped[]` style), Alembic, Pydantic v2, pytest-asyncio, pgvector Python package.

---

## ⚠️ Conflicts & Decisions (MUST READ BEFORE EXECUTING)

The spec references paths like `app/models/`, but the actual codebase uses `src/models/`. All paths below use `src/`.

| Spec field | Current state | Resolution |
|---|---|---|
| `version` on Question | ✅ already exists (INT, default 1) | Skip — do NOT add again |
| `created_at`, `updated_at` on Q/M/T | ✅ via TimestampMixin on all three | Skip |
| `irt_b` NULL | `irt_difficulty` REAL nullable exists | ADD `irt_b` as **separate** new column. `effective_b()` reads `irt_b` first, else `difficulty_bucket`. The old `irt_difficulty` is untouched (legacy). |
| `irt_a` NULL | `irt_discrimination` REAL nullable exists | Same: add `irt_a` as separate new column |
| `num_shown` INT | `total_responses` INT exists | ADD `num_shown` + `num_correct` as new columns; keep `total_responses` |
| `review_status` enum | `status` enum(draft\|active\|calibrated\|retired) exists | ADD `review_status` as **new** column; keep old `status` |
| `user_responses` table | `interactions` table (different schema) | ADD new table alongside; trigger fires on `user_responses` only |
| `user_mastery` table | `mastery_scores` table (different PK, topic_id UUID vs topic_slug) | ADD new table alongside |
| `app/seed/loader.py` | Seed loader does not exist; `ingestion.py` handles legacy lectures only | CREATE `src/seed/loader.py` — completely new file |
| `app/services/recommender.py` | `src/services/recommendation_engine.py` is 1472 lines — different scope | CREATE `src/services/recommender.py` — new focused file |
| Seed data at `seed/data/` | JSON files are in `data/` (repo root) | Loader reads from `data/` |
| Module/Topic/KC — no `slug` column | JSON seed uses slugs to link records (topic_slug, module_slug, kc_slugs) | ADD `slug` columns to these three tables — required for idempotent UPSERT. Not in spec, but without slugs the loader cannot link records. |

**Trigger choice:** Using Postgres trigger (option a from spec) for `num_shown` / `num_correct` counters. Reason: trigger fires atomically on every `user_responses` INSERT with no application-layer coordination required, making it correct even under concurrent writes from multiple API workers.

---

## File Map

### Created
| File | Role |
|---|---|
| `alembic/versions/20260418_0001_schema_v1.py` | Single migration — all schema additions |
| `src/models/state.py` | `UserMastery`, `ReviewSchedule` ORM models |
| `src/models/v1_tables.py` | `UserResponse`, `TutorSession` ORM models |
| `src/models/embeddings.py` | `Embedding` ORM model (pgvector) |
| `src/seed/__init__.py` | Package init |
| `src/seed/loader.py` | Idempotent UPSERT seed logic |
| `scripts/__init__.py` | Package init |
| `scripts/seed_all.py` | CLI entry point |
| `src/services/recommender.py` | `effective_b()` + `pick_next_question()` |
| `src/services/irt_calibration.py` | Stub for Phase 1 IRT calibration |
| `src/services/embeddings.py` | Stub for Phase 1 embedding generation |
| `tests/test_seed_v1.py` | Seed schema defaults + idempotency + recommender tests |
| `MIGRATION_V1.md` | Vietnamese ops doc (commands, rollback) |

### Modified
| File | Change |
|---|---|
| `pyproject.toml` | Add `pgvector>=0.3.0` |
| `src/models/content.py` | New enums + new columns on Module, Topic, KC, Question |
| `src/models/__init__.py` | Import new model modules |
| `tests/conftest.py` | Enable vector extension before `create_all` |

---

## Task 1: Add pgvector Dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pgvector to dependencies**

Open `pyproject.toml` and add `pgvector>=0.3.0` after `passlib[bcrypt]`:

```toml
dependencies = [
    "alembic>=1.18.4",
    "asyncpg>=0.31.0",
    "email-validator>=2.3.0",
    "fastapi>=0.135.3",
    "langchain>=1.2.15",
    "langchain-core>=1.2.28",
    "langchain-openai>=1.1.12",
    "langchain-google-genai>=1.0.0",
    "langgraph>=1.1.6",
    "numpy>=2.4.4",
    "openai>=2.31.0",
    "pandas>=3.0.2",
    "passlib[bcrypt]>=1.7.4",
    "pgvector>=0.3.0",
    "psycopg2-binary>=2.9.11",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.13.1",
    "python-dotenv>=1.2.2",
    "python-jose[cryptography]>=3.5.0",
    "python-multipart>=0.0.26",
    "scipy>=1.17.1",
    "sqlalchemy>=2.0.49",
    "sympy>=1.14.0",
    "uvicorn>=0.44.0",
]
```

- [ ] **Step 2: Install the new dependency**

```bash
uv sync
```

Expected: `pgvector` package installed with no errors.

- [ ] **Step 3: Verify pgvector is available in your PostgreSQL server**

```bash
psql -U postgres -d ai_learning -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

Expected: One row with `name=vector`. If the row is missing, install pgvector in your Postgres server before continuing (e.g. `brew install pgvector` on macOS or the OS package for your distro).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pgvector dependency for schema v1 embeddings"
```

---

## Task 2: Write Alembic Migration

**Files:**
- Create: `alembic/versions/20260418_0001_schema_v1.py`

This is the only migration file for all schema v1 additions. It is idempotent via `checkfirst=True` / `IF NOT EXISTS`.

- [ ] **Step 1: Create the migration file**

Create `alembic/versions/20260418_0001_schema_v1.py` with the following content:

```python
"""Schema v1: forward-compatible migration for Phase 0 → Phase 1.

Adds:
  questions  : source, review_status, num_shown, num_correct, irt_a, irt_b,
               calibration_status, content_embedding_id
  modules    : slug, version, status
  topics     : slug, learning_objectives, assessment_config,
               content_embedding_id, version, status
  knowledge_components: slug
  New tables : embeddings, user_responses, user_mastery,
               review_schedule, tutor_sessions
  Trigger    : trg_update_question_counters on user_responses

Revision ID: 20260418_schema_v1
Revises: 20260415_checkpoint_state
Create Date: 2026-04-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "20260418_schema_v1"
down_revision = "20260415_checkpoint_state"
branch_labels = None
depends_on = None

_DEFAULT_ASSESSMENT_CONFIG = (
    '{"num_questions_placement":5,"num_questions_quiz":10,'
    '"difficulty_distribution":{"easy":0.3,"medium":0.5,"hard":0.2},'
    '"min_mastery_to_pass":0.7}'
)


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 0. Enable pgvector extension
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # ------------------------------------------------------------------
    # 1. Create new enum types (checkfirst prevents duplicate-type errors)
    # ------------------------------------------------------------------
    sa.Enum(
        "human", "llm_generated", "imported",
        name="question_source_enum",
    ).create(bind, checkfirst=True)

    sa.Enum(
        "draft", "published", "retired",
        name="review_status_enum",
    ).create(bind, checkfirst=True)

    sa.Enum(
        "uncalibrated", "llm_estimated", "ml_calibrated",
        name="calibration_status_enum",
    ).create(bind, checkfirst=True)

    sa.Enum(
        "draft", "published", "archived",
        name="content_status_enum",
    ).create(bind, checkfirst=True)

    sa.Enum(
        "placement", "quiz", "review", "module_test", "tutor",
        name="response_context_enum",
    ).create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # 2. Add slug columns to modules, topics, knowledge_components
    #    (nullable — existing rows get NULL, seed loader will fill them)
    # ------------------------------------------------------------------
    op.add_column("modules", sa.Column("slug", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_modules_slug", "modules", ["slug"])

    op.add_column("topics", sa.Column("slug", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_topics_slug", "topics", ["slug"])

    op.add_column(
        "knowledge_components",
        sa.Column("slug", sa.String(100), nullable=True),
    )
    op.create_unique_constraint(
        "uq_kc_slug", "knowledge_components", ["slug"]
    )

    # ------------------------------------------------------------------
    # 3. Add v1 columns to modules
    # ------------------------------------------------------------------
    op.add_column(
        "modules",
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default="1"
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "status",
            sa.Enum(
                "draft", "published", "archived",
                name="content_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="published",
        ),
    )

    # ------------------------------------------------------------------
    # 4. Add v1 columns to topics
    # ------------------------------------------------------------------
    op.add_column(
        "topics",
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default="1"
        ),
    )
    op.add_column(
        "topics",
        sa.Column(
            "status",
            sa.Enum(
                "draft", "published", "archived",
                name="content_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="published",
        ),
    )
    op.add_column(
        "topics",
        sa.Column(
            "learning_objectives",
            ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "topics",
        sa.Column(
            "assessment_config",
            JSONB,
            nullable=False,
            server_default=_DEFAULT_ASSESSMENT_CONFIG,
        ),
    )
    op.add_column(
        "topics",
        sa.Column("content_embedding_id", UUID(as_uuid=True), nullable=True),
    )

    # ------------------------------------------------------------------
    # 5. Add v1 columns to questions
    # ------------------------------------------------------------------
    op.add_column(
        "questions",
        sa.Column(
            "source",
            sa.Enum(
                "human", "llm_generated", "imported",
                name="question_source_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="human",
        ),
    )
    op.add_column(
        "questions",
        sa.Column(
            "review_status",
            sa.Enum(
                "draft", "published", "retired",
                name="review_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="published",
        ),
    )
    op.add_column(
        "questions",
        sa.Column(
            "num_shown", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "questions",
        sa.Column(
            "num_correct", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "questions", sa.Column("irt_a", sa.Float(), nullable=True)
    )
    op.add_column(
        "questions", sa.Column("irt_b", sa.Float(), nullable=True)
    )
    op.add_column(
        "questions",
        sa.Column(
            "calibration_status",
            sa.Enum(
                "uncalibrated", "llm_estimated", "ml_calibrated",
                name="calibration_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="uncalibrated",
        ),
    )
    op.add_column(
        "questions",
        sa.Column("content_embedding_id", UUID(as_uuid=True), nullable=True),
    )

    # ------------------------------------------------------------------
    # 6. Create embeddings table (vector column via raw SQL)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(50)  NOT NULL,
            entity_id   UUID         NOT NULL,
            model       VARCHAR(100) NOT NULL,
            vector      vector(384),
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT uq_entity_embedding
                UNIQUE (entity_type, entity_id, model)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_hnsw "
        "ON embeddings USING hnsw (vector vector_cosine_ops) "
        "WITH (m=16, ef_construction=64);"
    )

    # ------------------------------------------------------------------
    # 7. Create user_responses table (append-only, source of truth)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_responses (
            id                    BIGSERIAL   PRIMARY KEY,
            user_id               UUID        NOT NULL
                                  REFERENCES users(id) ON DELETE CASCADE,
            question_id           UUID        NOT NULL
                                  REFERENCES questions(id) ON DELETE RESTRICT,
            session_id            UUID
                                  REFERENCES sessions(id) ON DELETE SET NULL,
            context               response_context_enum NOT NULL,
            selected_answer       CHAR(1),
            is_correct            BOOLEAN     NOT NULL,
            time_taken_ms         INTEGER,
            theta_before          REAL,
            question_irt_b_at_time REAL,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_responses_user_id "
        "ON user_responses(user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_responses_question_id "
        "ON user_responses(question_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_responses_user_created "
        "ON user_responses(user_id, created_at);"
    )

    # ------------------------------------------------------------------
    # 8. Create user_mastery table
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_mastery (
            user_id       UUID         NOT NULL
                          REFERENCES users(id) ON DELETE CASCADE,
            topic_slug    VARCHAR(255) NOT NULL,
            mastery_score REAL         NOT NULL DEFAULT 0.0,
            theta         REAL,
            theta_se      REAL,
            last_updated  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, topic_slug)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_mastery_user_id "
        "ON user_mastery(user_id);"
    )

    # ------------------------------------------------------------------
    # 9. Create review_schedule table (SM-2 Phase 0, FSRS Phase 1)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS review_schedule (
            user_id             UUID    NOT NULL
                                REFERENCES users(id) ON DELETE CASCADE,
            question_id         UUID    NOT NULL
                                REFERENCES questions(id) ON DELETE CASCADE,
            ease_factor         REAL    NOT NULL DEFAULT 2.5,
            interval_days       INTEGER NOT NULL DEFAULT 1,
            repetition_count    INTEGER NOT NULL DEFAULT 0,
            fsrs_stability      REAL,
            fsrs_difficulty     REAL,
            fsrs_retrievability REAL,
            last_rating         INTEGER,
            next_review_at      TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, question_id)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_review_schedule_user_next "
        "ON review_schedule(user_id, next_review_at);"
    )

    # ------------------------------------------------------------------
    # 10. Create tutor_sessions table
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tutor_sessions (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID        NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
            question_id UUID
                        REFERENCES questions(id) ON DELETE SET NULL,
            topic_slug  VARCHAR(255),
            messages    JSONB       NOT NULL DEFAULT '[]',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tutor_sessions_user_id "
        "ON tutor_sessions(user_id);"
    )

    # ------------------------------------------------------------------
    # 11. Create Postgres trigger: update num_shown / num_correct
    #     on every INSERT into user_responses.
    #     Postgres trigger chosen over app-layer listener because it fires
    #     atomically for every writer, regardless of which API worker
    #     inserts the row.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_question_response_counters()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE questions
            SET
                num_shown   = num_shown   + 1,
                num_correct = num_correct + CASE WHEN NEW.is_correct THEN 1 ELSE 0 END
            WHERE id = NEW.question_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE TRIGGER trg_update_question_counters
        AFTER INSERT ON user_responses
        FOR EACH ROW EXECUTE FUNCTION update_question_response_counters();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Drop trigger + function
    op.execute(
        "DROP TRIGGER IF EXISTS trg_update_question_counters ON user_responses;"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS update_question_response_counters();"
    )

    # Drop new tables (reverse FK order)
    op.execute("DROP TABLE IF EXISTS tutor_sessions;")
    op.execute("DROP TABLE IF EXISTS review_schedule;")
    op.execute("DROP TABLE IF EXISTS user_mastery;")
    op.execute("DROP TABLE IF EXISTS user_responses;")
    op.execute("DROP TABLE IF EXISTS embeddings;")

    # Remove columns from questions
    for col in [
        "content_embedding_id",
        "calibration_status",
        "irt_b",
        "irt_a",
        "num_correct",
        "num_shown",
        "review_status",
        "source",
    ]:
        op.drop_column("questions", col)

    # Remove columns from topics
    for col in [
        "content_embedding_id",
        "assessment_config",
        "learning_objectives",
        "status",
        "version",
    ]:
        op.drop_column("topics", col)
    op.drop_constraint("uq_topics_slug", "topics", type_="unique")
    op.drop_column("topics", "slug")

    # Remove columns from modules
    for col in ["status", "version"]:
        op.drop_column("modules", col)
    op.drop_constraint("uq_modules_slug", "modules", type_="unique")
    op.drop_column("modules", "slug")

    # Remove slug from knowledge_components
    op.drop_constraint("uq_kc_slug", "knowledge_components", type_="unique")
    op.drop_column("knowledge_components", "slug")

    # Drop enum types
    for type_name in [
        "response_context_enum",
        "content_status_enum",
        "calibration_status_enum",
        "review_status_enum",
        "question_source_enum",
    ]:
        sa.Enum(name=type_name).drop(bind, checkfirst=True)
```

- [ ] **Step 2: Verify alembic history chain is correct**

```bash
alembic history
```

Expected output (last 4 lines):
```
20260415_checkpoint_state -> 20260418_schema_v1 (head), Schema v1 ...
20260414_add_rating -> 20260415_checkpoint_state, add checkpoint_state ...
<base> -> 20260414_add_rating, add rating to qa_history ...
```

- [ ] **Step 3: Run the migration**

```bash
alembic upgrade head
```

Expected: No errors. All 11 blocks execute successfully.

- [ ] **Step 4: Spot-check DB schema**

```bash
psql -U postgres -d ai_learning -c "\d questions" | grep -E "num_shown|irt_b|review_status|source|calibration"
psql -U postgres -d ai_learning -c "\d user_responses"
psql -U postgres -d ai_learning -c "\d+ embeddings" | grep vector
```

Expected: columns exist with correct types.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/20260418_0001_schema_v1.py
git commit -m "feat: add schema v1 alembic migration (questions/modules/topics extensions + 5 new tables)"
```

---

## Task 3: Update Content SQLAlchemy Models

**Files:**
- Modify: `src/models/content.py`

- [ ] **Step 1: Add new enums and imports at the top of content.py**

After the existing `CorrectAnswer` enum (line 57) and before the `Module` class (line 65), add:

```python
class QuestionSource(enum.StrEnum):
    human = "human"
    llm_generated = "llm_generated"
    imported = "imported"


class ReviewStatus(enum.StrEnum):
    draft = "draft"
    published = "published"
    retired = "retired"


class CalibrationStatus(enum.StrEnum):
    uncalibrated = "uncalibrated"
    llm_estimated = "llm_estimated"
    ml_calibrated = "ml_calibrated"


class ContentStatus(enum.StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"
```

Also add these imports at the top of the file (after `from sqlalchemy import ...`):

```python
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
```

(Replace `from sqlalchemy.dialects.postgresql import JSON, UUID` with the above.)

- [ ] **Step 2: Add slug + version + status columns to Module (after line 77 `prerequisite_module_ids`)**

```python
    slug: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=False
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status_enum", create_type=False),
        nullable=False,
        default=ContentStatus.published,
        server_default="published",
    )
```

- [ ] **Step 3: Add slug + v1 columns to Topic (after line 115 `video_url`)**

```python
    slug: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=False
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status_enum", create_type=False),
        nullable=False,
        default=ContentStatus.published,
        server_default="published",
    )
    learning_objectives: Mapped[list[str]] = mapped_column(
        ARRAY(Text()), nullable=False, default=list, server_default="{}"
    )
    assessment_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=(
            '{"num_questions_placement":5,"num_questions_quiz":10,'
            '"difficulty_distribution":{"easy":0.3,"medium":0.5,"hard":0.2},'
            '"min_mastery_to_pass":0.7}'
        ),
    )
    content_embedding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
```

- [ ] **Step 4: Add slug column to KnowledgeComponent (after line 147 `description`)**

```python
    slug: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=False
    )
```

- [ ] **Step 5: Add v1 columns to Question (after line 236 `total_responses`)**

```python
    # Schema v1 additions
    source: Mapped[QuestionSource] = mapped_column(
        Enum(QuestionSource, name="question_source_enum", create_type=False),
        nullable=False,
        default=QuestionSource.human,
        server_default="human",
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status_enum", create_type=False),
        nullable=False,
        default=ReviewStatus.published,
        server_default="published",
    )
    num_shown: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    num_correct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    irt_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    irt_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibration_status: Mapped[CalibrationStatus] = mapped_column(
        Enum(CalibrationStatus, name="calibration_status_enum", create_type=False),
        nullable=False,
        default=CalibrationStatus.uncalibrated,
        server_default="uncalibrated",
    )
    content_embedding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
```

- [ ] **Step 6: Update __all__ exports in content.py to include new enums**

Add to the module-level (or just confirm the new enums are importable). Since SQLAlchemy models are used by name, no explicit `__all__` update needed — the new classes are automatically importable.

- [ ] **Step 7: Verify content.py imports correctly**

```bash
python -c "from src.models.content import Module, Topic, KnowledgeComponent, Question, QuestionSource, ReviewStatus, CalibrationStatus, ContentStatus; print('OK')"
```

Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add src/models/content.py
git commit -m "feat: add schema v1 fields to Module, Topic, KC, Question ORM models"
```

---

## Task 4: Create New SQLAlchemy Model Files

**Files:**
- Create: `src/models/state.py`
- Create: `src/models/v1_tables.py`
- Create: `src/models/embeddings.py`

- [ ] **Step 1: Create `src/models/state.py`**

```python
"""
models/state.py
---------------
Schema v1 state tracking: UserMastery, ReviewSchedule.
"""

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class UserMastery(Base):
    """IRT-based mastery per (user, topic_slug). PK: (user_id, topic_slug).

    Coexists with legacy mastery_scores (which uses topic_id UUID + KC grain).
    This table uses topic_slug for simpler IRT-based Phase 1 tracking.
    """

    __tablename__ = "user_mastery"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic_slug: Mapped[str] = mapped_column(String(255), primary_key=True)
    mastery_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0.0"
    )
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    theta_se: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_user_mastery_user_id", "user_id"),)


class ReviewSchedule(Base):
    """SM-2 spaced repetition schedule. PK: (user_id, question_id).

    Phase 0: ease_factor, interval_days, repetition_count.
    Phase 1: fsrs_* columns will be populated by FSRS batch job.
    """

    __tablename__ = "review_schedule"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ease_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5, server_default="2.5"
    )
    interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    repetition_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    fsrs_stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    fsrs_difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    fsrs_retrievability: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_review_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_review_schedule_user_next", "user_id", "next_review_at"),
    )
```

- [ ] **Step 2: Create `src/models/v1_tables.py`**

```python
"""
models/v1_tables.py
-------------------
Schema v1 new interaction tables: UserResponse (append-only), TutorSession.

UserResponse is the SOURCE OF TRUTH for IRT calibration — coexists with
the legacy `interactions` table (which the existing API still writes to).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Enum, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ResponseContext(enum.StrEnum):
    placement = "placement"
    quiz = "quiz"
    review = "review"
    module_test = "module_test"
    tutor = "tutor"


class UserResponse(Base):
    """Append-only question-response event.

    Written by any session context (quiz, assessment, review, tutor).
    The Postgres trigger trg_update_question_counters updates
    questions.num_shown / num_correct on every INSERT here.
    """

    __tablename__ = "user_responses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    context: Mapped[ResponseContext] = mapped_column(
        Enum(ResponseContext, name="response_context_enum", create_type=False),
        nullable=False,
    )
    selected_answer: Mapped[str | None] = mapped_column(String(1), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_taken_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    theta_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    question_irt_b_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_user_responses_user_id", "user_id"),
        Index("ix_user_responses_question_id", "question_id"),
        Index("ix_user_responses_user_created", "user_id", "created_at"),
    )


class TutorSession(Base):
    """Multi-turn LLM tutor conversation, linked to a question or topic."""

    __tablename__ = "tutor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    topic_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    messages: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="'[]'"
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_tutor_sessions_user_id", "user_id"),)
```

- [ ] **Step 3: Create `src/models/embeddings.py`**

```python
"""
models/embeddings.py
--------------------
Schema v1: vector embedding storage (Phase 1).
Requires pgvector PostgreSQL extension + pgvector Python package.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Embedding(Base):
    """Dense vector embedding for a content entity (question or topic).

    entity_type: 'question' | 'topic'
    entity_id:   UUID of the corresponding row
    model:       embedding model identifier, e.g. 'all-MiniLM-L6-v2'
    vector:      384-dimensional float vector (pgvector)
    """

    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    vector: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "model", name="uq_entity_embedding"
        ),
    )
```

- [ ] **Step 4: Verify all three files import cleanly**

```bash
python -c "from src.models.state import UserMastery, ReviewSchedule; from src.models.v1_tables import UserResponse, TutorSession, ResponseContext; from src.models.embeddings import Embedding; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/models/state.py src/models/v1_tables.py src/models/embeddings.py
git commit -m "feat: add schema v1 ORM models (UserMastery, ReviewSchedule, UserResponse, TutorSession, Embedding)"
```

---

## Task 5: Register New Models and Update Test Fixtures

**Files:**
- Modify: `src/models/__init__.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update `src/models/__init__.py` to import new models**

Replace the file content with:

```python
"""
models/__init__.py
------------------
Re-export every model so that Alembic env.py only needs to import this
package to discover all tables.
"""

from src.models.base import Base  # noqa: F401
from src.models.content import KnowledgeComponent, Module, Question, Topic  # noqa: F401
from src.models.embeddings import Embedding  # noqa: F401
from src.models.learning import (  # noqa: F401
    Interaction,
    LearningPath,
    MasteryScore,
    Session,
)
from src.models.state import ReviewSchedule, UserMastery  # noqa: F401
from src.models.v1_tables import ResponseContext, TutorSession, UserResponse  # noqa: F401

# Original lecture models
from src.models.store import Chapter, Lecture, QAHistory, TranscriptLine  # noqa: F401

# User
from src.models.user import User  # noqa: F401

__all__ = [
    "Base",
    # Lecture models
    "Lecture",
    "Chapter",
    "TranscriptLine",
    "QAHistory",
    # User
    "User",
    # Content
    "Module",
    "Topic",
    "KnowledgeComponent",
    "Question",
    # Learning (legacy)
    "Session",
    "Interaction",
    "MasteryScore",
    "LearningPath",
    # Schema v1 — state
    "UserMastery",
    "ReviewSchedule",
    # Schema v1 — interaction
    "UserResponse",
    "TutorSession",
    "ResponseContext",
    # Schema v1 — embeddings
    "Embedding",
]
```

- [ ] **Step 2: Update `tests/conftest.py` to enable pgvector before create_all**

Add `from sqlalchemy import text` to the imports and update the `test_engine` fixture:

```python
from sqlalchemy import text

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create all tables in the test DB, yield the engine, drop tables after."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
pytest tests/test_health.py -v
```

Expected: All existing tests pass (no regression from model changes).

- [ ] **Step 4: Commit**

```bash
git add src/models/__init__.py tests/conftest.py
git commit -m "feat: register schema v1 models; enable pgvector in test fixtures"
```

---

## Task 6: Write Schema Default Tests (TDD — write tests FIRST)

**Files:**
- Create: `tests/test_seed_v1.py`

- [ ] **Step 1: Create the test file with schema default tests**

```python
"""
tests/test_seed_v1.py
---------------------
Tests for Schema v1:
  - Old JSON (no v1 fields) parses with correct Pydantic defaults.
  - UPSERT is idempotent: no duplicates, no reset of protected fields.
  - Recommender works in Phase 0 (all irt_b=None) and mixed mode.
"""

import pytest

# ---------------------------------------------------------------------------
# Schema default tests — no DB required
# ---------------------------------------------------------------------------


def test_question_seed_schema_old_json_gets_defaults():
    """Old question JSON without v1 fields → all v1 defaults are applied."""
    from src.schemas.v1_seed import QuestionSeedSchema

    old_data = {
        "item_id": "ITEM-NLP-00001",
        "topic_slug": "nlp_history",
        "module_slug": "cs224n_nlp",
        "bloom_level": "remember",
        "difficulty_bucket": "easy",
        "stem_text": "Test question",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_answer": "B",
    }
    q = QuestionSeedSchema(**old_data)

    assert q.source == "human"
    assert q.review_status == "published"
    assert q.calibration_status == "uncalibrated"
    assert q.version == 1
    assert q.kc_slugs == []
    assert q.usage_context is None
    assert q.explanation_text is None


def test_topic_seed_schema_old_json_gets_defaults():
    """Old topic JSON without v1 fields → assessment_config default is correct."""
    from src.schemas.v1_seed import TopicSeedSchema

    old_data = {
        "slug": "nlp_history",
        "module_slug": "cs224n_nlp",
        "name": "History of NLP",
        "order_index": 1,
    }
    t = TopicSeedSchema(**old_data)

    assert t.learning_objectives == []
    assert t.version == 1
    assert t.status == "published"
    assert t.assessment_config["num_questions_quiz"] == 10
    assert t.assessment_config["min_mastery_to_pass"] == 0.7
    assert t.assessment_config["difficulty_distribution"]["easy"] == 0.3
    assert t.knowledge_components == []


def test_module_seed_schema_old_json_gets_defaults():
    """Old module JSON without v1 fields → version=1, status=published."""
    from src.schemas.v1_seed import ModuleSeedSchema

    old_data = {
        "slug": "cs224n_nlp",
        "name": "CS224N NLP",
        "order_index": 1,
    }
    m = ModuleSeedSchema(**old_data)

    assert m.version == 1
    assert m.status == "published"
    assert m.prerequisite_module_slugs == []


def test_question_seed_schema_ignores_unknown_fields():
    """Extra fields in JSON are silently ignored (model_config extra='ignore')."""
    from src.schemas.v1_seed import QuestionSeedSchema

    data = {
        "item_id": "ITEM-NLP-00001",
        "topic_slug": "nlp_history",
        "module_slug": "cs224n_nlp",
        "bloom_level": "remember",
        "difficulty_bucket": "easy",
        "stem_text": "Test question",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_answer": "B",
        "unexpected_future_field": "ignored",
    }
    q = QuestionSeedSchema(**data)
    assert q.item_id == "ITEM-NLP-00001"


# ---------------------------------------------------------------------------
# Recommender tests — no DB required (mock Question objects)
# ---------------------------------------------------------------------------


class _MockQ:
    def __init__(self, irt_a, irt_b, difficulty_bucket):
        self.irt_a = irt_a
        self.irt_b = irt_b
        self.difficulty_bucket = difficulty_bucket


def test_effective_b_phase0_uses_difficulty_bucket():
    """Phase 0: irt_b=None → fallback to difficulty_bucket mapping."""
    from src.services.recommender import effective_b

    assert effective_b(_MockQ(None, None, "easy")) == -1.0
    assert effective_b(_MockQ(None, None, "medium")) == 0.0
    assert effective_b(_MockQ(None, None, "hard")) == 1.0


def test_effective_b_phase1_uses_irt_b():
    """Phase 1: irt_b set → uses irt_b regardless of difficulty_bucket."""
    from src.services.recommender import effective_b

    q = _MockQ(1.2, -0.5, "hard")
    assert effective_b(q) == -0.5


def test_pick_next_question_phase0_all_null():
    """Phase 0: picks question with b closest to user theta (maximises Fisher info)."""
    from src.services.recommender import pick_next_question

    user_theta = 0.1
    candidates = [
        _MockQ(None, None, "easy"),    # b = -1.0
        _MockQ(None, None, "medium"),  # b =  0.0  ← closest to 0.1
        _MockQ(None, None, "hard"),    # b =  1.0
    ]
    chosen = pick_next_question(user_theta, candidates)
    assert chosen.difficulty_bucket == "medium"


def test_pick_next_question_mixed_mode():
    """Mixed mode: some irt_b set, some None — effective_b handles transparently."""
    from src.services.recommender import pick_next_question

    user_theta = -0.3
    candidates = [
        _MockQ(1.0, None, "easy"),     # effective_b = -1.0
        _MockQ(1.0, -0.4, "medium"),   # effective_b = -0.4 ← closest to -0.3
        _MockQ(1.0, 1.5, "hard"),      # effective_b =  1.5
    ]
    chosen = pick_next_question(user_theta, candidates)
    assert chosen.irt_b == -0.4


def test_pick_next_question_empty_raises():
    """Empty candidate list raises ValueError."""
    from src.services.recommender import pick_next_question

    with pytest.raises(ValueError, match="non-empty"):
        pick_next_question(0.0, [])


# ---------------------------------------------------------------------------
# DB tests — require db_session fixture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session):
    """Seeding twice returns same counts and creates no duplicates."""
    from src.seed.loader import seed_all

    r1 = await seed_all(db_session)
    r2 = await seed_all(db_session)

    assert r1["questions"] > 0
    assert r1["questions"] == r2["questions"]
    assert r1["modules"] == r2["modules"]
    assert r1["topics"] == r2["topics"]


@pytest.mark.asyncio
async def test_seed_preserves_protected_fields(db_session):
    """Re-seeding does NOT reset num_shown / num_correct when > 0."""
    from sqlalchemy import select, update

    from src.models.content import Question
    from src.seed.loader import seed_all

    await seed_all(db_session)
    await db_session.flush()

    # Simulate production state: question has been shown 10 times, 7 correct.
    await db_session.execute(
        update(Question)
        .where(Question.item_id == "ITEM-NLP-00001")
        .values(num_shown=10, num_correct=7)
    )
    await db_session.flush()

    # Re-seed
    await seed_all(db_session)
    await db_session.flush()

    result = await db_session.execute(
        select(Question).where(Question.item_id == "ITEM-NLP-00001")
    )
    q = result.scalar_one()
    assert q.num_shown == 10, f"Expected 10, got {q.num_shown}"
    assert q.num_correct == 7, f"Expected 7, got {q.num_correct}"
```

- [ ] **Step 2: Run the tests to verify they fail (as expected before implementation)**

```bash
pytest tests/test_seed_v1.py -v 2>&1 | head -40
```

Expected: Tests that import `src.schemas.v1_seed` and `src.services.recommender` will fail with `ModuleNotFoundError`. DB tests will also fail. This is correct — we write code next.

---

## Task 7: Create Seed Schemas

**Files:**
- Create: `src/schemas/v1_seed.py`

- [ ] **Step 1: Create `src/schemas/v1_seed.py`**

```python
"""
schemas/v1_seed.py
------------------
Pydantic v2 schemas for loading JSON seed files (modules.json, topics.json,
question_bank.json) into the database.

Key design:
  - Accepts slugs instead of UUIDs (the JSON uses slugs; loader resolves them).
  - All v1 fields have defaults so old JSON (without those fields) parses cleanly.
  - extra='ignore' so future JSON fields don't break the loader.
"""

from pydantic import BaseModel, ConfigDict, Field


class KCSeedSchema(BaseModel):
    """One knowledge component nested inside a topic entry."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    name: str
    description: str | None = None


class TopicSeedSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    module_slug: str
    name: str
    description: str | None = None
    order_index: int
    prerequisite_topic_slugs: list[str] = []
    estimated_hours_beginner: float | None = None
    estimated_hours_intermediate: float | None = None
    estimated_hours_review: float | None = None
    content_markdown: str | None = None
    video_url: str | None = None
    knowledge_components: list[KCSeedSchema] = []
    # v1 additions with defaults
    learning_objectives: list[str] = []
    assessment_config: dict = Field(
        default_factory=lambda: {
            "num_questions_placement": 5,
            "num_questions_quiz": 10,
            "difficulty_distribution": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
            "min_mastery_to_pass": 0.7,
        }
    )
    version: int = 1
    status: str = "published"


class ModuleSeedSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    name: str
    description: str | None = None
    order_index: int
    prerequisite_module_slugs: list[str] = []
    # v1 additions with defaults
    version: int = 1
    status: str = "published"


class QuestionSeedSchema(BaseModel):
    """One question from question_bank.json.

    The v1 protected fields (num_shown, num_correct, irt_a, irt_b,
    calibration_status, content_embedding_id) are NOT in this schema —
    the loader never passes them to the INSERT, so they can never be
    accidentally overwritten via ON CONFLICT DO UPDATE.
    """

    model_config = ConfigDict(extra="ignore")

    item_id: str
    topic_slug: str
    module_slug: str
    bloom_level: str
    difficulty_bucket: str
    stem_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    kc_slugs: list[str] = []
    usage_context: list[str] | None = None
    distractor_a_rationale: str | None = None
    distractor_b_rationale: str | None = None
    distractor_c_rationale: str | None = None
    distractor_d_rationale: str | None = None
    misconception_a_id: str | None = None
    misconception_b_id: str | None = None
    misconception_c_id: str | None = None
    misconception_d_id: str | None = None
    explanation_text: str | None = None
    time_expected_seconds: int | None = None
    # v1 additions with defaults (content-level, not production-state)
    source: str = "human"
    review_status: str = "published"
    version: int = 1
```

- [ ] **Step 2: Run schema default tests to verify they pass**

```bash
pytest tests/test_seed_v1.py::test_question_seed_schema_old_json_gets_defaults \
       tests/test_seed_v1.py::test_topic_seed_schema_old_json_gets_defaults \
       tests/test_seed_v1.py::test_module_seed_schema_old_json_gets_defaults \
       tests/test_seed_v1.py::test_question_seed_schema_ignores_unknown_fields -v
```

Expected: 4 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/schemas/v1_seed.py tests/test_seed_v1.py
git commit -m "feat: add v1_seed Pydantic schemas; TDD tests for schema defaults"
```

---

## Task 8: Create Seed Loader

**Files:**
- Create: `src/seed/__init__.py`
- Create: `src/seed/loader.py`

- [ ] **Step 1: Create `src/seed/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Create `src/seed/loader.py`**

```python
"""
seed/loader.py
--------------
Idempotent UPSERT loader: JSON → PostgreSQL via ON CONFLICT DO UPDATE.

Protected fields — never overwritten on re-seed because they represent
production state (response counters, calibrated IRT params, embedding refs):
    questions: num_shown, num_correct, irt_a, irt_b,
               calibration_status, content_embedding_id

Load order (FK dependencies):
    modules → topics + knowledge_components → questions

Usage:
    from src.seed.loader import seed_all
    result = await seed_all(session)            # all courses
    result = await seed_all(session, "cs224n_nlp")  # filter by module slug
    # Caller must call session.commit() or session.flush() as needed.
"""

import json
import uuid
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.content import KnowledgeComponent, Module, Question, Topic
from src.schemas.v1_seed import (
    KCSeedSchema,
    ModuleSeedSchema,
    QuestionSeedSchema,
    TopicSeedSchema,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Fields on questions that must never be overwritten by re-seeding.
_QUESTION_PROTECTED = frozenset(
    {
        "num_shown",
        "num_correct",
        "irt_a",
        "irt_b",
        "calibration_status",
        "content_embedding_id",
    }
)


async def seed_modules(
    session: AsyncSession,
    course: str | None = None,
) -> dict[str, uuid.UUID]:
    """Upsert modules from data/modules.json.

    Returns:
        slug → UUID map for use in subsequent seed steps.
    """
    raw: list[dict] = json.loads((DATA_DIR / "modules.json").read_text())
    schemas = [ModuleSeedSchema(**m) for m in raw]
    if course:
        schemas = [s for s in schemas if course in s.slug]

    slug_to_id: dict[str, uuid.UUID] = {}
    for s in schemas:
        row_id = uuid.uuid4()
        values = {
            "id": row_id,
            "slug": s.slug,
            "name": s.name,
            "description": s.description,
            "order_index": s.order_index,
            "prerequisite_module_ids": None,
            "version": s.version,
            "status": s.status,
        }
        stmt = pg_insert(Module).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_modules_slug",
            set_={k: stmt.excluded[k] for k in values if k not in {"id", "created_at"}},
        ).returning(Module.id)
        result = await session.execute(stmt)
        slug_to_id[s.slug] = result.scalar_one()

    await session.flush()
    return slug_to_id


async def seed_topics(
    session: AsyncSession,
    module_slug_to_id: dict[str, uuid.UUID],
    course: str | None = None,
) -> tuple[dict[str, uuid.UUID], dict[str, uuid.UUID]]:
    """Upsert topics + knowledge_components from data/topics.json.

    Returns:
        (topic_slug → UUID, kc_slug → UUID)
    """
    raw: list[dict] = json.loads((DATA_DIR / "topics.json").read_text())
    schemas = [TopicSeedSchema(**t) for t in raw]
    if course:
        schemas = [s for s in schemas if course in s.module_slug]

    topic_slug_to_id: dict[str, uuid.UUID] = {}
    kc_slug_to_id: dict[str, uuid.UUID] = {}

    for s in schemas:
        module_id = module_slug_to_id.get(s.module_slug)
        if module_id is None:
            continue

        topic_id = uuid.uuid4()
        t_values = {
            "id": topic_id,
            "slug": s.slug,
            "module_id": module_id,
            "name": s.name,
            "description": s.description,
            "order_index": s.order_index,
            "prerequisite_topic_ids": None,
            "estimated_hours_beginner": s.estimated_hours_beginner,
            "estimated_hours_intermediate": s.estimated_hours_intermediate,
            "estimated_hours_review": s.estimated_hours_review,
            "content_markdown": s.content_markdown,
            "video_url": s.video_url,
            "learning_objectives": s.learning_objectives,
            "assessment_config": s.assessment_config,
            "version": s.version,
            "status": s.status,
        }
        t_stmt = pg_insert(Topic).values(t_values)
        t_stmt = t_stmt.on_conflict_do_update(
            constraint="uq_topics_slug",
            set_={k: t_stmt.excluded[k] for k in t_values if k not in {"id", "created_at"}},
        ).returning(Topic.id)
        t_result = await session.execute(t_stmt)
        resolved_topic_id: uuid.UUID = t_result.scalar_one()
        topic_slug_to_id[s.slug] = resolved_topic_id

        for kc in s.knowledge_components:
            kc_id = uuid.uuid4()
            kc_values = {
                "id": kc_id,
                "slug": kc.slug,
                "topic_id": resolved_topic_id,
                "name": kc.name,
                "description": kc.description,
            }
            kc_stmt = pg_insert(KnowledgeComponent).values(kc_values)
            kc_stmt = kc_stmt.on_conflict_do_update(
                constraint="uq_kc_slug",
                set_={k: kc_stmt.excluded[k] for k in kc_values if k not in {"id", "created_at"}},
            ).returning(KnowledgeComponent.id)
            kc_result = await session.execute(kc_stmt)
            kc_slug_to_id[kc.slug] = kc_result.scalar_one()

    await session.flush()
    return topic_slug_to_id, kc_slug_to_id


async def seed_questions(
    session: AsyncSession,
    topic_slug_to_id: dict[str, uuid.UUID],
    module_slug_to_id: dict[str, uuid.UUID],
    kc_slug_to_id: dict[str, uuid.UUID],
    course: str | None = None,
) -> int:
    """Upsert questions from data/question_bank.json.

    Protected fields (num_shown, num_correct, irt_a, irt_b,
    calibration_status, content_embedding_id) are excluded from the
    ON CONFLICT DO UPDATE set, preserving production state on re-seed.

    Returns:
        Number of questions processed.
    """
    raw: list[dict] = json.loads((DATA_DIR / "question_bank.json").read_text())
    schemas = [QuestionSeedSchema(**q) for q in raw]
    if course:
        schemas = [s for s in schemas if course in s.module_slug]

    count = 0
    for s in schemas:
        topic_id = topic_slug_to_id.get(s.topic_slug)
        module_id = module_slug_to_id.get(s.module_slug)
        if topic_id is None or module_id is None:
            continue

        kc_ids = [
            str(kc_slug_to_id[slug])
            for slug in s.kc_slugs
            if slug in kc_slug_to_id
        ] or None

        values = {
            "id": uuid.uuid4(),
            "item_id": s.item_id,
            "topic_id": topic_id,
            "module_id": module_id,
            "bloom_level": s.bloom_level,
            "difficulty_bucket": s.difficulty_bucket,
            "stem_text": s.stem_text,
            "option_a": s.option_a,
            "option_b": s.option_b,
            "option_c": s.option_c,
            "option_d": s.option_d,
            "correct_answer": s.correct_answer,
            "kc_ids": kc_ids,
            "usage_context": s.usage_context,
            "distractor_a_rationale": s.distractor_a_rationale,
            "distractor_b_rationale": s.distractor_b_rationale,
            "distractor_c_rationale": s.distractor_c_rationale,
            "distractor_d_rationale": s.distractor_d_rationale,
            "misconception_a_id": s.misconception_a_id,
            "misconception_b_id": s.misconception_b_id,
            "misconception_c_id": s.misconception_c_id,
            "misconception_d_id": s.misconception_d_id,
            "explanation_text": s.explanation_text,
            "time_expected_seconds": s.time_expected_seconds,
            "source": s.source,
            "review_status": s.review_status,
            "version": s.version,
            "status": "active",
        }

        insert_stmt = pg_insert(Question).values(values)
        update_cols = {
            k: insert_stmt.excluded[k]
            for k in values
            if k not in _QUESTION_PROTECTED and k != "id"
        }
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["item_id"],
            set_=update_cols,
        )
        await session.execute(insert_stmt)
        count += 1

    await session.flush()
    return count


async def seed_all(
    session: AsyncSession,
    course: str | None = None,
) -> dict[str, int]:
    """Upsert all curriculum data in dependency order.

    Does NOT commit — the caller must call session.commit() when ready.

    Args:
        session: Async SQLAlchemy session.
        course:  Optional module slug prefix to filter (e.g. 'cs224n_nlp').
                 None means seed everything.

    Returns:
        {'modules': N, 'topics': N, 'questions': N}
    """
    module_map = await seed_modules(session, course)
    topic_map, kc_map = await seed_topics(session, module_map, course)
    q_count = await seed_questions(session, topic_map, module_map, kc_map, course)
    return {
        "modules": len(module_map),
        "topics": len(topic_map),
        "questions": q_count,
    }
```

- [ ] **Step 3: Run all seed tests**

```bash
pytest tests/test_seed_v1.py -v -k "seed"
```

Expected: `test_seed_is_idempotent` and `test_seed_preserves_protected_fields` PASS.

- [ ] **Step 4: Commit**

```bash
git add src/seed/__init__.py src/seed/loader.py
git commit -m "feat: add idempotent seed loader with protected-field UPSERT logic"
```

---

## Task 9: Create CLI Entry Point

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/seed_all.py`

- [ ] **Step 1: Create `scripts/__init__.py`** (empty file)

```python
```

- [ ] **Step 2: Create `scripts/seed_all.py`**

```python
"""CLI entry point for curriculum seeding.

Usage:
    python -m scripts.seed_all
    python -m scripts.seed_all --course cs224n_nlp
"""

import asyncio
import argparse

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings
from src.seed.loader import seed_all


async def main(course: str | None = None) -> None:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await seed_all(session, course=course)
        await session.commit()
    await engine.dispose()
    print(f"Seeded: modules={result['modules']}, topics={result['topics']}, questions={result['questions']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed curriculum data into the database.")
    parser.add_argument(
        "--course",
        default=None,
        help="Filter by module slug (e.g. cs224n_nlp). Omit to seed all.",
    )
    args = parser.parse_args()
    asyncio.run(main(course=args.course))
```

- [ ] **Step 3: Run seed_all once and verify**

```bash
python -m scripts.seed_all
```

Expected output (counts vary by your data):
```
Seeded: modules=1, topics=6, questions=104
```

- [ ] **Step 4: Run seed_all again (idempotency check)**

```bash
python -m scripts.seed_all
```

Expected: Same output, no duplicates, no errors.

- [ ] **Step 5: Verify counters are NOT reset**

```bash
psql -U postgres -d ai_learning -c "SELECT item_id, num_shown, num_correct FROM questions LIMIT 3;"
```

Expected: `num_shown=0`, `num_correct=0` for all (trigger only fires on `user_responses` INSERTs, which haven't happened yet).

- [ ] **Step 6: Commit**

```bash
git add scripts/__init__.py scripts/seed_all.py
git commit -m "feat: add scripts/seed_all.py CLI entry point"
```

---

## Task 10: Create Recommender Service

**Files:**
- Create: `src/services/recommender.py`

- [ ] **Step 1: Create `src/services/recommender.py`**

```python
"""
services/recommender.py
-----------------------
IRT-based question selection for adaptive learning.

Phase 0: irt_b=None → effective_b() falls back to difficulty_bucket mapping.
Phase 1: irt_b is filled by the calibration batch job — no code change needed.

The Fisher information criterion selects the question that provides the most
information about the user's ability at their current theta estimate.
"""

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.content import Question

# Maps difficulty_bucket to an IRT b parameter approximation used in Phase 0.
DIFFICULTY_TO_B: dict[str, float] = {
    "easy": -1.0,
    "medium": 0.0,
    "hard": 1.0,
}


def effective_b(question: "Question") -> float:
    """Return the best available difficulty parameter for a question.

    Phase 0 (irt_b=None): returns the b-proxy derived from difficulty_bucket.
    Phase 1 (irt_b set):   returns irt_b directly.

    Note: irt_b is a separate column from the legacy irt_difficulty — the legacy
    column holds the seed-time estimate, irt_b holds the ML-calibrated value.
    """
    if question.irt_b is not None:
        return question.irt_b
    return DIFFICULTY_TO_B.get(str(question.difficulty_bucket), 0.0)


def pick_next_question(user_theta: float, candidates: list["Question"]) -> "Question":
    """Select the question maximising Fisher information at user_theta.

    Works transparently across Phase 0 (all irt_b=None), Phase 1 (mixed or
    fully calibrated), and any state in between.

    Fisher information for a 2PL IRT item:
        I(θ) = a² · P(θ) · (1 − P(θ))
        where P(θ) = 1 / (1 + exp(−a·(θ − b)))

    Args:
        user_theta: Current ability estimate θ (e.g. from BKT or prior IRT step).
        candidates: Non-empty list of Question ORM objects to choose from.

    Returns:
        The candidate with the highest Fisher information.

    Raises:
        ValueError: if candidates is empty.
    """
    if not candidates:
        raise ValueError("candidates must be non-empty")

    def _fisher(q: "Question") -> float:
        a = q.irt_a if q.irt_a is not None else 1.0
        b = effective_b(q)
        z = max(-10.0, min(10.0, a * (user_theta - b)))
        p = 1.0 / (1.0 + math.exp(-z))
        return a * a * p * (1.0 - p)

    return max(candidates, key=_fisher)
```

- [ ] **Step 2: Run recommender tests**

```bash
pytest tests/test_seed_v1.py -v -k "effective_b or pick_next"
```

Expected: All 5 recommender tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/services/recommender.py
git commit -m "feat: add recommender service with effective_b and pick_next_question"
```

---

## Task 11: Create Service Stubs

**Files:**
- Create: `src/services/irt_calibration.py`
- Create: `src/services/embeddings.py`

- [ ] **Step 1: Create `src/services/irt_calibration.py`**

```python
"""
services/irt_calibration.py
----------------------------
IRT calibration batch job stub (Phase 1).

When num_shown >= 30 for a question, this service will estimate irt_a and
irt_b using the py-irt library and write them into questions.irt_a / irt_b.
Once set, the recommender's effective_b() uses irt_b automatically — no
code changes required in the calling layer.

To activate:
    1. pip install py-irt
    2. Implement fit_irt_for_eligible_questions() below.
    3. Run as a nightly batch job (cron or Celery task).
"""

from sqlalchemy.ext.asyncio import AsyncSession


async def fit_irt_for_eligible_questions(session: AsyncSession) -> dict[str, int]:
    """Estimate 2PL IRT parameters for questions with sufficient responses.

    Eligibility: questions where num_shown >= 30 in the user_responses table.

    Phase 1 implementation steps (TODO):
        1. Query eligible question_ids from user_responses:
               SELECT question_id, array_agg(is_correct ORDER BY id)
               FROM user_responses
               GROUP BY question_id
               HAVING COUNT(*) >= 30
        2. For each eligible question, fit 2PL model:
               from py_irt.models import TwoParameterLogistic
               model = TwoParameterLogistic()
               model.fit(responses)
               irt_a, irt_b = model.discrimination, model.difficulty
        3. UPDATE questions
           SET irt_a = :a, irt_b = :b,
               calibration_status = 'ml_calibrated'
           WHERE id = :question_id
        4. Return counts.

    Returns:
        {'calibrated': N, 'skipped': M}  — N calibrated, M skipped (< 30 responses)
    """
    raise NotImplementedError(
        "Phase 1: implement IRT calibration. "
        "Dependency required: py-irt>=0.4.0"
    )
```

- [ ] **Step 2: Create `src/services/embeddings.py`**

```python
"""
services/embeddings.py
-----------------------
Vector embedding generation stub (Phase 1).

Generates 384-dimensional sentence embeddings for questions and topics,
stores them in the embeddings table, and updates content_embedding_id FKs.

To activate:
    1. pip install sentence-transformers pgvector
    2. Implement embed_question() and embed_topic() below.
    3. Run as a batch job after content is seeded or updated.
"""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.models.content import Question, Topic


async def embed_question(q: "Question", session: AsyncSession) -> None:
    """Generate and persist a 384-dim embedding for a question's stem text.

    Phase 1 implementation steps (TODO):
        1. Load model (cache in module-level singleton):
               from sentence_transformers import SentenceTransformer
               _model = SentenceTransformer('all-MiniLM-L6-v2')
        2. vector = _model.encode(q.stem_text).tolist()  # list[float] len=384
        3. UPSERT into embeddings:
               INSERT INTO embeddings (entity_type, entity_id, model, vector)
               VALUES ('question', q.id, 'all-MiniLM-L6-v2', :vector)
               ON CONFLICT (entity_type, entity_id, model) DO UPDATE SET vector = EXCLUDED.vector
        4. UPDATE questions SET content_embedding_id = <embedding_id> WHERE id = q.id
    """
    raise NotImplementedError(
        "Phase 1: implement question embedding. "
        "Dependencies required: sentence-transformers>=2.2.0"
    )


async def embed_topic(t: "Topic", session: AsyncSession) -> None:
    """Generate and persist a 384-dim embedding for a topic's content.

    Text input = f"{t.name}. {t.description or ''}. {' '.join(t.learning_objectives)}"

    Phase 1 implementation steps (TODO):
        Same pattern as embed_question() with entity_type='topic'.
    """
    raise NotImplementedError(
        "Phase 1: implement topic embedding. "
        "Dependencies required: sentence-transformers>=2.2.0"
    )
```

- [ ] **Step 3: Verify both stubs import cleanly**

```bash
python -c "from src.services.irt_calibration import fit_irt_for_eligible_questions; from src.services.embeddings import embed_question, embed_topic; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/services/irt_calibration.py src/services/embeddings.py
git commit -m "feat: add IRT calibration and embeddings service stubs (Phase 1 TODOs)"
```

---

## Task 12: Full Test Suite Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass. Zero failures, zero errors.

- [ ] **Step 2: Verify seed_all twice (production simulation)**

```bash
python -m scripts.seed_all
python -m scripts.seed_all
```

Expected: Both runs print the same counts. No errors.

- [ ] **Step 3: Verify trigger fires correctly**

```bash
psql -U postgres -d ai_learning <<'SQL'
-- Get a real question_id and user_id
SELECT id INTO TEMP q FROM questions LIMIT 1;
SELECT id INTO TEMP u FROM users LIMIT 1;

-- Insert a user_response (simulating a correct answer)
INSERT INTO user_responses (user_id, question_id, context, selected_answer, is_correct)
VALUES (
    (SELECT id FROM u),
    (SELECT id FROM q),
    'quiz',
    'A',
    true
);

-- Verify counter updated
SELECT item_id, num_shown, num_correct FROM questions WHERE id = (SELECT id FROM q);
SQL
```

Expected: `num_shown=1`, `num_correct=1`.

- [ ] **Step 4: Run alembic downgrade and upgrade to test reversibility**

```bash
alembic downgrade 20260415_checkpoint_state
alembic upgrade head
```

Expected: Both commands succeed with no errors. Data is preserved.

---

## Task 13: Write MIGRATION_V1.md

**Files:**
- Create: `MIGRATION_V1.md`

- [ ] **Step 1: Create `MIGRATION_V1.md`**

```markdown
# MIGRATION_V1.md — Hướng dẫn vận hành Schema v1

## Lệnh cần chạy

### Áp dụng migration
```bash
# Kiểm tra trạng thái hiện tại
alembic current

# Chạy migration (thêm tất cả bảng/cột v1)
alembic upgrade head

# Verify: kiểm tra bảng mới đã có
psql -U postgres -d ai_learning -c "\dt user_responses user_mastery review_schedule tutor_sessions embeddings"
```

### Seed dữ liệu ban đầu
```bash
# Seed tất cả courses
python -m scripts.seed_all

# Seed riêng một course
python -m scripts.seed_all --course cs224n_nlp

# Chạy lần 2 để verify idempotent (không tạo duplicate)
python -m scripts.seed_all
```

### Chạy test suite
```bash
pytest tests/ -v
pytest tests/test_seed_v1.py -v  # chỉ test v1
```

---

## Rollback Plan

### Rollback migration (nếu có sự cố)

```bash
# Kiểm tra revision hiện tại
alembic current

# Rollback về trước v1 migration
alembic downgrade 20260415_checkpoint_state
```

**Lưu ý quan trọng khi rollback:**
- Downgrade sẽ **DROP** 5 bảng mới: `user_responses`, `user_mastery`, `review_schedule`, `tutor_sessions`, `embeddings`.
- Nếu đã có dữ liệu production trong các bảng này, **BACKUP TRƯỚC** khi rollback:
```bash
pg_dump -U postgres -d ai_learning -t user_responses -t user_mastery \
    -t review_schedule -t tutor_sessions > v1_tables_backup.sql
```
- Downgrade cũng xóa các cột mới trên `questions`, `modules`, `topics`, `knowledge_components`.
- Dữ liệu trong các cột cũ (existing fields) **KHÔNG bị ảnh hưởng**.

---

## Điểm quan trọng cần biết

### Protected fields trên questions
Các field sau **KHÔNG BAO GIỜ bị ghi đè** khi re-seed:
- `num_shown`, `num_correct` — counter tích lũy từ `user_responses`
- `irt_a`, `irt_b` — IRT params từ calibration job (Phase 1)
- `calibration_status` — trạng thái calibration
- `content_embedding_id` — FK tới embedding

### Trigger tự động
Postgres trigger `trg_update_question_counters` tự động cập nhật `num_shown`/`num_correct` mỗi khi có INSERT vào `user_responses`. **Không cần code application nào**.

### Phân biệt hai tập cột IRT
| Cột cũ (legacy) | Cột mới (v1) | Ý nghĩa |
|---|---|---|
| `irt_difficulty` | `irt_b` | b-parameter (độ khó) |
| `irt_discrimination` | `irt_a` | a-parameter (độ phân biệt) |

Recommender dùng `irt_b` (mới). Cột cũ giữ nguyên để backward compat.

### Phase 0 → Phase 1 transition
- Phase 0: `irt_b = NULL` → `effective_b()` fallback về `difficulty_bucket`
- Phase 1: Chạy batch job `fit_irt_for_eligible_questions()` (khi `num_shown >= 30`)
  → `irt_b` được điền → `effective_b()` tự động dùng giá trị mới
- **Không cần ALTER TABLE, không cần đổi code gọi.**

### pgvector prerequisite
Extension `vector` phải được cài trong PostgreSQL:
```bash
# macOS (Homebrew)
brew install pgvector

# Ubuntu/Debian
sudo apt install postgresql-14-pgvector

# Verify
psql -U postgres -c "SELECT * FROM pg_available_extensions WHERE name='vector';"
```
```

- [ ] **Step 2: Commit**

```bash
git add MIGRATION_V1.md
git commit -m "docs: add MIGRATION_V1.md with Vietnamese ops guide and rollback plan"
```

---

## Self-Review Checklist

After all tasks are complete, verify against the original spec:

- [ ] `alembic upgrade head` runs clean on existing DB — verified in Task 2 Step 3
- [ ] All 10 deliverables are present:
  - `alembic/versions/20260418_0001_schema_v1.py` ✓
  - `src/models/content.py` updated ✓, `src/models/state.py` ✓, `src/models/v1_tables.py` ✓
  - `src/schemas/v1_seed.py` ✓
  - `src/seed/loader.py` ✓
  - `scripts/seed_all.py` ✓
  - `src/services/recommender.py` ✓
  - `src/services/irt_calibration.py` ✓
  - `src/services/embeddings.py` ✓
  - `tests/test_seed_v1.py` ✓
  - `MIGRATION_V1.md` ✓
- [ ] `python -m scripts.seed_all` runs twice without errors and produces same counts
- [ ] `pytest tests/test_seed_v1.py -v` — all pass
- [ ] `pytest tests/` — no regression in existing tests
- [ ] Recommender returns valid question when all `irt_b=NULL` (Phase 0) ✓
- [ ] Recommender returns valid question in mixed mode ✓
- [ ] MIGRATION_V1.md explains rollback steps ✓
