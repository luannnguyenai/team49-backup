from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_planner_audit_repo_importable():
    from src.repositories.planner_audit_repo import PlannerAuditRepository  # noqa


@pytest.mark.asyncio
async def test_planner_audit_repo_creates_plan_and_rationale():
    from src.repositories.planner_audit_repo import PlannerAuditRepository

    session = AsyncMock()
    session.add = Mock()
    repo = PlannerAuditRepository(session)
    user_id = uuid4()
    unit_id = uuid4()

    plan = await repo.create_plan(
        user_id=user_id,
        trigger="manual_replan",
        recommended_path_json=[{"learning_unit_id": str(unit_id), "rank": 1}],
        goal_snapshot_json={"selected_course_ids": ["course_cs231n"]},
        weights_used_json={"need": 0.4, "interest": 0.6},
    )
    rationale = await repo.add_rationale(
        plan_history_id=plan.id,
        learning_unit_id=unit_id,
        rank=1,
        reason_code="need_high",
        term_breakdown_json={"need": 0.9, "interest": 0.2},
        rationale_text="Need is currently dominant.",
    )

    assert rationale.plan_history_id == plan.id
    assert rationale.learning_unit_id == unit_id
    assert rationale.rank == 1


@pytest.mark.asyncio
async def test_planner_audit_repo_upserts_session_state():
    from src.repositories.planner_audit_repo import PlannerAuditRepository

    session = AsyncMock()
    user_id = uuid4()
    created = Mock()
    created.id = uuid4()
    updated = Mock()
    updated.id = created.id
    updated.bridge_chain_depth = 3
    updated.consecutive_bridge_count = 1
    updated.state_json = {"frontier": ["unit_b"]}
    result_1 = Mock()
    result_1.scalar_one.return_value = created
    result_2 = Mock()
    result_2.scalar_one.return_value = updated
    session.execute.side_effect = [result_1, result_2]

    repo = PlannerAuditRepository(session)

    created = await repo.upsert_session_state(
        user_id=user_id,
        session_id="planner-session-1",
        bridge_chain_depth=1,
        consecutive_bridge_count=2,
        state_json={"frontier": ["unit_a"]},
    )
    updated = await repo.upsert_session_state(
        user_id=user_id,
        session_id="planner-session-1",
        bridge_chain_depth=3,
        consecutive_bridge_count=1,
        state_json={"frontier": ["unit_b"]},
        last_plan_history_id=None,
    )

    assert updated.id == created.id
    assert updated.bridge_chain_depth == 3
    assert updated.consecutive_bridge_count == 1
    assert updated.state_json == {"frontier": ["unit_b"]}
