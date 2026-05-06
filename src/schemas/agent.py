from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


AgentScope = Literal[
    "current_unit",
    "current_lecture",
    "current_course",
    "current_path",
    "global_catalog",
]

AgentIntent = Literal[
    "explain_concept",
    "find_content",
    "navigate_to_unit",
    "ask_what_next",
    "assess_knowledge",
    "request_replan",
    "explain_planner_decision",
    "summarize_progress",
    "general_course_question",
    "assistant_help",
    "request_path_switch",
    "clarify",
]

AssessmentPhase = Literal[
    "placement",
    "mini_quiz",
    "skip_verification",
    "bridge_check",
    "final_quiz",
    "review",
]


class RouteContext(BaseModel):
    route: str
    course_slug: str | None = Field(default=None, alias="courseSlug")
    unit_slug: str | None = Field(default=None, alias="unitSlug")
    canonical_unit_id: str | None = Field(default=None, alias="canonicalUnitId")
    player_timestamp_sec: int | None = Field(default=None, alias="playerTimestampSec")

    model_config = ConfigDict(populate_by_name=True)


class QueryExpansion(BaseModel):
    from_term: str = Field(alias="from")
    to: list[str]
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class RuntimeNavigationTrace(BaseModel):
    canonical_unit_id: str
    source: Literal["path_item", "product_learning_unit", "missing"]
    learning_unit_id: str | None = None
    course_slug: str | None = None
    unit_slug: str | None = None
    learn_href: str | None = None


class RetrievalTrace(BaseModel):
    trace_id: str
    intent: AgentIntent | None = None
    raw_query: str | None = None
    normalized_query: str | None = None
    resolved_scope: AgentScope | None = None
    selected_path: str | None = None
    candidate_courses: list[str] = Field(default_factory=list)
    query_expansions: list[QueryExpansion] = Field(default_factory=list)
    applied_filters: list[str] = Field(default_factory=list)
    ranking_version: str
    runtime_navigation_resolution: list[RuntimeNavigationTrace | dict[str, Any]] = Field(
        default_factory=list
    )
    selected_unit_ids: list[str] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = Field(default=None, alias="conversationId")
    incoming_message_id: str = Field(
        default_factory=lambda: f"msg_{uuid4()}",
        alias="incomingMessageId",
    )
    route_context: RouteContext | None = Field(default=None, alias="routeContext")
    intent: AgentIntent | None = None
    response_mode: Literal["non_streaming", "streaming"] = Field(
        default="non_streaming", alias="responseMode"
    )
    trace_mode: Literal["none", "summary", "full"] = Field(default="summary", alias="traceMode")

    model_config = ConfigDict(populate_by_name=True)


class AgentAnswer(BaseModel):
    markdown: str
    confidence: Literal["grounded", "partial", "no_source", "fallback"]


class AgentCitation(BaseModel):
    canonical_unit_id: str
    course_id: str
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_name: str
    learn_href: str | None = None
    timestamp_s: int | None = None
    quote: str | None = None
    source: Literal["summary", "key_point", "transcript", "planner", "mastery"]


class AssessmentProposalScopeItem(BaseModel):
    label: str
    unit_count: int = Field(alias="unitCount")
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class AssessmentDifficultyMix(BaseModel):
    easy: int = 0
    medium: int = 0
    hard: int = 0
    application: int = 0


class AssessmentReductionOption(BaseModel):
    id: str
    label: str
    effect: str
    estimated_questions_after_reduction: int = Field(alias="estimatedQuestionsAfterReduction")

    model_config = ConfigDict(populate_by_name=True)


class AssessmentProposal(BaseModel):
    title: str
    purpose: str
    estimated_questions: int = Field(alias="estimatedQuestions", ge=1, le=70)
    estimated_time_minutes: int = Field(alias="estimatedTimeMinutes", ge=1)
    scope: list[AssessmentProposalScopeItem] = Field(default_factory=list)
    difficulty_mix: AssessmentDifficultyMix = Field(alias="difficultyMix")
    reduction_options: list[AssessmentReductionOption] = Field(
        default_factory=list, alias="reductionOptions"
    )

    model_config = ConfigDict(populate_by_name=True)


class AgentPrerequisitePathNode(BaseModel):
    canonical_unit_id: str = Field(alias="canonicalUnitId")
    unit_name: str = Field(alias="unitName")
    role: Literal["prerequisite", "target"]
    status: Literal[
        "unknown",
        "needs_review",
        "mastered",
        "completed",
        "skipped",
        "in_progress",
        "target",
    ] = "unknown"
    learn_href: str | None = Field(default=None, alias="learnHref")
    mastery_lcb: float | None = Field(default=None, alias="masteryLcb")
    reason: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AgentPrerequisitePathEdge(BaseModel):
    from_canonical_unit_id: str = Field(alias="fromCanonicalUnitId")
    to_canonical_unit_id: str = Field(alias="toCanonicalUnitId")
    reason: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AgentPrerequisitePath(BaseModel):
    target_canonical_unit_id: str = Field(alias="targetCanonicalUnitId")
    nodes: list[AgentPrerequisitePathNode] = Field(default_factory=list)
    edges: list[AgentPrerequisitePathEdge] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class AgentAction(BaseModel):
    type: Literal[
        "open_unit",
        "review_prerequisite_path",
        "start_assessment_workflow",
        "start_assessment",
        "request_replan_dry_run",
        "request_replan",
        "request_path_switch",
        "continue_assessment_workflow",
        "choose_target_path",
        "choose_topic",
    ]
    label: str
    action_id: str | None = Field(default=None, alias="actionId")
    status: Literal[
        "proposed",
        "awaiting_confirmation",
        "confirmed",
        "cancelled",
        "committed",
        "expired",
    ] | None = None
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    learn_href: str | None = None
    workflow_id: str | None = Field(default=None, alias="workflowId")
    canonical_unit_id: str | None = None
    canonical_unit_ids: list[str] = Field(default_factory=list)
    default_phase: AssessmentPhase | None = None
    question_budget: int | None = Field(default=None, ge=1, le=70, alias="questionBudget")
    eligible: bool | None = None
    disabled_reason: Literal[
        "no_eligible_questions",
        "unsupported_phase",
        "out_of_scope",
        "requires_login",
        "not_implemented",
    ] | None = Field(default=None, alias="disabledReason")
    current_plan_id: str | None = Field(default=None, alias="currentPlanId")
    planner_session_id: str | None = Field(default=None, alias="plannerSessionId")
    assessment_session_id: str | None = Field(default=None, alias="assessmentSessionId")
    source_canonical_unit_ids: list[str] = Field(
        default_factory=list, alias="sourceCanonicalUnitIds"
    )
    proposal: AssessmentProposal | None = None
    prerequisite_path: AgentPrerequisitePath | None = Field(default=None, alias="prerequisitePath")

    model_config = ConfigDict(populate_by_name=True)


class AgentFallback(BaseModel):
    reason: Literal[
        "no_retrieval_result",
        "out_of_scope",
        "unsafe_action",
        "tool_error",
        "agent_unavailable",
        "action_error",
    ]
    message: str
    error_code: str | None = Field(default=None, alias="errorCode")

    model_config = ConfigDict(populate_by_name=True)


class AgentWarning(BaseModel):
    type: Literal[
        "outside_current_path",
        "needs_assessment",
        "ambiguous_target",
        "agent_unavailable",
    ]
    message: str


class AgentChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: AgentAnswer
    citations: list[AgentCitation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    warning: AgentWarning | None = None
    fallback: AgentFallback | None = None
    trace: RetrievalTrace | None = None


class AgentInProgressResponse(BaseModel):
    status: Literal["in_progress"] = "in_progress"
    conversation_id: str = Field(alias="conversationId")
    thread_id: str = Field(alias="threadId")
    graph_run_id: str = Field(alias="graphRunId")
    retry_after_ms: int = Field(default=1000, alias="retryAfterMs")

    model_config = ConfigDict(populate_by_name=True)


class AgentActionResumeRequest(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    action_id: str = Field(alias="actionId")
    decision: Literal["approve", "reject", "edit"]
    incoming_message_id: str = Field(
        default_factory=lambda: f"msg_{uuid4()}",
        alias="incomingMessageId",
    )
    edit_payload: dict[str, Any] | None = Field(default=None, alias="editPayload")

    model_config = ConfigDict(populate_by_name=True)


class AgentConversationSummary(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    title: str
    preview: str
    updated_at: datetime = Field(alias="updatedAt")
    message_count: int = Field(alias="messageCount")

    model_config = ConfigDict(populate_by_name=True)


class AgentConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AgentConversationMutationResponse(BaseModel):
    ok: bool = True


class AgentConversationMemory(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    thread_id: str | None = Field(default=None, alias="threadId")
    summary_status: Literal["empty", "fresh", "stale", "updating"] = Field(alias="summaryStatus")
    recent_message_window: int = Field(alias="recentMessageWindow")
    last_updated_at: datetime | None = Field(default=None, alias="lastUpdatedAt")
    summary: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class AgentConversationMessage(BaseModel):
    message_id: str = Field(alias="messageId")
    role: Literal["user", "assistant"]
    markdown: str
    created_at: datetime = Field(alias="createdAt")
    citations: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class UnitSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: AgentScope | None = None
    course_ids: list[str] | None = Field(default=None, alias="courseIds")
    limit: int = Field(default=5, ge=1, le=20)
    intent: AgentIntent | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class UnitSearchResult(BaseModel):
    canonical_unit_id: str
    learning_unit_id: str | None = None
    course_id: str
    course_slug: str | None = None
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_name: str
    summary: str | None = None
    learn_href: str | None = None
    score: float = 0.0
    quiz_available: bool = False
    outside_current_path: bool = False


class UnitSearchResponse(BaseModel):
    results: list[UnitSearchResult]
    trace: RetrievalTrace


class PathRequirementsRequest(BaseModel):
    target_path_key: Literal["computer_vision", "nlp"] | None = Field(
        default=None, alias="targetPathKey"
    )
    target_course_ids: list[str] | None = Field(default=None, alias="targetCourseIds")
    current_mastery_user_id: str | None = Field(default=None, alias="currentMasteryUserId")
    prerequisite_depth: int = Field(default=2, ge=1, le=3, alias="prerequisiteDepth")
    include_mastery: bool = Field(default=True, alias="includeMastery")

    model_config = ConfigDict(populate_by_name=True)


class PathRequirementUnit(BaseModel):
    canonical_unit_id: str
    course_id: str
    unit_name: str
    learn_href: str | None = None
    required_kp_ids: list[str] = Field(default_factory=list)
    mastery_lcb: float | None = None
    status: Literal["unknown", "already_mastered", "needs_review"] = "unknown"
    reason: str | None = None


class PathRequirementsResponse(BaseModel):
    target_path_key: str | None = None
    required_units: list[PathRequirementUnit]
    trace: RetrievalTrace


class UnitContextResponse(BaseModel):
    canonical_unit_id: str
    course_id: str
    unit_name: str
    summary: str | None = None
    key_points: list[Any] = Field(default_factory=list)
    kp_ids: list[str] = Field(default_factory=list)
    quiz_available: bool = False
    learn_href: str | None = None
    transcript_snippets: list[dict[str, Any]] = Field(default_factory=list)


class TranscriptSnippet(BaseModel):
    canonical_unit_id: str
    text: str
    start_sec: int | None = None
    end_sec: int | None = None


class StartAssessmentActionRequest(BaseModel):
    canonical_unit_ids: list[str] = Field(alias="canonicalUnitIds", min_length=1)
    phase: AssessmentPhase
    reason: str
    question_budget: int | None = Field(default=None, ge=1, le=70, alias="questionBudget")

    model_config = ConfigDict(populate_by_name=True)


class RequestReplanActionRequest(BaseModel):
    assessment_session_id: str | None = Field(default=None, alias="assessmentSessionId")
    source_canonical_unit_ids: list[str] = Field(default_factory=list, alias="sourceCanonicalUnitIds")
    reason: str
    dry_run: bool = Field(default=True, alias="dryRun")

    model_config = ConfigDict(populate_by_name=True)


class AgentActionResponse(BaseModel):
    accepted: bool
    rejected_reason: str | None = Field(default=None, alias="rejectedReason")
    dry_run: bool = Field(default=True, alias="dryRun")
    impact: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True)


class AssessmentWorkflowDecision(BaseModel):
    action: Literal["approve", "reduce", "reject"]
    question_budget: int | None = Field(default=None, ge=1, le=70, alias="questionBudget")
    reduction_id: str | None = Field(default=None, alias="reductionId")

    model_config = ConfigDict(populate_by_name=True)


class AgentAssessmentWorkflowRequest(BaseModel):
    workflow_id: str | None = Field(default=None, alias="workflowId")
    event: Literal["start", "resume"] = "start"
    message: str | None = None
    candidate_canonical_unit_ids: list[str] = Field(
        default_factory=list, alias="candidateCanonicalUnitIds"
    )
    question_budget: int = Field(default=30, ge=1, le=70, alias="questionBudget")
    phase: AssessmentPhase = "skip_verification"
    decision: AssessmentWorkflowDecision | None = None

    model_config = ConfigDict(populate_by_name=True)


class AgentAssessmentWorkflowResponse(BaseModel):
    workflow_id: str = Field(alias="workflowId")
    status: Literal[
        "collecting_self_report",
        "waiting_user_approval",
        "assessment_ready",
        "waiting_assessment_result",
        "completed",
        "rejected",
    ]
    interrupt: dict[str, Any] | None = None
    actions: list[AgentAction] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)
