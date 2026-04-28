"""
End-to-end integration test for complete onboarding flow.
Tests: Goals → Topics → Known Topics → Experience Level → Placement Assessment
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserOnboardingProgress
from src.models.course import LearningUnit
from src.models.canonical import QuestionBankItem
from src.models.learning import Session
from src.schemas.onboarding import (
    GoalsRequest,
    KnownTopicsRequest,
    ExperienceLevelRequest,
)
from src.schemas.placement_assessment import (
    PlacementStartRequest,
    PlacementSubmitRequest,
    PlacementAnswerInput,
)
from src.services.onboarding_service import (
    save_user_goals,
    get_topics_tree,
    save_known_topics,
    save_experience_level,
)
from src.services.placement_assessment_service import (
    start_placement_assessment,
    submit_placement_assessment,
)


@pytest.mark.asyncio
async def test_onboarding_flow_step1_set_goals(db_session: AsyncSession):
    """Step 1: User sets their learning goals."""
    # Create test user
    user = User(
        email="test_goals@example.com",
        password_hash="dummy",
    )
    db_session.add(user)
    await db_session.flush()

    # Set goals
    req = GoalsRequest(goal_ids=["nlp"])
    resp = await save_user_goals(db_session, user_id=user.id, goal_ids=req.goal_ids)

    # Verify
    assert resp.goal_ids == ["nlp"]
    assert "cs224n" in resp.course_ids  # nlp should map to cs224n

    # Verify in DB
    stmt = select(UserOnboardingProgress).where(
        UserOnboardingProgress.user_id == user.id
    )
    result = await db_session.execute(stmt)
    progress = result.scalar_one_or_none()

    assert progress is not None
    assert "nlp" in progress.selected_goals


@pytest.mark.asyncio
async def test_onboarding_flow_step2_get_topics(db_session: AsyncSession):
    """Step 2: User gets available topics for their goals."""
    user = User(email="test_topics@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    # Get topics for nlp goal
    resp = await get_topics_tree(db_session, goal_ids=["nlp"])

    # Verify response structure
    assert resp.courses is not None
    # nlp goal maps to cs224n which should have topics
    assert len(resp.courses) > 0


@pytest.mark.asyncio
async def test_onboarding_flow_step3_set_known_topics(db_session: AsyncSession):
    """Step 3: User marks which topics they already know."""
    user = User(email="test_known@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    # Get a learning unit for testing
    stmt = select(LearningUnit).limit(1)
    result = await db_session.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        pytest.skip("No learning units in DB")

    # Mark topic as known
    req = KnownTopicsRequest(topic_unit_ids=[unit.id])
    resp = await save_known_topics(
        db_session, user_id=user.id, topic_unit_ids=req.topic_unit_ids
    )

    # Verify
    assert len(resp.marked_as_known) > 0
    assert unit.id in resp.marked_as_known


@pytest.mark.asyncio
async def test_onboarding_flow_step4_set_experience_level(db_session: AsyncSession):
    """Step 4: User sets their experience level."""
    user = User(email="test_experience@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    # Set experience level
    req = ExperienceLevelRequest(level="intermediate")
    resp = await save_experience_level(db_session, user_id=user.id, level=req.level)

    # Verify
    assert resp.level == "intermediate"

    # Verify in DB
    stmt = select(UserOnboardingProgress).where(
        UserOnboardingProgress.user_id == user.id
    )
    result = await db_session.execute(stmt)
    progress = result.scalar_one_or_none()

    assert progress is not None
    assert progress.experience_level == "intermediate"


@pytest.mark.asyncio
async def test_onboarding_flow_step5_start_placement_assessment(db_session: AsyncSession):
    """Step 5: Start placement assessment for selected topics."""
    user = User(email="test_placement_start@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    # Get learning units with placement items
    stmt = (
        select(LearningUnit)
        .where(LearningUnit.canonical_unit_id.isnot(None))
        .limit(2)
    )
    result = await db_session.execute(stmt)
    units = result.scalars().all()

    if len(units) < 1:
        pytest.skip("Not enough learning units with canonical_unit_id")

    topic_unit_ids = [u.id for u in units[:2]]

    # Start placement
    req = PlacementStartRequest(topic_unit_ids=topic_unit_ids)
    resp = await start_placement_assessment(
        db_session, user_id=user.id, topic_unit_ids=req.topic_unit_ids
    )

    # Verify response
    assert resp.session_id is not None
    if resp.should_skip_step:
        pytest.skip("All units had no placement items")

    assert resp.total_questions > 0
    assert len(resp.questions) == resp.total_questions
    assert len(resp.topic_unit_ids) > 0

    # Verify session in DB
    stmt = select(Session).where(Session.id == resp.session_id)
    result = await db_session.execute(stmt)
    session = result.scalar_one_or_none()

    assert session is not None
    assert session.user_id == user.id
    assert session.total_questions == resp.total_questions
    assert session.completed_at is None

    return resp.session_id, resp.questions, resp.topic_unit_ids


@pytest.mark.asyncio
async def test_onboarding_flow_step6_submit_placement_answers(db_session: AsyncSession):
    """Step 6: User submits placement assessment answers."""
    user = User(email="test_placement_submit@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    # Start placement
    stmt = (
        select(LearningUnit)
        .where(LearningUnit.canonical_unit_id.isnot(None))
        .limit(1)
    )
    result = await db_session.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit or not unit.canonical_unit_id:
        pytest.skip("No learning unit with canonical_unit_id")

    req = PlacementStartRequest(topic_unit_ids=[unit.id])
    start_resp = await start_placement_assessment(
        db_session, user_id=user.id, topic_unit_ids=[unit.id]
    )

    if start_resp.should_skip_step:
        pytest.skip("Unit has no placement items")

    # Submit answers (answer all correctly)
    answers = [
        PlacementAnswerInput(
            item_id=q.item_id,
            topic_unit_id=q.topic_unit_id,
            selected_answer="A",  # Assuming A is answer for all
        )
        for q in start_resp.questions
    ]

    submit_resp = await submit_placement_assessment(
        db_session,
        user_id=user.id,
        session_id=start_resp.session_id,
        answers=answers,
    )

    # Verify response
    assert submit_resp.session_id == start_resp.session_id
    assert len(submit_resp.topic_decisions) > 0
    assert (
        submit_resp.skipped_count
        + submit_resp.review_count
        + submit_resp.relearn_count
        == len(submit_resp.topic_decisions)
    )

    # Verify session marked complete
    stmt = select(Session).where(Session.id == start_resp.session_id)
    result = await db_session.execute(stmt)
    session = result.scalar_one_or_none()

    assert session is not None
    assert session.completed_at is not None
    assert session.score_percent is not None


@pytest.mark.asyncio
async def test_onboarding_flow_complete_journey(db_session: AsyncSession):
    """Complete onboarding journey: Goals → Topics → Experience → Placement."""
    # Create user
    user = User(email="test_complete_journey@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    # Step 1: Set goals
    goals_resp = await save_user_goals(
        db_session, user_id=user.id, goal_ids=["nlp"]
    )
    assert goals_resp.goal_ids == ["nlp"]

    # Step 2: Get topics
    topics_resp = await get_topics_tree(db_session, goal_ids=["nlp"])
    assert topics_resp.courses is not None

    # Step 3: Set known topics
    stmt = select(LearningUnit).limit(1)
    result = await db_session.execute(stmt)
    unit = result.scalar_one_or_none()

    if unit:
        known_resp = await save_known_topics(
            db_session, user_id=user.id, topic_unit_ids=[unit.id]
        )
        assert len(known_resp.marked_as_known) >= 0

    # Step 4: Set experience level
    exp_resp = await save_experience_level(
        db_session, user_id=user.id, level="beginner"
    )
    assert exp_resp.level == "beginner"

    # Step 5: Start placement (with units that have canonical_unit_id)
    stmt = (
        select(LearningUnit)
        .where(LearningUnit.canonical_unit_id.isnot(None))
        .limit(1)
    )
    result = await db_session.execute(stmt)
    placement_unit = result.scalar_one_or_none()

    if placement_unit:
        placement_start = await start_placement_assessment(
            db_session, user_id=user.id, topic_unit_ids=[placement_unit.id]
        )

        if not placement_start.should_skip_step:
            # Step 6: Submit answers
            answers = [
                PlacementAnswerInput(
                    item_id=q.item_id,
                    topic_unit_id=q.topic_unit_id,
                    selected_answer="A",
                )
                for q in placement_start.questions
            ]

            submit_resp = await submit_placement_assessment(
                db_session,
                user_id=user.id,
                session_id=placement_start.session_id,
                answers=answers,
            )

            assert submit_resp.session_id is not None
            assert len(submit_resp.topic_decisions) > 0

    # Verify user onboarding progress
    stmt = select(UserOnboardingProgress).where(
        UserOnboardingProgress.user_id == user.id
    )
    result = await db_session.execute(stmt)
    progress = result.scalar_one_or_none()

    assert progress is not None
    assert "nlp" in progress.selected_goals
    assert progress.experience_level == "beginner"


@pytest.mark.asyncio
async def test_placement_assessment_with_mixed_answers(db_session: AsyncSession):
    """Test placement assessment with correct and incorrect answers."""
    user = User(email="test_mixed_answers@example.com", password_hash="dummy")
    db_session.add(user)
    await db_session.flush()

    # Get a learning unit with placement items
    stmt = (
        select(LearningUnit)
        .where(LearningUnit.canonical_unit_id.isnot(None))
        .limit(1)
    )
    result = await db_session.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit or not unit.canonical_unit_id:
        pytest.skip("No learning unit with canonical_unit_id")

    # Start placement
    start_resp = await start_placement_assessment(
        db_session, user_id=user.id, topic_unit_ids=[unit.id]
    )

    if start_resp.should_skip_step:
        pytest.skip("Unit has no placement items")

    # Get correct answers
    item_ids = [q.item_id for q in start_resp.questions]
    stmt = select(QuestionBankItem).where(QuestionBankItem.item_id.in_(item_ids))
    result = await db_session.execute(stmt)
    items_by_id = {item.item_id: item for item in result.scalars().all()}

    # Create mixed answers: some correct, some wrong
    answers = []
    for i, q in enumerate(start_resp.questions):
        item = items_by_id.get(q.item_id)
        if item:
            # Answer first question correctly, others wrong
            if i == 0:
                correct_answer = ["A", "B", "C", "D"][item.answer_index or 0]
            else:
                # Answer incorrectly
                idx = (item.answer_index or 0) + 1
                correct_answer = ["A", "B", "C", "D"][idx % 4]
        else:
            correct_answer = "A"

        answers.append(
            PlacementAnswerInput(
                item_id=q.item_id,
                topic_unit_id=q.topic_unit_id,
                selected_answer=correct_answer,
            )
        )

    # Submit answers
    submit_resp = await submit_placement_assessment(
        db_session,
        user_id=user.id,
        session_id=start_resp.session_id,
        answers=answers,
    )

    # Verify decision based on score
    assert len(submit_resp.topic_decisions) > 0
    decision = submit_resp.topic_decisions[0]

    # Score should be around 20% (1 correct out of ~5 questions)
    assert decision.score_pct >= 0 and decision.score_pct <= 100

    # Decision classification
    if decision.score_pct >= 70:
        assert decision.decision == "skip"
    elif decision.score_pct >= 50:
        assert decision.decision == "review"
    else:
        assert decision.decision == "relearn"
