"""
models/canonical.py
-------------------
Canonical content-layer tables materialized from the validated JSONL artifact
bundle under data/final_artifacts/cs224n_cs231n_v1/canonical/.

These tables use deterministic natural keys from the canonical artifacts
(`kp_id`, `unit_id`, `item_id`, and edge pairs) so import/backfill can be
idempotent without an extra mapping layer.
"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ConceptKP(TimestampMixin, Base):
    """Global canonical knowledge point catalog."""

    __tablename__ = "concepts_kp"

    kp_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    track_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    domain_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    career_path_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    difficulty_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    difficulty_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    importance_level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    structural_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    importance: Mapped[float | None] = mapped_column(Float, nullable=True)
    importance_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    importance_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_scope: Mapped[str | None] = mapped_column(String(120), nullable=True)
    importance_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_course_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    description_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_concepts_kp_name", "name"),
        Index("ix_concepts_kp_difficulty", "difficulty_level"),
    )


class CanonicalUnit(TimestampMixin, Base):
    """Canonical learning unit exported from P1 sanitized course artifacts."""

    __tablename__ = "units"

    unit_id: Mapped[str] = mapped_column(String(220), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(80), nullable=False)
    lecture_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lecture_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lecture_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordering_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    section_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    difficulty_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcript_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_clip_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    topic_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_units_course_lecture", "course_id", "lecture_id"),
        Index("ix_units_course_order", "course_id", "lecture_order", "ordering_index"),
    )


class UnitKPMap(TimestampMixin, Base):
    """Many-to-many mapping from canonical units to global KP IDs."""

    __tablename__ = "unit_kp_map"

    unit_id: Mapped[str] = mapped_column(
        String(220), ForeignKey("units.unit_id", ondelete="CASCADE"), primary_key=True
    )
    kp_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("concepts_kp.kp_id", ondelete="CASCADE"), primary_key=True
    )
    planner_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    instruction_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    coverage_level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    coverage_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    coverage_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    coverage_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_local_kp_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_unit_kp_map_kp", "kp_id"),
        Index("ix_unit_kp_map_unit", "unit_id"),
    )


class QuestionBankItem(TimestampMixin, Base):
    """Authored assessment item content separated from calibration and phase use."""

    __tablename__ = "question_bank"

    item_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(80), nullable=False)
    lecture_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    unit_id: Mapped[str] = mapped_column(
        String(220), ForeignKey("units.unit_id", ondelete="CASCADE"), nullable=False
    )
    primary_kp_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("concepts_kp.kp_id", ondelete="RESTRICT"), nullable=False
    )
    item_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list] = mapped_column(JSON, nullable=False)
    answer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(80), nullable=True)
    question_intent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    knowledge_scope: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assessment_purpose: Mapped[str | None] = mapped_column(String(120), nullable=True)
    render_mode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    grounding_mode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    grounding_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    concept_alignment_cosine: Mapped[float | None] = mapped_column(Float, nullable=True)
    distractor_cosine_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    distractor_cosine_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    qa_gate_passed: Mapped[bool | None] = mapped_column(nullable=True)
    repair_history: Mapped[list | None] = mapped_column(JSON, nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_question_bank_unit", "unit_id"),
        Index("ix_question_bank_primary_kp", "primary_kp_id"),
        Index("ix_question_bank_course_lecture", "course_id", "lecture_id"),
        Index("ix_question_bank_review_status", "review_status"),
    )


class ItemCalibration(TimestampMixin, Base):
    """Static and future calibrated item parameters separated from authored content."""

    __tablename__ = "item_calibration"

    item_id: Mapped[str] = mapped_column(
        String(180), ForeignKey("question_bank.item_id", ondelete="CASCADE"), primary_key=True
    )
    course_id: Mapped[str] = mapped_column(String(80), nullable=False)
    lecture_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    unit_id: Mapped[str] = mapped_column(
        String(220), ForeignKey("units.unit_id", ondelete="CASCADE"), nullable=False
    )
    difficulty_prior: Mapped[str | None] = mapped_column(String(80), nullable=True)
    discrimination_prior: Mapped[float | None] = mapped_column(Float, nullable=True)
    guessing_prior: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibration_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    calibration_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    calibration_method: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_calibrated: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    difficulty_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    discrimination_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    guessing_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    irt_calibration_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    standard_error_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_calibrated_at: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_item_calibration_unit", "unit_id"),
        Index("ix_item_calibration_method", "calibration_method"),
    )


class ItemPhaseMap(TimestampMixin, Base):
    """Phase suitability map for item selection."""

    __tablename__ = "item_phase_map"

    item_id: Mapped[str] = mapped_column(
        String(180), ForeignKey("question_bank.item_id", ondelete="CASCADE"), primary_key=True
    )
    phase: Mapped[str] = mapped_column(String(80), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(80), nullable=False)
    lecture_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    unit_id: Mapped[str] = mapped_column(
        String(220), ForeignKey("units.unit_id", ondelete="CASCADE"), nullable=False
    )
    suitability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    phase_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    selection_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phase_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_reviewed_at: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_item_phase_map_phase", "phase"),
        Index("ix_item_phase_map_unit", "unit_id"),
    )


class ItemKPMap(TimestampMixin, Base):
    """Q-matrix row mapping an item to one or more canonical KP IDs."""

    __tablename__ = "item_kp_map"

    item_id: Mapped[str] = mapped_column(
        String(180), ForeignKey("question_bank.item_id", ondelete="CASCADE"), primary_key=True
    )
    kp_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("concepts_kp.kp_id", ondelete="CASCADE"), primary_key=True
    )
    kp_role: Mapped[str] = mapped_column(String(80), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(80), nullable=False)
    lecture_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    unit_id: Mapped[str] = mapped_column(
        String(220), ForeignKey("units.unit_id", ondelete="CASCADE"), nullable=False
    )
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    mapping_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_item_kp_map_kp", "kp_id"),
        Index("ix_item_kp_map_unit", "unit_id"),
        Index("ix_item_kp_map_item", "item_id"),
    )


class PrerequisiteEdge(TimestampMixin, Base):
    """Final kept prerequisite edge after P5 + GPT audit."""

    __tablename__ = "prerequisite_edges"

    source_kp_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("concepts_kp.kp_id", ondelete="CASCADE"), primary_key=True
    )
    target_kp_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("concepts_kp.kp_id", ondelete="CASCADE"), primary_key=True
    )
    edge_scope: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    edge_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    bidirectional_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    p5_keep_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    p5_expected_directionality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    p5_trace: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    temporal_signal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_first_seen: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    target_first_seen: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_prerequisite_edges_target", "target_kp_id"),
        Index("ix_prerequisite_edges_scope", "edge_scope"),
        Index("ix_prerequisite_edges_review", "review_status"),
    )


class PrunedEdge(TimestampMixin, Base):
    """Rejected/pruned prerequisite edge retained for audit."""

    __tablename__ = "pruned_edges"

    source_kp_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("concepts_kp.kp_id", ondelete="CASCADE"), primary_key=True
    )
    target_kp_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("concepts_kp.kp_id", ondelete="CASCADE"), primary_key=True
    )
    prune_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    edge_scope: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    edge_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    bidirectional_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    p5_keep_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    p5_expected_directionality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    p5_trace: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    temporal_signal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_first_seen: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    target_first_seen: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_pruned_edges_target", "target_kp_id"),
        Index("ix_pruned_edges_reason", "prune_reason"),
    )
