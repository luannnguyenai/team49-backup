"""
services/history_service.py
-----------------------------
Business logic for the unified Learning History API.

get_history
-----------
1.  Build a base query joining Session → Topic (optional) and Module (optional)
    with filters: session_type, module_id, days back.
2.  Count total rows (for pagination).
3.  Fetch one page sorted by started_at DESC.
4.  Compute summary stats from ALL matching rows (not just the page).
5.  Return HistoryResponse.

get_session_detail
------------------
1.  Load Session, validate ownership.
2.  Load all Interactions + Questions for the session (ordered by sequence_position).
3.  Build bloom_breakdown, weak_kcs, misconceptions via mastery_evaluator helpers.
4.  Return SessionDetailResponse.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.content import (
    Module,
    Question,
    Topic,
)
from src.models.learning import (
    Interaction,
    Session,
    SessionType,
)
from src.schemas.history import (
    HistoryItem,
    HistoryResponse,
    HistorySummary,
    QuestionInteractionDetail,
    ScoreTrendPoint,
    SessionDetailResponse,
)
from src.exceptions import ConflictError, NotFoundError
from src.repositories.history_repo import HistoryRepository
from src.services.mastery_evaluator import (
    BloomLevel,
    QuestionResult,
    evaluate_topic,
)

# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------


async def get_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    session_type: SessionType | None = None,
    module_id: uuid.UUID | None = None,
    days: int | None = None,  # None = all time
    page: int = 1,
    page_size: int = 20,
) -> HistoryResponse:
    repo = HistoryRepository(db)

    # ── Base filter ────────────────────────────────────────────────────────
    filters = [Session.user_id == user_id]

    if session_type is not None:
        filters.append(Session.session_type == session_type)

    if module_id is not None:
        # For quiz / assessment filter by topic.module_id, for module_test by session.module_id
        from sqlalchemy import or_

        filters.append(
            or_(
                Session.module_id == module_id,
                Session.topic_id.in_(select(Topic.id).where(Topic.module_id == module_id)),
            )
        )

    if days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        filters.append(Session.started_at >= cutoff)

    # ── Count total ────────────────────────────────────────────────────────
    total = await repo.count_sessions(filters=filters)

    # ── Fetch page ─────────────────────────────────────────────────────────
    page_rows = await repo.fetch_history_page(
        filters=filters,
        page=page,
        page_size=page_size,
    )

    items: list[HistoryItem] = []
    for sess, topic_name, module_name in page_rows:
        items.append(_session_to_item(sess, topic_name, module_name))

    # ── Summary stats from ALL matching sessions ──────────────────────────
    summary = await _compute_summary(db, user_id, filters)

    return HistoryResponse(
        summary=summary,
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


def _session_to_item(
    sess: Session,
    topic_name: str | None,
    module_name: str | None,
) -> HistoryItem:
    duration: int | None = None
    if sess.completed_at and sess.started_at:
        delta = sess.completed_at - sess.started_at
        duration = max(0, int(delta.total_seconds()))

    # Determine display subject
    if sess.session_type == SessionType.module_test:
        subject = module_name or str(sess.module_id or "—")
    else:
        subject = topic_name or module_name or "—"

    return HistoryItem(
        session_id=sess.id,
        session_type=sess.session_type,
        started_at=sess.started_at,
        completed_at=sess.completed_at,
        duration_seconds=duration,
        subject=subject,
        topic_id=sess.topic_id,
        module_id=sess.module_id,
        score_percent=sess.score_percent,
        correct_count=sess.correct_count,
        total_questions=sess.total_questions,
    )


async def _compute_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    filters: list,
) -> HistorySummary:
    """Compute stats over ALL rows matching filters (ignores pagination)."""
    repo = HistoryRepository(db)

    sessions = await repo.fetch_sessions_for_summary(filters=filters)

    completed = [s for s in sessions if s.completed_at is not None]

    total_sessions = len(sessions)
    completed_sessions = len(completed)

    scores = [s.score_percent for s in completed if s.score_percent is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    total_study_seconds = 0
    for s in completed:
        if s.completed_at and s.started_at:
            total_study_seconds += max(0, int((s.completed_at - s.started_at).total_seconds()))

    # Score trend: last ≤ 20 completed sessions with a score
    trend_sessions = [s for s in completed if s.score_percent is not None][-20:]
    score_trend = [
        ScoreTrendPoint(
            started_at=s.started_at,
            score_percent=s.score_percent,  # type: ignore[arg-type]
        )
        for s in trend_sessions
    ]

    return HistorySummary(
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        avg_score=avg_score,
        total_study_seconds=total_study_seconds,
        score_trend=score_trend,
    )


# ---------------------------------------------------------------------------
# GET /api/history/{session_id}/detail
# ---------------------------------------------------------------------------


async def get_session_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> SessionDetailResponse:
    repo = HistoryRepository(db)

    # 1. Validate session ownership
    sess = await repo.get_owned_session(user_id=user_id, session_id=session_id)
    if sess is None:
        raise NotFoundError("Session not found.")
    if sess.completed_at is None:
        raise ConflictError("Session has not been completed yet.")

    # 2. Load interactions + questions
    rows = await repo.fetch_session_detail_rows(session_id)

    if not rows:
        return SessionDetailResponse(
            session_id=session_id,
            session_type=sess.session_type,
            bloom_breakdown={},
            weak_kcs=[],
            misconceptions=[],
            questions=[],
        )

    # 3. Build QuestionResult list for the evaluator.
    # Canonical-only interactions do not have legacy Bloom/KC/misconception
    # fields, so they are still shown in detail but skipped for legacy
    # bloom/weak-KC aggregation.
    qr_list: list[QuestionResult] = [
        QuestionResult(
            question_id=q.id,
            topic_id=q.topic_id,
            bloom_level=q.bloom_level,
            correct_answer=q.correct_answer,
            selected_answer=inter.selected_answer,
            is_correct=inter.is_correct,
            kc_ids=q.kc_ids or [],
            misconception_a_id=q.misconception_a_id,
            misconception_b_id=q.misconception_b_id,
            misconception_c_id=q.misconception_c_id,
            misconception_d_id=q.misconception_d_id,
        )
        for inter, q, _, _ in rows
        if q is not None
    ]

    # 4. Group by topic and evaluate each
    by_topic: dict[uuid.UUID, list[QuestionResult]] = {}
    for qr in qr_list:
        by_topic.setdefault(qr.topic_id, []).append(qr)

    # Aggregate bloom across all topics
    bloom_correct: dict[str, int] = {b.value: 0 for b in BloomLevel}
    bloom_total: dict[str, int] = {b.value: 0 for b in BloomLevel}
    all_weak_kc_ids: set[str] = set()
    all_misconceptions: set[str] = set()

    for tid, qrs in by_topic.items():
        ev = evaluate_topic(qrs)
        for level_str, fraction in ev.bloom_breakdown.items():
            c, t = fraction.split("/")
            bloom_correct[level_str] = bloom_correct.get(level_str, 0) + int(c)
            bloom_total[level_str] = bloom_total.get(level_str, 0) + int(t)
        all_weak_kc_ids.update(ev.weak_kc_ids)
        all_misconceptions.update(ev.misconceptions_detected)

    bloom_breakdown: dict[str, str] = {
        k: f"{bloom_correct[k]}/{bloom_total[k]}" for k in bloom_correct if bloom_total[k] > 0
    }

    # 5. Resolve KC names
    weak_kc_names = await _resolve_kc_names(db, list(all_weak_kc_ids))

    # 6. Build per-question detail list
    questions_detail = [
        _interaction_detail_from_row(inter, q, canonical_item, topic_name)
        for inter, q, canonical_item, topic_name in rows
    ]

    return SessionDetailResponse(
        session_id=session_id,
        session_type=sess.session_type,
        bloom_breakdown=bloom_breakdown,
        weak_kcs=weak_kc_names,
        misconceptions=list(all_misconceptions),
        questions=questions_detail,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _resolve_kc_names(
    db: AsyncSession,
    kc_id_strs: list[str],
) -> list[str]:
    if not kc_id_strs:
        return []
    valid: list[uuid.UUID] = []
    for s in kc_id_strs:
        try:
            valid.append(uuid.UUID(s))
        except ValueError:
            pass
    if not valid:
        return kc_id_strs
    repo = HistoryRepository(db)
    name_map = await repo.resolve_kc_names(valid)
    return [name_map.get(s, s) for s in kc_id_strs]


def _answer_index_to_letter(index: int | None) -> str:
    if index is None:
        return ""
    return {0: "A", 1: "B", 2: "C", 3: "D"}.get(index, "")


def _interaction_detail_from_row(
    inter: Interaction,
    question: Question | None,
    canonical_item,
    topic_name: str | None,
) -> QuestionInteractionDetail:
    if question is not None:
        return QuestionInteractionDetail(
            question_id=question.id,
            canonical_item_id=inter.canonical_item_id,
            sequence_position=inter.sequence_position,
            topic_name=topic_name or str(question.topic_id),
            stem_text=question.stem_text,
            bloom_level=question.bloom_level.value,
            difficulty_bucket=question.difficulty_bucket.value,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            selected_answer=(inter.selected_answer.value if inter.selected_answer else None),
            correct_answer=question.correct_answer.value,
            is_correct=inter.is_correct,
            response_time_ms=inter.response_time_ms,
            explanation_text=question.explanation_text,
        )

    if canonical_item is None:
        return QuestionInteractionDetail(
            question_id=None,
            canonical_item_id=inter.canonical_item_id,
            sequence_position=inter.sequence_position,
            topic_name="canonical",
            stem_text="",
            bloom_level="",
            difficulty_bucket="",
            option_a="",
            option_b="",
            option_c="",
            option_d="",
            selected_answer=(inter.selected_answer.value if inter.selected_answer else None),
            correct_answer="",
            is_correct=inter.is_correct,
            response_time_ms=inter.response_time_ms,
            explanation_text=None,
        )

    choices = list(canonical_item.choices or [])
    padded_choices = (choices + ["", "", "", ""])[:4]
    return QuestionInteractionDetail(
        question_id=None,
        canonical_item_id=canonical_item.item_id,
        sequence_position=inter.sequence_position,
        topic_name=canonical_item.unit_id,
        stem_text=canonical_item.question,
        bloom_level=canonical_item.question_intent or "",
        difficulty_bucket=canonical_item.difficulty or "",
        option_a=padded_choices[0],
        option_b=padded_choices[1],
        option_c=padded_choices[2],
        option_d=padded_choices[3],
        selected_answer=(inter.selected_answer.value if inter.selected_answer else None),
        correct_answer=_answer_index_to_letter(canonical_item.answer_index),
        is_correct=inter.is_correct,
        response_time_ms=inter.response_time_ms,
        explanation_text=canonical_item.explanation,
    )
