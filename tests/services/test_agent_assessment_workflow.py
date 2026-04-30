from src.services.agent_assessment_workflow import AgentAssessmentWorkflowService


def test_assessment_workflow_starts_with_negotiable_proposal():
    service = AgentAssessmentWorkflowService()

    response = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a", "unit-b"],
        question_budget=58,
        phase="skip_verification",
    )

    assert response.status == "waiting_user_approval"
    assert response.interrupt
    assert response.interrupt["estimatedQuestions"] == 58
    assert response.interrupt["reductionOptions"][0]["id"] == "minimum-evidence"


def test_assessment_workflow_reduce_then_approve_keeps_start_disabled_until_real_assessment_is_wired():
    service = AgentAssessmentWorkflowService()
    started = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a", "unit-b"],
        question_budget=58,
        phase="skip_verification",
    )

    reduced = service.resume(
        workflow_id=started.workflow_id,
        user_id="user-1",
        decision={"action": "reduce", "reductionId": "minimum-evidence"},
    )
    assert reduced.status == "waiting_user_approval"
    assert reduced.interrupt
    assert reduced.interrupt["estimatedQuestions"] == 29

    approved = service.resume(
        workflow_id=started.workflow_id,
        user_id="user-1",
        decision={"action": "approve"},
    )
    assert approved.status == "assessment_ready"
    assert approved.actions[0].eligible is False
    assert approved.actions[0].disabled_reason == "not_implemented"


def test_assessment_workflow_rejects_bad_decision_without_500():
    service = AgentAssessmentWorkflowService()
    started = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a"],
        question_budget=20,
        phase="skip_verification",
    )

    response = service.resume(
        workflow_id=started.workflow_id,
        user_id="user-1",
        decision={"action": "reduce", "questionBudget": "abc"},
    )

    assert response.status == "rejected"


def test_assessment_workflow_is_user_scoped():
    service = AgentAssessmentWorkflowService()
    started = service.start(
        user_id="user-1",
        candidate_canonical_unit_ids=["unit-a"],
        question_budget=20,
        phase="skip_verification",
    )

    try:
        service.resume(
            workflow_id=started.workflow_id,
            user_id="user-2",
            decision={"action": "approve"},
        )
    except PermissionError as exc:
        assert "workflow_out_of_scope" in str(exc)
    else:
        raise AssertionError("wrong user must not resume workflow")
