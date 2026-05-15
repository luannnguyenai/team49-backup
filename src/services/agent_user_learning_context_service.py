from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import CanonicalUnit, ConceptKP, QuestionBankItem
from src.models.course import Course, CourseSection, LearningProgressRecord, LearningUnit
from src.models.learning import (
    Interaction,
    LearnerMasteryKP,
    PlannerSessionState,
    Session,
    WaivedUnit,
)
from src.models.placement import PlacementAssessmentResult


class AgentUserLearningContextService:
    """Read-only, user-scoped learning context for Agentic RAG tools.

    This service intentionally exposes a small allowlist of learning analytics
    fields. The caller supplies the authenticated user_id; model-generated tool
    arguments never choose a user or arbitrary SQL.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def snapshot(
        self,
        *,
        user_id: UUID,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
        route_context: Any = None,
        context_kind: str | None = None,
    ) -> dict[str, Any]:
        path_course_ids = current_path_course_ids or allowed_course_ids
        current_unit_row = await self._unit_from_route_context(route_context)
        return {
            "context_kind": self._safe_context_kind(context_kind),
            "available_fields": self.available_fields(),
            "current_learning_state": await self._current_learning_state(
                user_id,
                route_context,
                route_unit=current_unit_row,
            ),
            "progress_summary": await self._progress_summary(user_id, path_course_ids),
            "path_workload_summary": await self._path_workload_summary(user_id, path_course_ids),
            "path_position": await self._path_position(user_id, path_course_ids, current_unit_row),
            "recent_progress": await self._recent_progress(user_id, path_course_ids),
            "weak_knowledge_points": await self._weak_knowledge_points(user_id),
            "recent_assessments": await self._recent_assessments(user_id),
            "quiz_history_analysis": await self._quiz_history_analysis(user_id, path_course_ids),
            "recent_placement_results": await self._recent_placement_results(user_id),
            "waived_units": await self._waived_units(user_id),
        }

    @staticmethod
    def available_fields() -> dict[str, list[str]]:
        return {
            "current_learning_state": [
                "current_unit",
                "current_stage",
                "video_progress_s",
                "watch_percent",
                "has_quiz_items",
                "last_activity",
            ],
            "progress_summary": [
                "status_counts",
                "completed_units",
                "in_progress_units",
                "total_tracked_units",
            ],
            "path_workload_summary": [
                "total_units",
                "done_units",
                "remaining_units",
                "total_estimated_minutes",
                "remaining_estimated_minutes",
                "remaining_estimated_hours",
            ],
            "path_position": [
                "current_index",
                "total_units",
                "previous_unit",
                "current_unit",
                "next_unit",
                "next_unfinished_unit",
            ],
            "recent_progress": [
                "course_id",
                "unit_title",
                "status",
                "last_position_seconds",
                "last_opened_at",
            ],
            "weak_knowledge_points": [
                "kp_id",
                "name",
                "mastery_mean",
                "mastery_lcb",
                "n_items_observed",
                "updated_at",
            ],
            "recent_assessments": [
                "session_type",
                "canonical_phase",
                "unit_title",
                "score_percent",
                "completed_at",
            ],
            "quiz_history_analysis": [
                "total_answered",
                "correct_count",
                "accuracy_percent",
                "weakest_quiz_kps",
                "weakest_quiz_units",
                "recent_session_scores",
                "trend",
                "data_window",
            ],
            "recent_placement_results": [
                "unit_title",
                "score_pct",
                "decision",
                "theta_estimate",
                "created_at",
            ],
            "waived_units": [
                "unit_title",
                "mastery_lcb_at_waive",
                "skip_quiz_score",
                "created_at",
            ],
        }

    async def _current_learning_state(
        self,
        user_id: UUID,
        route_context: Any,
        *,
        route_unit: Any = None,
    ) -> dict[str, Any]:
        state_result = await self.session.execute(
            select(PlannerSessionState)
            .where(PlannerSessionState.user_id == user_id)
            .order_by(
                PlannerSessionState.last_activity.desc().nullslast(),
                PlannerSessionState.updated_at.desc(),
            )
            .limit(1)
        )
        state = state_result.scalar_one_or_none()
        state_unit = await self._unit_by_id(state.current_unit_id) if state and state.current_unit_id else None
        unit_payload = self._unit_payload(route_unit or state_unit)
        progress = state.current_progress if state and isinstance(state.current_progress, dict) else {}
        return {
            "current_unit": unit_payload,
            "current_stage": getattr(state, "current_stage", None) if state else None,
            "video_progress_s": progress.get("video_progress_s"),
            "watch_percent": progress.get("watch_percent"),
            "last_activity": self._iso(getattr(state, "last_activity", None)) if state else None,
        }

    async def _unit_from_route_context(self, route_context: Any):
        canonical_id = self._value_from(route_context, "canonical_unit_id") or self._value_from(
            route_context, "canonicalUnitId"
        )
        unit_slug = self._value_from(route_context, "unit_slug") or self._value_from(
            route_context, "unitSlug"
        )
        course_slug = self._value_from(route_context, "course_slug") or self._value_from(
            route_context, "courseSlug"
        )
        if canonical_id:
            result = await self.session.execute(
                select(LearningUnit, Course, CourseSection)
                .join(Course, LearningUnit.course_id == Course.id)
                .join(CourseSection, LearningUnit.section_id == CourseSection.id)
                .where(LearningUnit.canonical_unit_id == str(canonical_id))
                .limit(1)
            )
            row = result.first()
            if row:
                return row
        if unit_slug and course_slug:
            result = await self.session.execute(
                select(LearningUnit, Course, CourseSection)
                .join(Course, LearningUnit.course_id == Course.id)
                .join(CourseSection, LearningUnit.section_id == CourseSection.id)
                .where(LearningUnit.slug == str(unit_slug), Course.slug == str(course_slug))
                .limit(1)
            )
            return result.first()
        return None

    async def _unit_by_id(self, unit_id: UUID):
        result = await self.session.execute(
            select(LearningUnit, Course, CourseSection)
            .join(Course, LearningUnit.course_id == Course.id)
            .join(CourseSection, LearningUnit.section_id == CourseSection.id)
            .where(LearningUnit.id == unit_id)
            .limit(1)
        )
        return result.first()

    async def _progress_summary(self, user_id: UUID, course_ids: list[str]) -> dict[str, Any]:
        filters = self._course_filters(course_ids)
        stmt = (
            select(LearningProgressRecord.status, func.count(LearningProgressRecord.id))
            .join(Course, LearningProgressRecord.course_id == Course.id)
            .where(LearningProgressRecord.user_id == user_id)
            .group_by(LearningProgressRecord.status)
        )
        if filters:
            stmt = stmt.where(or_(*filters))
        result = await self.session.execute(stmt)
        counts = {
            self._value(status): int(count)
            for status, count in result.all()
        }
        total = sum(counts.values())
        return {
            "status_counts": counts,
            "completed_units": counts.get("completed", 0),
            "in_progress_units": counts.get("in_progress", 0),
            "skipped_units": counts.get("skipped", 0),
            "total_tracked_units": total,
        }

    async def _path_workload_summary(self, user_id: UUID, course_ids: list[str]) -> dict[str, Any]:
        filters = self._course_filters(course_ids)
        stmt = (
            select(LearningUnit, Course, LearningProgressRecord)
            .join(Course, LearningUnit.course_id == Course.id)
            .outerjoin(
                LearningProgressRecord,
                and_(
                    LearningProgressRecord.learning_unit_id == LearningUnit.id,
                    LearningProgressRecord.user_id == user_id,
                ),
            )
            .order_by(Course.sort_order, LearningUnit.sort_order)
        )
        if filters:
            stmt = stmt.where(or_(*filters))
        result = await self.session.execute(stmt)

        total_units = 0
        done_units = 0
        remaining_units = 0
        total_minutes = 0.0
        remaining_minutes = 0.0
        missing_estimate_units = 0
        course_ids_seen: set[str] = set()

        for unit, course, progress in result.all():
            total_units += 1
            course_ids_seen.add(course.canonical_course_id or course.slug)
            estimated = float(unit.estimated_minutes or 0)
            if unit.estimated_minutes is None:
                missing_estimate_units += 1
            total_minutes += estimated

            status = self._value(progress.status) if progress else "not_started"
            if status in {"completed", "skipped"}:
                done_units += 1
                continue

            remaining_units += 1
            watched_minutes = 0.0
            if progress and progress.last_position_seconds is not None:
                watched_minutes = max(0.0, float(progress.last_position_seconds) / 60.0)
            remaining_minutes += max(0.0, estimated - min(estimated, watched_minutes))

        return {
            "course_ids": sorted(course_ids_seen),
            "total_units": total_units,
            "done_units": done_units,
            "remaining_units": remaining_units,
            "total_estimated_minutes": round(total_minutes, 1),
            "remaining_estimated_minutes": round(remaining_minutes, 1),
            "remaining_estimated_hours": round(remaining_minutes / 60.0, 2),
            "missing_estimate_units": missing_estimate_units,
        }

    async def _path_position(self, user_id: UUID, course_ids: list[str], current_unit_row) -> dict[str, Any]:
        filters = self._course_filters(course_ids)
        stmt = (
            select(LearningUnit, Course, CourseSection, LearningProgressRecord)
            .join(Course, LearningUnit.course_id == Course.id)
            .join(CourseSection, LearningUnit.section_id == CourseSection.id)
            .outerjoin(
                LearningProgressRecord,
                and_(
                    LearningProgressRecord.learning_unit_id == LearningUnit.id,
                    LearningProgressRecord.user_id == user_id,
                ),
            )
            .order_by(Course.sort_order, CourseSection.sort_order, LearningUnit.sort_order)
        )
        if filters:
            stmt = stmt.where(or_(*filters))
        result = await self.session.execute(stmt)
        return self._path_position_payload(result.all(), current_unit_row)

    @classmethod
    def _path_position_payload(cls, rows: list[Any], current_unit_row) -> dict[str, Any]:
        if not rows:
            return {
                "current_index": None,
                "total_units": 0,
                "previous_unit": None,
                "current_unit": None,
                "next_unit": None,
                "next_unfinished_unit": None,
            }
        current_unit = current_unit_row[0] if current_unit_row else None
        current_id = getattr(current_unit, "id", None)
        current_index = None
        for index, row in enumerate(rows):
            unit = row[0]
            if current_id is not None and getattr(unit, "id", None) == current_id:
                current_index = index
                break
        next_unfinished = None
        if current_index is not None:
            for row in rows[current_index + 1 :]:
                progress = row[3] if len(row) > 3 else None
                status = cls._value(progress.status) if progress else "not_started"
                if status not in {"completed", "skipped"}:
                    next_unfinished = row
                    break
        return {
            "current_index": current_index + 1 if current_index is not None else None,
            "total_units": len(rows),
            "previous_unit": cls._unit_payload(rows[current_index - 1]) if current_index and current_index > 0 else None,
            "current_unit": cls._unit_payload(rows[current_index]) if current_index is not None else None,
            "next_unit": cls._unit_payload(rows[current_index + 1])
            if current_index is not None and current_index + 1 < len(rows)
            else None,
            "next_unfinished_unit": cls._unit_payload(next_unfinished),
        }

    async def _recent_progress(self, user_id: UUID, course_ids: list[str]) -> list[dict[str, Any]]:
        filters = self._course_filters(course_ids)
        stmt = (
            select(LearningProgressRecord, LearningUnit, Course, CourseSection)
            .join(LearningUnit, LearningProgressRecord.learning_unit_id == LearningUnit.id)
            .join(Course, LearningProgressRecord.course_id == Course.id)
            .join(CourseSection, LearningUnit.section_id == CourseSection.id)
            .where(LearningProgressRecord.user_id == user_id)
            .order_by(LearningProgressRecord.last_opened_at.desc())
            .limit(8)
        )
        if filters:
            stmt = stmt.where(or_(*filters))
        result = await self.session.execute(stmt)
        rows = []
        for progress, unit, course, section in result.all():
            rows.append(
                {
                    "course_id": course.canonical_course_id or course.slug,
                    "course_slug": course.slug,
                    "section_title": section.title,
                    "unit_title": unit.title,
                    "canonical_unit_id": unit.canonical_unit_id,
                    "status": self._value(progress.status),
                    "last_position_seconds": progress.last_position_seconds,
                    "last_opened_at": self._iso(progress.last_opened_at),
                    "completed_at": self._iso(progress.completed_at),
                }
            )
        return rows

    async def _weak_knowledge_points(self, user_id: UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(LearnerMasteryKP, ConceptKP)
            .outerjoin(ConceptKP, LearnerMasteryKP.kp_id == ConceptKP.kp_id)
            .where(LearnerMasteryKP.user_id == user_id)
            .order_by(
                LearnerMasteryKP.mastery_mean_cached.asc(),
                LearnerMasteryKP.n_items_observed.desc(),
                LearnerMasteryKP.updated_at.desc(),
            )
            .limit(8)
        )
        rows = []
        for mastery, concept in result.all():
            lcb = max(0.0, float(mastery.mastery_mean_cached) - float(mastery.theta_sigma) * 0.5)
            rows.append(
                {
                    "kp_id": mastery.kp_id,
                    "name": concept.name if concept else mastery.kp_id,
                    "mastery_mean": round(float(mastery.mastery_mean_cached), 3),
                    "mastery_lcb": round(lcb, 3),
                    "n_items_observed": mastery.n_items_observed,
                    "updated_at": self._iso(mastery.updated_at),
                }
            )
        return rows

    async def _recent_assessments(self, user_id: UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(Session, LearningUnit, Course)
            .outerjoin(LearningUnit, Session.canonical_unit_id == LearningUnit.id)
            .outerjoin(Course, LearningUnit.course_id == Course.id)
            .where(Session.user_id == user_id)
            .order_by(Session.started_at.desc())
            .limit(6)
        )
        rows = []
        for session, unit, course in result.all():
            rows.append(
                {
                    "session_type": self._value(session.session_type),
                    "canonical_phase": session.canonical_phase,
                    "course_id": (course.canonical_course_id or course.slug) if course else None,
                    "unit_title": unit.title if unit else None,
                    "total_questions": session.total_questions,
                    "correct_count": session.correct_count,
                    "score_percent": session.score_percent,
                    "completed_at": self._iso(session.completed_at),
                    "started_at": self._iso(session.started_at),
                }
            )
        return rows

    async def _quiz_history_analysis(self, user_id: UUID, course_ids: list[str]) -> dict[str, Any]:
        item_filters = self._canonical_course_id_filters(course_ids, QuestionBankItem.course_id)
        interaction_stmt = (
            select(Interaction, Session, QuestionBankItem, ConceptKP, CanonicalUnit)
            .join(Session, Interaction.session_id == Session.id)
            .join(QuestionBankItem, Interaction.canonical_item_id == QuestionBankItem.item_id)
            .outerjoin(ConceptKP, QuestionBankItem.primary_kp_id == ConceptKP.kp_id)
            .outerjoin(CanonicalUnit, QuestionBankItem.unit_id == CanonicalUnit.unit_id)
            .where(Interaction.user_id == user_id)
            .order_by(Interaction.timestamp.desc())
            .limit(300)
        )
        if item_filters:
            interaction_stmt = interaction_stmt.where(or_(*item_filters))
        interaction_result = await self.session.execute(interaction_stmt)

        session_stmt = (
            select(Session, LearningUnit, Course)
            .outerjoin(LearningUnit, Session.canonical_unit_id == LearningUnit.id)
            .outerjoin(Course, LearningUnit.course_id == Course.id)
            .where(Session.user_id == user_id)
            .order_by(Session.started_at.desc())
            .limit(12)
        )
        course_filters = self._course_filters(course_ids)
        if course_filters:
            session_stmt = session_stmt.where(or_(*course_filters))
        session_result = await self.session.execute(session_stmt)

        return self._quiz_history_analysis_payload(
            interaction_result.all(),
            session_result.all(),
        )

    @classmethod
    def _quiz_history_analysis_payload(
        cls,
        interaction_rows: list[Any],
        session_rows: list[Any],
    ) -> dict[str, Any]:
        total_answered = len(interaction_rows)
        correct_count = sum(1 for row in interaction_rows if bool(row[0].is_correct))
        accuracy_percent = (
            round(correct_count * 100.0 / total_answered, 1) if total_answered else None
        )
        kp_buckets: dict[str, dict[str, Any]] = {}
        unit_buckets: dict[str, dict[str, Any]] = {}
        course_ids: set[str] = set()

        for interaction, _session, item, concept, canonical_unit in interaction_rows:
            is_correct = bool(interaction.is_correct)
            course_id = getattr(item, "course_id", None)
            if course_id:
                course_ids.add(str(course_id))

            kp_id = str(getattr(item, "primary_kp_id", None) or "unknown")
            kp_bucket = kp_buckets.setdefault(
                kp_id,
                {
                    "kp_id": kp_id,
                    "name": getattr(concept, "name", None) or kp_id,
                    "answered_count": 0,
                    "incorrect_count": 0,
                },
            )
            kp_bucket["answered_count"] += 1
            if not is_correct:
                kp_bucket["incorrect_count"] += 1

            unit_id = str(getattr(item, "unit_id", None) or "unknown")
            unit_bucket = unit_buckets.setdefault(
                unit_id,
                {
                    "unit_id": unit_id,
                    "unit_title": getattr(canonical_unit, "unit_name", None) or unit_id,
                    "course_id": course_id,
                    "answered_count": 0,
                    "incorrect_count": 0,
                },
            )
            unit_bucket["answered_count"] += 1
            if not is_correct:
                unit_bucket["incorrect_count"] += 1

        recent_scores = cls._recent_quiz_session_scores(session_rows)
        return {
            "total_answered": total_answered,
            "correct_count": correct_count,
            "accuracy_percent": accuracy_percent,
            "weakest_quiz_kps": cls._rank_quiz_error_buckets(kp_buckets.values()),
            "weakest_quiz_units": cls._rank_quiz_error_buckets(unit_buckets.values()),
            "recent_session_scores": recent_scores,
            "trend": cls._quiz_score_trend(recent_scores),
            "data_window": {
                "interaction_limit": 300,
                "session_limit": 12,
                "course_ids": sorted(course_ids),
            },
        }

    @classmethod
    def _rank_quiz_error_buckets(cls, buckets: Any) -> list[dict[str, Any]]:
        ranked = []
        for bucket in buckets:
            answered = int(bucket["answered_count"])
            incorrect = int(bucket["incorrect_count"])
            if incorrect <= 0:
                continue
            ranked.append(
                {
                    **bucket,
                    "accuracy_percent": round((answered - incorrect) * 100.0 / answered, 1)
                    if answered
                    else None,
                    "incorrect_rate": round(incorrect / answered, 3) if answered else None,
                }
            )
        return sorted(
            ranked,
            key=lambda bucket: (
                -int(bucket["incorrect_count"]),
                float(bucket["accuracy_percent"] or 0),
                str(bucket.get("kp_id") or bucket.get("unit_id") or ""),
            ),
        )[:8]

    @classmethod
    def _recent_quiz_session_scores(cls, rows: list[Any]) -> list[dict[str, Any]]:
        scores = []
        for session, unit, course in rows:
            scores.append(
                {
                    "session_type": cls._value(session.session_type),
                    "canonical_phase": session.canonical_phase,
                    "course_id": (course.canonical_course_id or course.slug) if course else None,
                    "unit_title": unit.title if unit else None,
                    "total_questions": session.total_questions,
                    "correct_count": session.correct_count,
                    "score_percent": session.score_percent,
                    "completed_at": cls._iso(session.completed_at),
                    "started_at": cls._iso(session.started_at),
                }
            )
        return scores

    @staticmethod
    def _quiz_score_trend(scores: list[dict[str, Any]]) -> dict[str, Any]:
        numeric_scores = [
            float(score["score_percent"])
            for score in scores
            if score.get("score_percent") is not None
        ]
        if len(numeric_scores) < 2:
            return {"direction": "insufficient_data", "latest_average": None, "previous_average": None}
        split = max(1, min(3, len(numeric_scores) // 2))
        latest = numeric_scores[:split]
        previous = numeric_scores[split : split * 2]
        if not previous:
            previous = numeric_scores[split:]
        latest_average = sum(latest) / len(latest)
        previous_average = sum(previous) / len(previous)
        delta = latest_average - previous_average
        if delta >= 5:
            direction = "improving"
        elif delta <= -5:
            direction = "declining"
        else:
            direction = "stable"
        return {
            "direction": direction,
            "latest_average": round(latest_average, 1),
            "previous_average": round(previous_average, 1),
            "delta": round(delta, 1),
        }

    async def _recent_placement_results(self, user_id: UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(PlacementAssessmentResult, LearningUnit, Course)
            .join(LearningUnit, PlacementAssessmentResult.topic_unit_id == LearningUnit.id)
            .join(Course, LearningUnit.course_id == Course.id)
            .where(PlacementAssessmentResult.user_id == user_id)
            .order_by(PlacementAssessmentResult.created_at.desc())
            .limit(6)
        )
        rows = []
        for placement, unit, course in result.all():
            rows.append(
                {
                    "course_id": course.canonical_course_id or course.slug,
                    "unit_title": unit.title,
                    "canonical_unit_id": unit.canonical_unit_id,
                    "score_pct": self._number(placement.score_pct),
                    "decision": placement.decision,
                    "user_choice": placement.user_choice,
                    "theta_estimate": self._number(placement.theta_estimate),
                    "created_at": self._iso(placement.created_at),
                }
            )
        return rows

    async def _waived_units(self, user_id: UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(WaivedUnit, LearningUnit, Course)
            .join(LearningUnit, WaivedUnit.learning_unit_id == LearningUnit.id)
            .join(Course, LearningUnit.course_id == Course.id)
            .where(WaivedUnit.user_id == user_id)
            .order_by(WaivedUnit.created_at.desc())
            .limit(8)
        )
        rows = []
        for waived, unit, course in result.all():
            rows.append(
                {
                    "course_id": course.canonical_course_id or course.slug,
                    "unit_title": unit.title,
                    "canonical_unit_id": unit.canonical_unit_id,
                    "mastery_lcb_at_waive": waived.mastery_lcb_at_waive,
                    "skip_quiz_score": waived.skip_quiz_score,
                    "created_at": self._iso(waived.created_at),
                }
            )
        return rows

    def _course_filters(self, course_ids: list[str]):
        if not course_ids:
            return []
        raw_ids = [str(course_id) for course_id in course_ids if str(course_id).strip()]
        lowered = [course_id.lower() for course_id in raw_ids]
        uuid_ids = []
        for course_id in raw_ids:
            try:
                uuid_ids.append(UUID(course_id))
            except ValueError:
                continue
        filters = [func.lower(Course.canonical_course_id).in_(lowered), func.lower(Course.slug).in_(lowered)]
        if uuid_ids:
            filters.append(Course.id.in_(uuid_ids))
        return filters

    @staticmethod
    def _canonical_course_id_filters(course_ids: list[str], column: Any):
        if not course_ids:
            return []
        lowered = [
            str(course_id).strip().lower()
            for course_id in course_ids
            if str(course_id).strip()
        ]
        return [func.lower(column).in_(lowered)] if lowered else []

    @staticmethod
    def _unit_payload(row) -> dict[str, Any] | None:
        if not row:
            return None
        unit, course, section = row[:3]
        progress = row[3] if len(row) > 3 else None
        return {
            "course_id": course.canonical_course_id or course.slug,
            "course_slug": course.slug,
            "section_title": section.title,
            "unit_title": unit.title,
            "unit_slug": unit.slug,
            "canonical_unit_id": unit.canonical_unit_id,
            "estimated_minutes": unit.estimated_minutes,
            "has_quiz_items": bool(getattr(unit, "has_quiz_items", False)),
            "status": AgentUserLearningContextService._value(progress.status)
            if progress
            else "not_started",
        }

    @staticmethod
    def _safe_context_kind(value: str | None) -> str:
        allowed = {
            "current_unit_state",
            "progress_summary",
            "weak_areas",
            "study_time_estimate",
            "planner_reasoning_context",
            "quiz_history_analysis",
            "general",
        }
        return value if value in allowed else "general"

    @staticmethod
    def _value(value: Any) -> str:
        return getattr(value, "value", str(value))

    @staticmethod
    def _number(value: Decimal | float | int | None) -> float | None:
        return float(value) if value is not None else None

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _value_from(value, key: str, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)
