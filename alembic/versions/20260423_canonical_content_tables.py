"""Materialize canonical content artifact tables.

Revision ID: 20260423_canonical_content
Revises: 20260423_planner_stubs
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260423_canonical_content"
down_revision: str | None = "20260423_planner_stubs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = postgresql.JSON(astext_type=sa.Text())


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "concepts_kp",
        sa.Column("kp_id", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("track_tags", JSON, nullable=True),
        sa.Column("domain_tags", JSON, nullable=True),
        sa.Column("career_path_tags", JSON, nullable=True),
        sa.Column("difficulty_level", sa.Float(), nullable=True),
        sa.Column("difficulty_source", sa.String(length=120), nullable=True),
        sa.Column("difficulty_confidence", sa.String(length=40), nullable=True),
        sa.Column("importance_level", sa.String(length=80), nullable=True),
        sa.Column("structural_role", sa.String(length=80), nullable=True),
        sa.Column("importance", sa.Float(), nullable=True),
        sa.Column("importance_confidence", sa.String(length=40), nullable=True),
        sa.Column("importance_rationale", sa.Text(), nullable=True),
        sa.Column("importance_scope", sa.String(length=120), nullable=True),
        sa.Column("importance_source", sa.String(length=120), nullable=True),
        sa.Column("source_course_ids", JSON, nullable=True),
        sa.Column("description_embedding", JSON, nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("kp_id"),
    )
    op.create_index("ix_concepts_kp_name", "concepts_kp", ["name"])
    op.create_index("ix_concepts_kp_difficulty", "concepts_kp", ["difficulty_level"])

    op.create_table(
        "units",
        sa.Column("unit_id", sa.String(length=220), nullable=False),
        sa.Column("course_id", sa.String(length=80), nullable=False),
        sa.Column("lecture_id", sa.String(length=160), nullable=True),
        sa.Column("lecture_order", sa.Integer(), nullable=True),
        sa.Column("lecture_title", sa.String(length=255), nullable=True),
        sa.Column("unit_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("ordering_index", sa.Integer(), nullable=True),
        sa.Column("content_ref", JSON, nullable=True),
        sa.Column("key_points", JSON, nullable=True),
        sa.Column("section_flags", JSON, nullable=True),
        sa.Column("difficulty", sa.Float(), nullable=True),
        sa.Column("difficulty_source", sa.String(length=120), nullable=True),
        sa.Column("difficulty_confidence", sa.String(length=40), nullable=True),
        sa.Column("duration_min", sa.Float(), nullable=True),
        sa.Column("transcript_path", sa.String(length=500), nullable=True),
        sa.Column("video_clip_ref", JSON, nullable=True),
        sa.Column("topic_embedding", JSON, nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("unit_id"),
    )
    op.create_index("ix_units_course_lecture", "units", ["course_id", "lecture_id"])
    op.create_index("ix_units_course_order", "units", ["course_id", "lecture_order", "ordering_index"])

    op.create_table(
        "unit_kp_map",
        sa.Column("unit_id", sa.String(length=220), nullable=False),
        sa.Column("kp_id", sa.String(length=160), nullable=False),
        sa.Column("planner_role", sa.String(length=80), nullable=True),
        sa.Column("instruction_role", sa.String(length=80), nullable=True),
        sa.Column("coverage_level", sa.String(length=80), nullable=True),
        sa.Column("coverage_confidence", sa.String(length=40), nullable=True),
        sa.Column("coverage_rationale", sa.Text(), nullable=True),
        sa.Column("coverage_weight", sa.Float(), nullable=True),
        sa.Column("source_local_kp_ids", JSON, nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["unit_id"], ["units.unit_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kp_id"], ["concepts_kp.kp_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("unit_id", "kp_id"),
    )
    op.create_index("ix_unit_kp_map_unit", "unit_kp_map", ["unit_id"])
    op.create_index("ix_unit_kp_map_kp", "unit_kp_map", ["kp_id"])

    op.create_table(
        "question_bank",
        sa.Column("item_id", sa.String(length=180), nullable=False),
        sa.Column("course_id", sa.String(length=80), nullable=False),
        sa.Column("lecture_id", sa.String(length=160), nullable=True),
        sa.Column("unit_id", sa.String(length=220), nullable=False),
        sa.Column("primary_kp_id", sa.String(length=160), nullable=False),
        sa.Column("item_type", sa.String(length=80), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("choices", JSON, nullable=False),
        sa.Column("answer_index", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=80), nullable=True),
        sa.Column("question_intent", sa.String(length=80), nullable=True),
        sa.Column("knowledge_scope", sa.String(length=120), nullable=True),
        sa.Column("assessment_purpose", sa.String(length=120), nullable=True),
        sa.Column("render_mode", sa.String(length=80), nullable=True),
        sa.Column("grounding_mode", sa.String(length=80), nullable=True),
        sa.Column("grounding_confidence", sa.String(length=40), nullable=True),
        sa.Column("source_ref", JSON, nullable=True),
        sa.Column("concept_alignment_cosine", sa.Float(), nullable=True),
        sa.Column("distractor_cosine_lower", sa.Float(), nullable=True),
        sa.Column("distractor_cosine_upper", sa.Float(), nullable=True),
        sa.Column("qa_gate_passed", sa.Boolean(), nullable=True),
        sa.Column("repair_history", JSON, nullable=True),
        sa.Column("provenance", sa.String(length=120), nullable=True),
        sa.Column("review_status", sa.String(length=80), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["unit_id"], ["units.unit_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_kp_id"], ["concepts_kp.kp_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index("ix_question_bank_unit", "question_bank", ["unit_id"])
    op.create_index("ix_question_bank_primary_kp", "question_bank", ["primary_kp_id"])
    op.create_index("ix_question_bank_course_lecture", "question_bank", ["course_id", "lecture_id"])
    op.create_index("ix_question_bank_review_status", "question_bank", ["review_status"])

    op.create_table(
        "item_calibration",
        sa.Column("item_id", sa.String(length=180), nullable=False),
        sa.Column("course_id", sa.String(length=80), nullable=False),
        sa.Column("lecture_id", sa.String(length=160), nullable=True),
        sa.Column("unit_id", sa.String(length=220), nullable=False),
        sa.Column("difficulty_prior", sa.Float(), nullable=True),
        sa.Column("discrimination_prior", sa.Float(), nullable=True),
        sa.Column("guessing_prior", sa.Float(), nullable=True),
        sa.Column("calibration_confidence", sa.String(length=40), nullable=True),
        sa.Column("calibration_rationale", sa.Text(), nullable=True),
        sa.Column("calibration_method", sa.String(length=120), nullable=True),
        sa.Column("is_calibrated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("difficulty_b", sa.Float(), nullable=True),
        sa.Column("discrimination_a", sa.Float(), nullable=True),
        sa.Column("guessing_c", sa.Float(), nullable=True),
        sa.Column("irt_calibration_n", sa.Integer(), nullable=True),
        sa.Column("standard_error_b", sa.Float(), nullable=True),
        sa.Column("last_calibrated_at", sa.String(length=80), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["item_id"], ["question_bank.item_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.unit_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index("ix_item_calibration_unit", "item_calibration", ["unit_id"])
    op.create_index("ix_item_calibration_method", "item_calibration", ["calibration_method"])

    op.create_table(
        "item_phase_map",
        sa.Column("item_id", sa.String(length=180), nullable=False),
        sa.Column("phase", sa.String(length=80), nullable=False),
        sa.Column("course_id", sa.String(length=80), nullable=False),
        sa.Column("lecture_id", sa.String(length=160), nullable=True),
        sa.Column("unit_id", sa.String(length=220), nullable=False),
        sa.Column("suitability_score", sa.Float(), nullable=True),
        sa.Column("phase_multiplier", sa.Float(), nullable=True),
        sa.Column("selection_priority", sa.Integer(), nullable=True),
        sa.Column("phase_rationale", sa.Text(), nullable=True),
        sa.Column("last_reviewed_at", sa.String(length=80), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["item_id"], ["question_bank.item_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.unit_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id", "phase"),
    )
    op.create_index("ix_item_phase_map_phase", "item_phase_map", ["phase"])
    op.create_index("ix_item_phase_map_unit", "item_phase_map", ["unit_id"])

    op.create_table(
        "item_kp_map",
        sa.Column("item_id", sa.String(length=180), nullable=False),
        sa.Column("kp_id", sa.String(length=160), nullable=False),
        sa.Column("kp_role", sa.String(length=80), nullable=False),
        sa.Column("course_id", sa.String(length=80), nullable=False),
        sa.Column("lecture_id", sa.String(length=160), nullable=True),
        sa.Column("unit_id", sa.String(length=220), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("mapping_confidence", sa.String(length=40), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["item_id"], ["question_bank.item_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kp_id"], ["concepts_kp.kp_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.unit_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id", "kp_id", "kp_role"),
    )
    op.create_index("ix_item_kp_map_item", "item_kp_map", ["item_id"])
    op.create_index("ix_item_kp_map_kp", "item_kp_map", ["kp_id"])
    op.create_index("ix_item_kp_map_unit", "item_kp_map", ["unit_id"])

    for table_name, has_prune_reason in (
        ("prerequisite_edges", False),
        ("pruned_edges", True),
    ):
        columns = [
            sa.Column("source_kp_id", sa.String(length=160), nullable=False),
            sa.Column("target_kp_id", sa.String(length=160), nullable=False),
        ]
        if has_prune_reason:
            columns.append(sa.Column("prune_reason", sa.String(length=160), nullable=True))
        columns.extend(
            [
                sa.Column("edge_scope", sa.String(length=80), nullable=True),
                sa.Column("provenance", sa.String(length=120), nullable=True),
                sa.Column("review_status", sa.String(length=80), nullable=True),
                sa.Column("confidence", sa.String(length=40), nullable=True),
                sa.Column("rationale", sa.Text(), nullable=True),
                sa.Column("edge_strength", sa.Float(), nullable=True),
                sa.Column("bidirectional_score", sa.Float(), nullable=True),
                sa.Column("p5_keep_confidence", sa.String(length=40), nullable=True),
                sa.Column("p5_expected_directionality", sa.String(length=120), nullable=True),
                sa.Column("p5_trace", JSON, nullable=True),
                sa.Column("temporal_signal", sa.String(length=120), nullable=True),
                sa.Column("source_first_seen", JSON, nullable=True),
                sa.Column("target_first_seen", JSON, nullable=True),
                sa.Column("source_file", sa.String(length=500), nullable=True),
                *_timestamps(),
                sa.ForeignKeyConstraint(["source_kp_id"], ["concepts_kp.kp_id"], ondelete="CASCADE"),
                sa.ForeignKeyConstraint(["target_kp_id"], ["concepts_kp.kp_id"], ondelete="CASCADE"),
                sa.PrimaryKeyConstraint("source_kp_id", "target_kp_id"),
            ]
        )
        op.create_table(table_name, *columns)
        op.create_index(f"ix_{table_name}_target", table_name, ["target_kp_id"])
        if has_prune_reason:
            op.create_index("ix_pruned_edges_reason", table_name, ["prune_reason"])
        else:
            op.create_index("ix_prerequisite_edges_scope", table_name, ["edge_scope"])
            op.create_index("ix_prerequisite_edges_review", table_name, ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_pruned_edges_reason", table_name="pruned_edges")
    op.drop_index("ix_pruned_edges_target", table_name="pruned_edges")
    op.drop_table("pruned_edges")

    op.drop_index("ix_prerequisite_edges_review", table_name="prerequisite_edges")
    op.drop_index("ix_prerequisite_edges_scope", table_name="prerequisite_edges")
    op.drop_index("ix_prerequisite_edges_target", table_name="prerequisite_edges")
    op.drop_table("prerequisite_edges")

    op.drop_index("ix_item_kp_map_unit", table_name="item_kp_map")
    op.drop_index("ix_item_kp_map_kp", table_name="item_kp_map")
    op.drop_index("ix_item_kp_map_item", table_name="item_kp_map")
    op.drop_table("item_kp_map")

    op.drop_index("ix_item_phase_map_unit", table_name="item_phase_map")
    op.drop_index("ix_item_phase_map_phase", table_name="item_phase_map")
    op.drop_table("item_phase_map")

    op.drop_index("ix_item_calibration_method", table_name="item_calibration")
    op.drop_index("ix_item_calibration_unit", table_name="item_calibration")
    op.drop_table("item_calibration")

    op.drop_index("ix_question_bank_review_status", table_name="question_bank")
    op.drop_index("ix_question_bank_course_lecture", table_name="question_bank")
    op.drop_index("ix_question_bank_primary_kp", table_name="question_bank")
    op.drop_index("ix_question_bank_unit", table_name="question_bank")
    op.drop_table("question_bank")

    op.drop_index("ix_unit_kp_map_kp", table_name="unit_kp_map")
    op.drop_index("ix_unit_kp_map_unit", table_name="unit_kp_map")
    op.drop_table("unit_kp_map")

    op.drop_index("ix_units_course_order", table_name="units")
    op.drop_index("ix_units_course_lecture", table_name="units")
    op.drop_table("units")

    op.drop_index("ix_concepts_kp_difficulty", table_name="concepts_kp")
    op.drop_index("ix_concepts_kp_name", table_name="concepts_kp")
    op.drop_table("concepts_kp")
