"""
services/history_service.py
-----------------------------
Business logic for the unified Learning History API.

get_history
-----------
1.  Build a base Session query with filters: session_type, module_id, days back.
2.  Count total rows (for pagination).
3.  Fetch one page sorted by started_at DESC.
4.  Compute summary stats from ALL matching rows (not just the page).
5.  Return HistoryResponse.

get_session_detail
------------------
1.  Load Session, validate ownership.
2.  Load all Interactions + canonical question_bank items for the session.
3.  Render canonical per-question details.
4.  Return SessionDetailResponse.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

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
        filters.append(Session.module_id == module_id)

    if days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        filters.append(Session.started_at >= cutoff)

    # ── Count total ────────────────────────────────────────────────────────
    total = await repo.count_sessions(filters=filters)

    # ── Fetch page ─────────────────────────────────────────────────────────
    page_rows = await repo.fetch_history_page_canonical_only(
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

    # 2. Load interactions + canonical question_bank items
    rows = await repo.fetch_session_detail_rows_canonical_only(session_id)

    if not rows:
        return SessionDetailResponse(
            session_id=session_id,
            session_type=sess.session_type,
            bloom_breakdown={},
            weak_kcs=[],
            misconceptions=[],
            questions=[],
        )

    # 3. Build per-question detail list
    questions_detail = [
        _interaction_detail_from_row(inter, q, canonical_item, topic_name)
        for inter, q, canonical_item, topic_name in rows
    ]

    return SessionDetailResponse(
        session_id=session_id,
        session_type=sess.session_type,
        bloom_breakdown={},
        weak_kcs=[],
        misconceptions=[],
        questions=questions_detail,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _answer_index_to_letter(index: int | None) -> str:
    if index is None:
        return ""
    return {0: "A", 1: "B", 2: "C", 3: "D"}.get(index, "")


def _interaction_detail_from_row(
    inter: Interaction,
    question,
    canonical_item,
    topic_name: str | None,
) -> QuestionInteractionDetail:
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
