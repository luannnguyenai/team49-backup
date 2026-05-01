from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.repositories.agent_conversation_repo import AgentConversationRepository
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import (
    AgentActionResponse,
    AgentActionResumeRequest,
    AgentAssessmentWorkflowRequest,
    AgentAssessmentWorkflowResponse,
    AgentChatRequest,
    AgentChatResponse,
    AgentConversationMemory,
    AgentConversationMessage,
    AgentConversationSummary,
    PathRequirementsRequest,
    PathRequirementsResponse,
    RequestReplanActionRequest,
    StartAssessmentActionRequest,
    TranscriptSnippet,
    UnitContextResponse,
    UnitSearchRequest,
    UnitSearchResponse,
)
from src.services.agent_action_service import (
    start_agent_assessment,
    validate_replan_request,
)
from src.exceptions import ValidationError
from src.services.agent_assessment_workflow import AgentAssessmentWorkflowService
from src.services.agent_context_service import AgentContextResolver
from src.services.agent_conversation_service import AgentConversationService
from src.services.agent_graph_contracts import AgentInProgressError, AgentRouterUnavailableError
from src.services.agent_graph_service import AgentGraphService
from src.services.agent_lock_service import AgentThreadLock
from src.services.agent_navigation_service import AgentNavigationService
from src.services.agent_requirement_service import AgentPathRequirementService
from src.repositories.agent_graph_repo import AgentGraphRepository
from src.services.agent_router_factory import build_production_agent_router
from src.services.agent_search_service import AgentUnitSearchService
from src.services.agent_unit_context_service import AgentUnitContextService


agent_router = APIRouter(prefix="/api/agent", tags=["agent"])
assessment_workflow_service = AgentAssessmentWorkflowService()


async def _agent_context_for_user(user: User, db: AsyncSession):
    return await AgentContextResolver(db).resolve(user)


def _services(db: AsyncSession):
    repo = CanonicalContentRepository(db)
    navigation = AgentNavigationService(repo)
    search = AgentUnitSearchService(repo, navigation)
    requirements = AgentPathRequirementService(repo, navigation)
    return repo, navigation, search, requirements


@agent_router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    body: AgentChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentChatResponse:
    context = await _agent_context_for_user(user, db)
    _repo, _navigation, search, requirements = _services(db)
    conversation_repo = AgentConversationRepository(db)
    conversation_id: UUID
    if body.conversation_id:
        conversation_id = UUID(body.conversation_id)
        conversation = await conversation_repo.get_conversation(conversation_id, user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="conversation_not_found")
    else:
        conversation = await conversation_repo.create_conversation(user.id)
        conversation_id = conversation.id
        body.conversation_id = str(conversation_id)

    try:
        response = await AgentGraphService(
            search,
            requirements,
            router=build_production_agent_router(),
            graph_repo=AgentGraphRepository(db),
            thread_lock=AgentThreadLock(db),
            conversation_repo=conversation_repo,
        ).chat(
            request=body,
            conversation_id=str(conversation_id),
            thread_id=conversation.thread_id,
            user_id=str(user.id),
            allowed_course_ids=context.allowed_course_ids,
            current_path_course_ids=context.selected_path_course_ids,
        )
    except AgentInProgressError as exc:
        return JSONResponse(status_code=409, content=exc.to_response().model_dump(by_alias=True))
    except AgentRouterUnavailableError as exc:
        response = exc.to_response(conversation_id=str(conversation_id), message_id=str(uuid4()))
    await db.commit()
    return response


@agent_router.post("/actions/continue", response_model=AgentChatResponse)
async def agent_continue_action(
    body: AgentActionResumeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentChatResponse:
    _repo, _navigation, search, requirements = _services(db)
    try:
        response = await AgentGraphService(
            search,
            requirements,
            router=build_production_agent_router(),
            graph_repo=AgentGraphRepository(db),
            thread_lock=AgentThreadLock(db),
        ).resume_action(request=body, user_id=str(user.id))
    except AgentInProgressError as exc:
        return JSONResponse(status_code=409, content=exc.to_response().model_dump(by_alias=True))
    except AgentRouterUnavailableError as exc:
        response = exc.to_response(conversation_id=body.conversation_id, message_id=str(uuid4()))
    await db.commit()
    return response


@agent_router.post("/search-units", response_model=UnitSearchResponse)
async def agent_search_units(
    body: UnitSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UnitSearchResponse:
    context = await _agent_context_for_user(user, db)
    _repo, _navigation, search, _requirements = _services(db)
    return await search.search(body, allowed_course_ids=context.allowed_course_ids)


@agent_router.post("/path-requirements", response_model=PathRequirementsResponse)
async def agent_path_requirements(
    body: PathRequirementsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> PathRequirementsResponse:
    context = await _agent_context_for_user(user, db)
    _repo, _navigation, _search, requirements = _services(db)
    return await requirements.get_requirements(
        body,
        allowed_course_ids=context.allowed_course_ids,
        user_id=user.id,
    )


@agent_router.get("/unit-context/{canonical_unit_id}", response_model=UnitContextResponse)
async def agent_unit_context(
    canonical_unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UnitContextResponse:
    context = await _agent_context_for_user(user, db)
    repo, navigation, _search, _requirements = _services(db)
    try:
        return await AgentUnitContextService(repo, navigation).get_context(
            canonical_unit_id,
            allowed_course_ids=context.allowed_course_ids,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@agent_router.get(
    "/unit-context/{canonical_unit_id}/transcript-snippets",
    response_model=list[TranscriptSnippet],
)
async def agent_transcript_snippets(
    canonical_unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[TranscriptSnippet]:
    context = await _agent_context_for_user(user, db)
    repo, navigation, _search, _requirements = _services(db)
    try:
        return await AgentUnitContextService(repo, navigation).get_transcript_snippets(
            canonical_unit_id,
            allowed_course_ids=context.allowed_course_ids,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@agent_router.get("/conversations", response_model=list[AgentConversationSummary])
async def agent_list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[AgentConversationSummary]:
    return await AgentConversationService(AgentConversationRepository(db)).list_conversations(user.id)


@agent_router.post("/conversations", response_model=AgentConversationSummary)
async def agent_create_conversation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentConversationSummary:
    result = await AgentConversationService(AgentConversationRepository(db)).create_conversation(user.id)
    await db.commit()
    return result


@agent_router.get("/conversations/{conversation_id}", response_model=list[AgentConversationMessage])
async def agent_conversation_messages(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[AgentConversationMessage]:
    try:
        return await AgentConversationService(AgentConversationRepository(db)).get_messages(
            conversation_id,
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@agent_router.get("/conversations/{conversation_id}/memory", response_model=AgentConversationMemory)
async def agent_conversation_memory(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentConversationMemory:
    try:
        return await AgentConversationService(AgentConversationRepository(db)).get_memory(
            conversation_id,
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def _validate_workflow_candidates_in_scope(
    canonical_unit_ids: list[str],
    allowed_course_ids: list[str],
    db: AsyncSession,
) -> None:
    units = await CanonicalContentRepository(db).get_canonical_units_by_ids(canonical_unit_ids)
    if len(units) != len(set(canonical_unit_ids)):
        raise HTTPException(status_code=404, detail="candidate_unit_not_found")
    if any(unit.course_id not in allowed_course_ids for unit in units.values()):
        raise HTTPException(status_code=403, detail="candidate_unit_out_of_scope")


@agent_router.post("/assessment-workflows", response_model=AgentAssessmentWorkflowResponse)
async def agent_start_assessment_workflow(
    body: AgentAssessmentWorkflowRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentAssessmentWorkflowResponse:
    if body.event != "start":
        raise HTTPException(status_code=422, detail="event_must_be_start")
    context = await _agent_context_for_user(user, db)
    await _validate_workflow_candidates_in_scope(
        body.candidate_canonical_unit_ids,
        allowed_course_ids=context.allowed_course_ids,
        db=db,
    )
    return assessment_workflow_service.start(
        user_id=str(user.id),
        candidate_canonical_unit_ids=body.candidate_canonical_unit_ids,
        question_budget=body.question_budget,
        phase=body.phase,
    )


@agent_router.post(
    "/assessment-workflows/{workflow_id}/resume",
    response_model=AgentAssessmentWorkflowResponse,
)
async def agent_resume_assessment_workflow(
    workflow_id: str,
    body: AgentAssessmentWorkflowRequest,
    user: User = Depends(get_current_user),
) -> AgentAssessmentWorkflowResponse:
    if body.event != "resume":
        raise HTTPException(status_code=422, detail="event_must_be_resume")
    try:
        return assessment_workflow_service.resume(
            workflow_id=workflow_id,
            user_id=str(user.id),
            decision=body.decision,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@agent_router.post("/actions/start-assessment", response_model=AgentActionResponse)
async def agent_start_assessment(
    body: StartAssessmentActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentActionResponse:
    try:
        assessment = await start_agent_assessment(db, user_id=user.id, request=body)
    except ValidationError as exc:
        return AgentActionResponse(
            accepted=False,
            rejectedReason=str(exc),
            dryRun=False,
            impact=None,
        )
    return AgentActionResponse(
        accepted=True,
        rejectedReason=None,
        dryRun=False,
        impact={
            "sessionId": str(assessment.session_id),
            "totalQuestions": assessment.total_questions,
            "questions": [question.model_dump(mode="json") for question in assessment.questions],
            "canonicalUnitIds": body.canonical_unit_ids,
            "phase": body.phase,
            "href": "/assessment",
        },
    )


@agent_router.post("/actions/request-replan", response_model=AgentActionResponse)
async def agent_request_replan(
    body: RequestReplanActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentActionResponse:
    validation = await validate_replan_request(db, body, user)
    return AgentActionResponse(
        accepted=validation.accepted,
        rejectedReason=validation.rejected_reason,
        dryRun=body.dry_run,
        impact=validation.impact,
    )
