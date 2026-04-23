"""
services/module_test_service.py
--------------------------------
Business logic for the Module Test System.

Flow
----
1.  start_module_test
    - Validate module exists.
    - Load all topics (ordered by order_index).
    - Guard: every topic must have ≥ 1 completed quiz session for this user.
    - Per topic select 5 questions: 2 Easy · 1 Medium · 2 Hard
      Filter: usage_context @> '["module_test"]'
      Priority tiers (same as quiz): never-answered → ever-wrong → always-correct.
    - Create Session(type=module_test, module_id=module_id, topic_id=None).
    - Return session_id + questions grouped by topic.

2.  submit_module_test
    - Validate session (module_test, owned by user, not already completed).
    - Validate each submitted question belongs to the session's module.
    - Persist all Interactions in one flush.
    - Grade:
        per-topic: correct/total, score_percent, bloom_max, weak KCs, misconceptions
        total: sum across all topics; passed = total_score_percent ≥ 70 %
    - If PASS:
        * mastery = max(current_mastery, topic_score_percent) for each topic
        * return next_module (module with the lowest order_index > current)
    - If FAIL:
        * weak_topics = per_topic results where score_percent < 60 %
        * Upsert LearningPath(action=remediate) for each weak topic (skip if one
          already exists and is not completed/skipped)
    - Finalise session (completed_at, score_percent).
    - Return ModuleTestResultResponse.

3.  get_module_test_results
    - Validate session (owned by user, completed).
    - Reload interactions + questions.
    - Re-compute result without any DB mutations.
    - Return ModuleTestResultResponse.

Question-slot distribution
--------------------------
  2 Easy  +  1 Medium  +  2 Hard  =  5 questions per topic

Pass thresholds
---------------
  Total PASS  : total_score_percent ≥ 70 %
  Topic FAIL  : topic score_percent  < 60 % → flagged as weak → remediation
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from src.exceptions import ConflictError, NotFoundError, ValidationError

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.canonical import ItemKPMap, QuestionBankItem
from src.models.content import (
    BloomLevel,
    DifficultyBucket,
    KnowledgeComponent,
    Module,
    Question,
    QuestionStatus,
    Topic,
)
from src.models.course import CourseSection, LearningUnit
from src.models.learning import (
    Interaction,
    LearningPath,
    MasteryScore,
    PathAction,
    PathStatus,
    SelectedAnswer,
    Session,
    SessionType,
)
from src.schemas.module_test import (
    ModuleTestResultResponse,
    ModuleTestStartResponse,
    ModuleTestSubmitRequest,
    NextModuleInfo,
    QuestionForModuleTest,
    ReviewTopicSuggestion,
    TopicQuestionsGroup,
    TopicTestResult,
    WrongAnswerDetail,
)
from src.services.mastery_evaluator import (
    classify_mastery,
    update_bloom_max,
)
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.services.canonical_assessor_compat import (
    answer_index_to_correct_answer,
    canonical_item_to_module_test_question,
    canonical_question_uuid,
    selected_answer_to_index,
)
from src.services.canonical_mastery_service import update_kp_mastery_from_item
from src.services.canonical_question_selector import CanonicalQuestionSelector

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Questions per topic: 2 Easy · 1 Medium · 2 Hard
_MODULE_TEST_SLOTS: list[tuple[DifficultyBucket, int]] = [
    (DifficultyBucket.easy, 2),
    (DifficultyBucket.medium, 1),
    (DifficultyBucket.hard, 2),
]

PASS_THRESHOLD: float = 70.0  # total_score_percent ≥ 70 → PASS
WEAK_THRESHOLD: float = 60.0  # topic score_percent  < 60 → weak topic


def _ensure_legacy_module_test_question_reads_allowed() -> None:
    if not settings.allow_legacy_question_reads:
        raise ValidationError(
            "Legacy module-test question reads are disabled. Use canonical question_bank module-test flow."
        )


def _ensure_legacy_module_test_mutations_allowed() -> None:
    if not settings.allow_legacy_mastery_writes:
        raise ValidationError(
            "Legacy module-test mastery writes are disabled. Use learner_mastery_kp canonical updates."
        )
    if not settings.allow_legacy_planner_writes:
        raise ValidationError(
            "Legacy module-test learning_path writes are disabled. Use canonical planner audit/output."
        )


# ===========================================================================
# POST /api/module-test/start
# ===========================================================================


async def start_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    module_id: uuid.UUID,
) -> ModuleTestStartResponse:
    if not settings.allow_legacy_question_reads:
        return await _start_canonical_module_test(db, user_id, module_id)

    _ensure_legacy_module_test_question_reads_allowed()

    # 1. Validate module ──────────────────────────────────────────────────────
    module = await _get_module_or_404(db, module_id)

    # 2. Load topics (ordered) ────────────────────────────────────────────────
    topics_result = await db.execute(
        select(Topic).where(Topic.module_id == module_id).order_by(Topic.order_index)
    )
    topics: list[Topic] = topics_result.scalars().all()

    if not topics:
        raise ValidationError(f"Module '{module.name}' không có topic nào.")

    # 3. Validate completed quizzes for every topic ───────────────────────────
    incomplete: list[str] = []
    for topic in topics:
        check = await db.execute(
            select(Session.id)
            .where(
                Session.user_id == user_id,
                Session.topic_id == topic.id,
                Session.session_type == SessionType.quiz,
                Session.completed_at.isnot(None),
            )
            .limit(1)
        )
        if check.scalar_one_or_none() is None:
            incomplete.append(topic.name)

    if incomplete:
        raise ValidationError((
                "Bạn chưa hoàn thành quiz cho các topic sau: "
                + ", ".join(f"'{t}'" for t in incomplete)
                + ". Hãy hoàn thành quiz tất cả topics trước khi thi module test."
            ))

    # 4. Select 5 questions per topic ─────────────────────────────────────────
    topic_groups: list[TopicQuestionsGroup] = []
    total_question_count = 0

    for topic in topics:
        prior = await _prior_topic_interactions(db, user_id, topic.id)
        ever_wrong: set[uuid.UUID] = {qid for qid, w in prior.items() if w}
        always_correct: set[uuid.UUID] = {qid for qid, w in prior.items() if not w}
        answered_ids: set[uuid.UUID] = set(prior.keys())

        selected: list[Question] = []
        selected_ids: set[uuid.UUID] = set()

        for difficulty, target_count in _MODULE_TEST_SLOTS:
            pool = await _get_questions_for_bucket(db, topic.id, difficulty)
            pool = [q for q in pool if q.id not in selected_ids]

            tier1 = [q for q in pool if q.id not in answered_ids]
            tier2 = [q for q in pool if q.id in ever_wrong]
            tier3 = [q for q in pool if q.id in always_correct]

            chosen = _sample_with_priority([tier1, tier2, tier3], target_count)
            selected.extend(chosen)
            selected_ids.update(q.id for q in chosen)

        if not selected:
            raise ValidationError((
                    f"Không tìm thấy câu hỏi module_test cho topic '{topic.name}'. "
                    'Hãy seed question bank với usage_context=["module_test"].'
                ))

        random.shuffle(selected)
        total_question_count += len(selected)
        topic_groups.append(
            TopicQuestionsGroup(
                topic_id=topic.id,
                topic_name=topic.name,
                questions=[QuestionForModuleTest.model_validate(q) for q in selected],
            )
        )

    # 5. Create Session ────────────────────────────────────────────────────────
    session = Session(
        user_id=user_id,
        session_type=SessionType.module_test,
        topic_id=None,
        module_id=module_id,
        total_questions=total_question_count,
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return ModuleTestStartResponse(
        session_id=session.id,
        module_id=module_id,
        module_name=module.name,
        total_topics=len(topics),
        total_questions=total_question_count,
        topics=topic_groups,
    )


# ===========================================================================
# POST /api/module-test/{session_id}/submit
# ===========================================================================


async def submit_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    req: ModuleTestSubmitRequest,
) -> ModuleTestResultResponse:
    # 1. Validate session ──────────────────────────────────────────────────────
    session = await _get_module_test_session(db, user_id, session_id)
    if session.canonical_section_id is not None:
        return await _submit_canonical_module_test(db, user_id, session, req)

    _ensure_legacy_module_test_question_reads_allowed()
    _ensure_legacy_module_test_mutations_allowed()
    if session.completed_at is not None:
        raise ConflictError("Module test đã được nộp trước đó.")

    # 2. Load module + topics ──────────────────────────────────────────────────
    module = await _get_module_or_404(db, session.module_id)
    topics_result = await db.execute(
        select(Topic).where(Topic.module_id == session.module_id).order_by(Topic.order_index)
    )
    topics: list[Topic] = topics_result.scalars().all()
    topic_by_id: dict[uuid.UUID, Topic] = {t.id: t for t in topics}

    # 3. Load questions for all submitted answer IDs ───────────────────────────
    answer_ids = list({a.question_id for a in req.answers})
    questions_result = await db.execute(select(Question).where(Question.id.in_(answer_ids)))
    question_by_id: dict[uuid.UUID, Question] = {q.id: q for q in questions_result.scalars().all()}

    # Validate module ownership of every question
    for q in question_by_id.values():
        if q.module_id != session.module_id:
            raise ValidationError(f"Question {q.id} không thuộc module này.")

    # 4. Guard: no duplicate answers in same session ───────────────────────────
    existing_qs_result = await db.execute(
        select(Interaction.question_id).where(Interaction.session_id == session_id)
    )
    already_answered: set[uuid.UUID] = {r[0] for r in existing_qs_result}
    if already_answered:
        raise ConflictError("Module test đã có câu trả lời. Không thể nộp lại.")

    # 5. Determine global sequence base ────────────────────────────────────────
    max_global_result = await db.execute(
        select(func.max(Interaction.global_sequence_position)).where(Interaction.user_id == user_id)
    )
    global_base: int = max_global_result.scalar() or 0

    # 6. Persist all interactions ──────────────────────────────────────────────
    now = datetime.now(UTC)
    for i, answer in enumerate(req.answers):
        q = question_by_id.get(answer.question_id)
        if q is None:
            continue  # skip unknown question IDs silently
        is_correct = q.correct_answer.value == answer.selected_answer.value
        db.add(
            Interaction(
                user_id=user_id,
                session_id=session_id,
                question_id=answer.question_id,
                sequence_position=i + 1,
                global_sequence_position=global_base + i + 1,
                selected_answer=SelectedAnswer(answer.selected_answer.value),
                is_correct=is_correct,
                response_time_ms=answer.response_time_ms,
                changed_answer=False,
                hint_used=False,
                explanation_viewed=bool(q.explanation_text),
                timestamp=now,
            )
        )
    await db.flush()

    # 7. Reload interactions with joined Question data ─────────────────────────
    rows_result = await db.execute(
        select(Interaction, Question)
        .join(Question, Interaction.question_id == Question.id)
        .where(Interaction.session_id == session_id)
        .order_by(Interaction.sequence_position)
    )
    rows = rows_result.all()

    if not rows:
        raise ValidationError("Không có câu trả lời hợp lệ nào.")

    # 8. Compute result ────────────────────────────────────────────────────────
    result = await _build_result(db, session, rows, topic_by_id, module)

    # 9. Apply DB mutations ────────────────────────────────────────────────────
    if result.passed:
        await _update_mastery_on_pass(db, user_id, rows, topic_by_id, now)
    else:
        await _upsert_remediate_entries(db, user_id, result.recommended_review_topics, now)

    # 10. Finalise session ─────────────────────────────────────────────────────
    total_correct = sum(1 for inter, _ in rows if inter.is_correct)
    session.completed_at = now
    session.total_questions = len(rows)
    session.correct_count = total_correct
    session.score_percent = result.total_score_percent
    db.add(session)
    await db.flush()

    return result


# ===========================================================================
# GET /api/module-test/{session_id}/results
# ===========================================================================


async def get_module_test_results(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ModuleTestResultResponse:
    _ensure_legacy_module_test_question_reads_allowed()

    # 1. Validate session ──────────────────────────────────────────────────────
    session = await _get_module_test_session(db, user_id, session_id)
    if session.canonical_section_id is not None:
        if session.completed_at is None:
            raise ConflictError("Module test chưa được nộp.")
        return await _build_canonical_module_test_result(db, user_id, session, mutate=False)

    if session.completed_at is None:
        raise ConflictError("Module test chưa được nộp.")

    # 2. Load module + topics ──────────────────────────────────────────────────
    module = await _get_module_or_404(db, session.module_id)
    topics_result = await db.execute(
        select(Topic).where(Topic.module_id == session.module_id).order_by(Topic.order_index)
    )
    topic_by_id: dict[uuid.UUID, Topic] = {t.id: t for t in topics_result.scalars().all()}

    # 3. Reload interactions ───────────────────────────────────────────────────
    rows_result = await db.execute(
        select(Interaction, Question)
        .join(Question, Interaction.question_id == Question.id)
        .where(Interaction.session_id == session_id)
        .order_by(Interaction.sequence_position)
    )
    rows = rows_result.all()

    # 4. Recompute result (read-only — no DB mutations) ────────────────────────
    return await _build_result(db, session, rows, topic_by_id, module)


# ===========================================================================
# Shared computation kernel
# ===========================================================================


async def _build_result(
    db: AsyncSession,
    session: Session,
    rows: list,  # list[(Interaction, Question)]
    topic_by_id: dict[uuid.UUID, Topic],
    module: Module,
) -> ModuleTestResultResponse:
    """
    Pure computation: grade a completed (or just-submitted) module test.
    Does NOT mutate any DB state.
    """

    # Group rows by topic, preserving question order
    per_topic_rows: dict[uuid.UUID, list[tuple[Interaction, Question]]] = {}
    for interaction, question in rows:
        per_topic_rows.setdefault(question.topic_id, []).append((interaction, question))

    # Sort topic IDs by the topic's order_index (unknown topics go last)
    sorted_topic_ids = sorted(
        per_topic_rows.keys(),
        key=lambda tid: topic_by_id[tid].order_index if tid in topic_by_id else 999,
    )

    # ── Per-topic grading ────────────────────────────────────────────────────
    per_topic_results: list[TopicTestResult] = []
    review_suggestions: list[ReviewTopicSuggestion] = []

    for topic_id in sorted_topic_ids:
        topic_rows = per_topic_rows[topic_id]
        topic = topic_by_id.get(topic_id)
        topic_name = topic.name if topic else str(topic_id)

        correct = sum(1 for inter, _ in topic_rows if inter.is_correct)
        total = len(topic_rows)
        score_pct = round(correct / total * 100, 1) if total else 0.0

        # Bloom max achieved for this topic
        bloom_max: str | None = None
        for inter, q in topic_rows:
            if inter.is_correct:
                bloom_max = update_bloom_max(bloom_max, q.bloom_level)

        # Weak KCs + misconceptions from wrong answers
        weak_kc_ids: set[str] = set()
        misconceptions: set[str] = set()
        for inter, q in topic_rows:
            if inter.is_correct:
                continue
            for kc_id in q.kc_ids or []:
                if kc_id:
                    weak_kc_ids.add(str(kc_id))
            if inter.selected_answer is not None:
                misc_id = _misc_id_for_answer(inter.selected_answer, q)
                if misc_id:
                    misconceptions.add(misc_id)

        weak_kc_names = await _resolve_kc_names(db, list(weak_kc_ids))
        verdict: str = "pass" if score_pct >= WEAK_THRESHOLD else "fail"

        per_topic_results.append(
            TopicTestResult(
                topic_id=topic_id,
                topic_name=topic_name,
                score=f"{correct}/{total}",
                score_percent=score_pct,
                bloom_max=bloom_max,
                verdict=verdict,
                weak_kcs=weak_kc_names,
            )
        )

        if verdict == "fail":
            est_hours = _review_hours(topic)
            review_suggestions.append(
                ReviewTopicSuggestion(
                    topic_id=topic_id,
                    topic_name=topic_name,
                    weak_kcs=weak_kc_names,
                    misconceptions=list(misconceptions),
                    estimated_review_hours=est_hours,
                )
            )

    # ── Overall score ────────────────────────────────────────────────────────
    total_correct = sum(1 for inter, _ in rows if inter.is_correct)
    total_qs = len(rows)
    total_score_pct = round(total_correct / total_qs * 100, 1) if total_qs else 0.0
    passed = total_score_pct >= PASS_THRESHOLD

    total_review_hours = round(sum(s.estimated_review_hours for s in review_suggestions), 1)

    # ── Next module (only when passed) ───────────────────────────────────────
    next_module_info: NextModuleInfo | None = None
    if passed:
        next_mod_result = await db.execute(
            select(Module)
            .where(Module.order_index > module.order_index)
            .order_by(Module.order_index)
            .limit(1)
        )
        next_mod = next_mod_result.scalar_one_or_none()
        if next_mod is not None:
            next_module_info = NextModuleInfo(
                module_id=next_mod.id,
                module_name=next_mod.name,
            )

    # ── Wrong-answer details (for review UI) ─────────────────────────────────
    wrong_answers: list[WrongAnswerDetail] = []
    for interaction, question in rows:
        if interaction.is_correct:
            continue
        if interaction.selected_answer is None:
            continue
        t = topic_by_id.get(question.topic_id)
        wrong_answers.append(
            WrongAnswerDetail(
                question_id=question.id,
                topic_id=question.topic_id,
                topic_name=t.name if t else str(question.topic_id),
                stem_text=question.stem_text,
                option_a=question.option_a,
                option_b=question.option_b,
                option_c=question.option_c,
                option_d=question.option_d,
                selected_answer=interaction.selected_answer,
                correct_answer=question.correct_answer.value,
                explanation_text=question.explanation_text,
            )
        )

    return ModuleTestResultResponse(
        session_id=session.id,
        module_id=module.id,
        module_name=module.name,
        total_score_percent=total_score_pct,
        passed=passed,
        per_topic=per_topic_results,
        recommended_review_topics=review_suggestions,
        estimated_review_hours=total_review_hours,
        next_module=next_module_info,
        wrong_answers=wrong_answers,
    )


# ===========================================================================
# Canonical compatibility helpers
# ===========================================================================


async def _start_canonical_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    section_id: uuid.UUID,
) -> ModuleTestStartResponse:
    section = await _get_canonical_section_or_404(db, section_id)
    units = await _get_canonical_units_for_section(db, section.id)
    if not units:
        raise ValidationError(f"Module '{section.title}' không có canonical learning unit nào.")

    incomplete = await _canonical_units_without_completed_quiz(db, user_id, units)
    if incomplete:
        raise ValidationError(
            "Bạn chưa hoàn thành quiz cho các learning unit sau: "
            + ", ".join(f"'{unit.title}'" for unit in incomplete)
            + ". Hãy hoàn thành quiz tất cả units trước khi thi module test."
        )

    selector = CanonicalQuestionSelector(CanonicalQuestionRepository(db))
    topic_groups: list[TopicQuestionsGroup] = []
    total_question_count = 0
    for unit in units:
        if not unit.canonical_unit_id:
            continue
        items = await selector.select_for_phase(
            phase="final_quiz",
            canonical_unit_ids=[unit.canonical_unit_id],
            count=5,
        )
        if not items:
            raise ValidationError(f"Không tìm thấy câu hỏi final_quiz cho learning unit '{unit.title}'.")
        total_question_count += len(items)
        topic_groups.append(
            TopicQuestionsGroup(
                topic_id=unit.id,
                topic_name=unit.title,
                questions=[
                    canonical_item_to_module_test_question(item, topic_id=unit.id)
                    for item in items
                ],
            )
        )

    session = Session(
        user_id=user_id,
        session_type=SessionType.module_test,
        topic_id=None,
        module_id=None,
        canonical_section_id=section.id,
        canonical_phase="final_quiz",
        total_questions=total_question_count,
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return ModuleTestStartResponse(
        session_id=session.id,
        module_id=section.id,
        module_name=section.title,
        total_topics=len(topic_groups),
        total_questions=total_question_count,
        topics=topic_groups,
    )


async def _submit_canonical_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
    req: ModuleTestSubmitRequest,
) -> ModuleTestResultResponse:
    if session.completed_at is not None:
        raise ConflictError("Module test đã được nộp trước đó.")

    section = await _get_canonical_section_or_404(db, session.canonical_section_id)
    units = await _get_canonical_units_for_section(db, section.id)
    item_by_question_id = await _canonical_item_lookup_for_units(db, units)

    seen: set[str] = set()
    for index, answer in enumerate(req.answers, start=1):
        item = item_by_question_id.get(answer.question_id)
        if item is None:
            raise ValidationError("Question does not belong to this canonical module test.")
        if item.item_id in seen:
            raise ConflictError("Duplicate question in module-test submission.")
        seen.add(item.item_id)
        is_correct = item.answer_index == selected_answer_to_index(answer.selected_answer.value)
        db.add(
            Interaction(
                user_id=user_id,
                session_id=session.id,
                question_id=None,
                canonical_item_id=item.item_id,
                sequence_position=index,
                global_sequence_position=index,
                selected_answer=SelectedAnswer(answer.selected_answer.value),
                is_correct=is_correct,
                response_time_ms=answer.response_time_ms,
                changed_answer=False,
                hint_used=False,
                explanation_viewed=bool(item.explanation),
                timestamp=datetime.now(UTC),
            )
        )

    return await _build_canonical_module_test_result(db, user_id, session, mutate=True)


async def _build_canonical_module_test_result(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
    *,
    mutate: bool,
) -> ModuleTestResultResponse:
    section = await _get_canonical_section_or_404(db, session.canonical_section_id)
    units = await _get_canonical_units_for_section(db, section.id)
    unit_by_canonical_id = {unit.canonical_unit_id: unit for unit in units if unit.canonical_unit_id}
    rows_result = await db.execute(
        select(Interaction, QuestionBankItem)
        .join(QuestionBankItem, Interaction.canonical_item_id == QuestionBankItem.item_id)
        .where(Interaction.session_id == session.id)
        .order_by(Interaction.sequence_position)
    )
    rows = rows_result.all()
    if not rows:
        raise ValidationError("Module test submission không có câu trả lời nào.")

    per_unit_rows: dict[uuid.UUID, list[tuple[Interaction, QuestionBankItem]]] = {}
    for interaction, item in rows:
        unit = unit_by_canonical_id.get(item.unit_id)
        if unit is not None:
            per_unit_rows.setdefault(unit.id, []).append((interaction, item))

    total = len(rows)
    correct = sum(1 for interaction, _ in rows if interaction.is_correct)
    total_score_pct = round(correct / total * 100, 1) if total else 0.0
    passed = total_score_pct >= PASS_THRESHOLD
    per_topic: list[TopicTestResult] = []
    review_suggestions: list[ReviewTopicSuggestion] = []
    wrong_answers: list[WrongAnswerDetail] = []

    for unit in units:
        unit_rows = per_unit_rows.get(unit.id, [])
        if not unit_rows:
            continue
        unit_total = len(unit_rows)
        unit_correct = sum(1 for interaction, _ in unit_rows if interaction.is_correct)
        unit_pct = round(unit_correct / unit_total * 100, 1)
        wrong_item_ids = [item.item_id for interaction, item in unit_rows if not interaction.is_correct]
        weak_kcs = await _canonical_weak_kp_ids(db, wrong_item_ids)
        per_topic.append(
            TopicTestResult(
                topic_id=unit.id,
                topic_name=unit.title,
                score=f"{unit_correct}/{unit_total}",
                score_percent=unit_pct,
                bloom_max=None,
                verdict="pass" if unit_pct >= WEAK_THRESHOLD else "fail",
                weak_kcs=weak_kcs,
            )
        )
        if unit_pct < WEAK_THRESHOLD:
            review_suggestions.append(
                ReviewTopicSuggestion(
                    topic_id=unit.id,
                    topic_name=unit.title,
                    weak_kcs=weak_kcs,
                    misconceptions=[],
                    estimated_review_hours=_unit_review_hours(unit),
                )
            )
        for interaction, item in unit_rows:
            if interaction.is_correct or interaction.selected_answer is None:
                continue
            question = canonical_item_to_module_test_question(item, topic_id=unit.id)
            wrong_answers.append(
                WrongAnswerDetail(
                    question_id=question.id,
                    topic_id=unit.id,
                    topic_name=unit.title,
                    stem_text=question.stem_text,
                    option_a=question.option_a,
                    option_b=question.option_b,
                    option_c=question.option_c,
                    option_d=question.option_d,
                    selected_answer=interaction.selected_answer,
                    correct_answer=answer_index_to_correct_answer(item.answer_index).value,
                    explanation_text=item.explanation,
                )
            )

    if mutate:
        now = datetime.now(UTC)
        for interaction, item in rows:
            await update_kp_mastery_from_item(
                db,
                user_id=user_id,
                canonical_item_id=item.item_id,
                is_correct=interaction.is_correct,
            )
        session.completed_at = now
        session.total_questions = total
        session.correct_count = correct
        session.score_percent = total_score_pct
        db.add(session)
        await db.flush()

    return ModuleTestResultResponse(
        session_id=session.id,
        module_id=section.id,
        module_name=section.title,
        total_score_percent=total_score_pct,
        passed=passed,
        per_topic=per_topic,
        recommended_review_topics=review_suggestions if not passed else [],
        estimated_review_hours=sum(item.estimated_review_hours for item in review_suggestions)
        if not passed
        else 0.0,
        next_module=None,
        wrong_answers=wrong_answers,
    )


async def _get_canonical_section_or_404(db: AsyncSession, section_id: uuid.UUID) -> CourseSection:
    result = await db.execute(select(CourseSection).where(CourseSection.id == section_id))
    section = result.scalar_one_or_none()
    if section is None:
        raise NotFoundError(f"Canonical course section {section_id} not found.")
    return section


async def _get_canonical_units_for_section(
    db: AsyncSession,
    section_id: uuid.UUID,
) -> list[LearningUnit]:
    result = await db.execute(
        select(LearningUnit)
        .where(
            LearningUnit.section_id == section_id,
            LearningUnit.canonical_unit_id.isnot(None),
        )
        .order_by(LearningUnit.sort_order)
    )
    return list(result.scalars().all())


async def _canonical_units_without_completed_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    units: list[LearningUnit],
) -> list[LearningUnit]:
    missing: list[LearningUnit] = []
    for unit in units:
        result = await db.execute(
            select(Session.id)
            .where(
                Session.user_id == user_id,
                Session.session_type == SessionType.quiz,
                Session.canonical_unit_id == unit.id,
                Session.completed_at.isnot(None),
            )
            .limit(1)
        )
        if result.scalar_one_or_none() is None:
            missing.append(unit)
    return missing


async def _canonical_item_lookup_for_units(
    db: AsyncSession,
    units: list[LearningUnit],
) -> dict[uuid.UUID, QuestionBankItem]:
    canonical_unit_ids = [unit.canonical_unit_id for unit in units if unit.canonical_unit_id]
    if not canonical_unit_ids:
        return {}
    result = await db.execute(
        select(QuestionBankItem).where(QuestionBankItem.unit_id.in_(canonical_unit_ids))
    )
    return {canonical_question_uuid(item.item_id): item for item in result.scalars().all()}


async def _canonical_weak_kp_ids(db: AsyncSession, item_ids: list[str]) -> list[str]:
    if not item_ids:
        return []
    result = await db.execute(select(ItemKPMap.kp_id).where(ItemKPMap.item_id.in_(item_ids)))
    return sorted({str(kp_id) for kp_id in result.scalars().all()})


def _unit_review_hours(unit: LearningUnit) -> float:
    if unit.estimated_minutes is None:
        return 1.0
    return max(0.25, round(unit.estimated_minutes / 60, 2))


# ===========================================================================
# DB mutation helpers
# ===========================================================================


async def _update_mastery_on_pass(
    db: AsyncSession,
    user_id: uuid.UUID,
    rows: list,  # list[(Interaction, Question)]
    topic_by_id: dict[uuid.UUID, Topic],
    now: datetime,
) -> None:
    """
    PASS path: for each topic, set mastery = max(current, test_score_percent).
    Also ratchet bloom_max_achieved.
    """
    # Group interactions by topic
    per_topic: dict[uuid.UUID, list[tuple[Interaction, Question]]] = {}
    for inter, q in rows:
        per_topic.setdefault(q.topic_id, []).append((inter, q))

    for topic_id, topic_rows in per_topic.items():
        correct = sum(1 for inter, _ in topic_rows if inter.is_correct)
        total = len(topic_rows)
        test_score_pct = round(correct / total * 100, 1) if total else 0.0

        # Bloom max from this test for this topic
        bloom_max_this_test: str | None = None
        for inter, q in topic_rows:
            if inter.is_correct:
                bloom_max_this_test = update_bloom_max(bloom_max_this_test, q.bloom_level)

        # Load existing mastery (topic-grain: kc_id IS NULL)
        ms_result = await db.execute(
            select(MasteryScore).where(
                MasteryScore.user_id == user_id,
                MasteryScore.topic_id == topic_id,
                MasteryScore.kc_id.is_(None),
            )
        )
        ms = ms_result.scalar_one_or_none()
        current_pct = round((ms.mastery_probability * 100), 1) if ms else 0.0

        # Take max (module test is authoritative — no regression)
        updated_pct = max(current_pct, test_score_pct)
        new_level = classify_mastery(updated_pct)

        # Ratchet bloom_max (never regresses)
        existing_bloom = ms.bloom_max_achieved if ms else None
        if bloom_max_this_test is not None:
            try:
                new_bloom = update_bloom_max(existing_bloom, BloomLevel(bloom_max_this_test))
            except ValueError:
                new_bloom = existing_bloom
        else:
            new_bloom = existing_bloom

        if ms is None:
            ms = MasteryScore(
                user_id=user_id,
                topic_id=topic_id,
                kc_id=None,
                evidence_count=0,
            )
            db.add(ms)

        ms.mastery_probability = round(updated_pct / 100, 4)
        ms.mastery_level = new_level
        ms.bloom_max_achieved = new_bloom
        ms.evidence_count = ms.evidence_count + total
        ms.last_practiced = now

    await db.flush()


async def _upsert_remediate_entries(
    db: AsyncSession,
    user_id: uuid.UUID,
    review_suggestions: list[ReviewTopicSuggestion],
    now: datetime,
) -> None:
    """
    FAIL path: for each weak topic, insert a LearningPath(action=remediate)
    unless an active one already exists (not completed/skipped).
    New entries are appended after the current maximum order_index.
    """
    if not review_suggestions:
        return

    # Current max order_index for this user
    max_order_result = await db.execute(
        select(func.max(LearningPath.order_index)).where(LearningPath.user_id == user_id)
    )
    next_order: int = (max_order_result.scalar() or 0) + 1

    for suggestion in review_suggestions:
        # Skip if an active remediate entry already exists
        existing_result = await db.execute(
            select(LearningPath.id).where(
                LearningPath.user_id == user_id,
                LearningPath.topic_id == suggestion.topic_id,
                LearningPath.action == PathAction.remediate,
                LearningPath.status.notin_([PathStatus.completed, PathStatus.skipped]),
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            continue

        db.add(
            LearningPath(
                user_id=user_id,
                topic_id=suggestion.topic_id,
                action=PathAction.remediate,
                estimated_hours=suggestion.estimated_review_hours,
                order_index=next_order,
                week_number=None,  # scheduler will assign weeks
                status=PathStatus.pending,
            )
        )
        next_order += 1

    await db.flush()


# ===========================================================================
# Private query helpers
# ===========================================================================


async def _get_module_or_404(db: AsyncSession, module_id: uuid.UUID) -> Module:
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalar_one_or_none()
    if module is None:
        raise NotFoundError(f"Module {module_id} not found.")
    return module


async def _get_module_test_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.session_type == SessionType.module_test,
        )
    )
    sess = result.scalar_one_or_none()
    if sess is None:
        raise NotFoundError("Module test session not found.")
    return sess


async def _get_questions_for_bucket(
    db: AsyncSession,
    topic_id: uuid.UUID,
    difficulty: DifficultyBucket,
) -> list[Question]:
    """Fetch all active module_test questions for a topic + difficulty bucket."""
    result = await db.execute(
        select(Question)
        .where(
            Question.topic_id == topic_id,
            Question.status == QuestionStatus.active,
            Question.difficulty_bucket == difficulty,
            text("usage_context::jsonb @> '[\"module_test\"]'::jsonb"),
        )
        .order_by(func.random())
    )
    return result.scalars().all()


async def _prior_topic_interactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
) -> dict[uuid.UUID, bool]:
    """
    For each question in this topic the user has previously answered,
    return {question_id: True if ever wrong else False}.
    """
    result = await db.execute(
        select(Interaction.question_id, Interaction.is_correct)
        .join(Question, Interaction.question_id == Question.id)
        .where(
            Interaction.user_id == user_id,
            Question.topic_id == topic_id,
        )
    )
    per_question: dict[uuid.UUID, bool] = {}
    for qid, is_correct in result.all():
        if qid not in per_question:
            per_question[qid] = False
        if not is_correct:
            per_question[qid] = True
    return per_question


def _sample_with_priority(
    tiers: list[list[Question]],
    count: int,
) -> list[Question]:
    """
    Draw `count` questions filling from tier-1 first, then tier-2, then tier-3.
    Shuffles within each tier before drawing.
    """
    selected: list[Question] = []
    for tier in tiers:
        if len(selected) >= count:
            break
        needed = count - len(selected)
        pool = list(tier)
        random.shuffle(pool)
        selected.extend(pool[:needed])
    return selected


async def _resolve_kc_names(
    db: AsyncSession,
    kc_id_strs: list[str],
) -> list[str]:
    """Convert KC UUID strings to display names, falling back to the raw string."""
    if not kc_id_strs:
        return []

    valid_uuids: list[uuid.UUID] = []
    for s in kc_id_strs:
        try:
            valid_uuids.append(uuid.UUID(s))
        except ValueError:
            pass

    if not valid_uuids:
        return kc_id_strs

    result = await db.execute(
        select(KnowledgeComponent).where(KnowledgeComponent.id.in_(valid_uuids))
    )
    name_map: dict[str, str] = {str(kc.id): kc.name for kc in result.scalars().all()}
    return [name_map.get(s, s) for s in kc_id_strs]


def _misc_id_for_answer(
    selected: SelectedAnswer,
    question: Question,
) -> str | None:
    """Return the misconception ID for the chosen distractor, or None."""
    if selected == SelectedAnswer.A:
        return question.misconception_a_id
    if selected == SelectedAnswer.B:
        return question.misconception_b_id
    if selected == SelectedAnswer.C:
        return question.misconception_c_id
    if selected == SelectedAnswer.D:
        return question.misconception_d_id
    return None


def _review_hours(topic: Topic | None) -> float:
    """Estimate review hours for a topic using the best available field."""
    if topic is None:
        return 1.0
    for h in (
        topic.estimated_hours_review,
        topic.estimated_hours_intermediate,
        topic.estimated_hours_beginner,
    ):
        if h is not None and h > 0:
            return h
    return 1.0
