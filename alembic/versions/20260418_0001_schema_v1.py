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

    # 0. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. Create new enum types (checkfirst prevents duplicate-type errors)
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

    # 2. Add slug columns to modules, topics, knowledge_components
    op.add_column("modules", sa.Column("slug", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_modules_slug", "modules", ["slug"])

    op.add_column("topics", sa.Column("slug", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_topics_slug", "topics", ["slug"])

    op.add_column(
        "knowledge_components",
        sa.Column("slug", sa.String(100), nullable=True),
    )
    op.create_unique_constraint("uq_kc_slug", "knowledge_components", ["slug"])

    # 3. Add v1 columns to modules
    op.add_column(
        "modules",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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

    # 4. Add v1 columns to topics
    op.add_column(
        "topics",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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

    # 5. Add v1 columns to questions
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
        sa.Column("num_shown", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "questions",
        sa.Column("num_correct", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("questions", sa.Column("irt_a", sa.Float(), nullable=True))
    op.add_column("questions", sa.Column("irt_b", sa.Float(), nullable=True))
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

    # 6. Create embeddings table
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

    # 7. Create user_responses table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_responses (
            id                     BIGSERIAL   PRIMARY KEY,
            user_id                UUID        NOT NULL
                                   REFERENCES users(id) ON DELETE CASCADE,
            question_id            UUID        NOT NULL
                                   REFERENCES questions(id) ON DELETE RESTRICT,
            session_id             UUID
                                   REFERENCES sessions(id) ON DELETE SET NULL,
            context                response_context_enum NOT NULL,
            selected_answer        CHAR(1),
            is_correct             BOOLEAN     NOT NULL,
            time_taken_ms          INTEGER,
            theta_before           REAL,
            question_irt_b_at_time REAL,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_responses_user_id ON user_responses(user_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_responses_question_id ON user_responses(question_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_responses_user_created "
        "ON user_responses(user_id, created_at);"
    )

    # 8. Create user_mastery table
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
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_mastery_user_id ON user_mastery(user_id);")

    # 9. Create review_schedule table
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

    # 10. Create tutor_sessions table
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
    op.execute("CREATE INDEX IF NOT EXISTS ix_tutor_sessions_user_id ON tutor_sessions(user_id);")

    # 11. Postgres trigger: update num_shown / num_correct on user_responses INSERT
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

    op.execute("DROP TRIGGER IF EXISTS trg_update_question_counters ON user_responses;")
    op.execute("DROP FUNCTION IF EXISTS update_question_response_counters();")

    op.execute("DROP TABLE IF EXISTS tutor_sessions;")
    op.execute("DROP TABLE IF EXISTS review_schedule;")
    op.execute("DROP TABLE IF EXISTS user_mastery;")
    op.execute("DROP TABLE IF EXISTS user_responses;")
    op.execute("DROP TABLE IF EXISTS embeddings;")

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

    for col in ["content_embedding_id", "assessment_config", "learning_objectives", "status", "version"]:
        op.drop_column("topics", col)
    op.drop_constraint("uq_topics_slug", "topics", type_="unique")
    op.drop_column("topics", "slug")

    for col in ["status", "version"]:
        op.drop_column("modules", col)
    op.drop_constraint("uq_modules_slug", "modules", type_="unique")
    op.drop_column("modules", "slug")

    op.drop_constraint("uq_kc_slug", "knowledge_components", type_="unique")
    op.drop_column("knowledge_components", "slug")

    for type_name in [
        "response_context_enum",
        "content_status_enum",
        "calibration_status_enum",
        "review_status_enum",
        "question_source_enum",
    ]:
        sa.Enum(name=type_name).drop(bind, checkfirst=True)
