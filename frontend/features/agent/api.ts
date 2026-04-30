import { api } from "@/lib/api";

export type AgentWarningType = "outside_current_path" | "needs_assessment" | "ambiguous_target";
export type AgentActionType =
  | "open_unit"
  | "review_prerequisite_path"
  | "start_assessment_workflow"
  | "start_assessment"
  | "request_replan_dry_run"
  | "continue_assessment_workflow"
  | "choose_target_path";

export interface AgentCitation {
  canonical_unit_id?: string;
  canonicalUnitId?: string;
  course_id?: string;
  courseId?: string;
  lecture_id?: string | null;
  lectureId?: string | null;
  lecture_title?: string | null;
  lectureTitle?: string | null;
  unit_name?: string;
  unitName?: string;
  learn_href?: string | null;
  learnHref?: string | null;
  timestamp_s?: number | null;
  timestampS?: number | null;
  quote?: string | null;
  source?: string;
}

export interface AgentAction {
  type: AgentActionType;
  label: string;
  learn_href?: string | null;
  learnHref?: string | null;
  workflow_id?: string | null;
  workflowId?: string | null;
  canonical_unit_id?: string | null;
  canonicalUnitId?: string | null;
  canonical_unit_ids?: string[];
  canonicalUnitIds?: string[];
  default_phase?: string | null;
  defaultPhase?: string | null;
  question_budget?: number | null;
  questionBudget?: number | null;
  eligible?: boolean | null;
  disabled_reason?: string | null;
  disabledReason?: string | null;
  proposal?: AssessmentProposal | null;
}

export interface AgentWarning {
  type: AgentWarningType;
  message: string;
}

export interface AgentAnswer {
  markdown: string;
  confidence: "grounded" | "partial" | "no_source";
}

export interface AgentChatResponse {
  conversation_id?: string;
  conversationId?: string;
  message_id?: string;
  messageId?: string;
  answer: AgentAnswer;
  citations: AgentCitation[];
  actions: AgentAction[];
  warning?: AgentWarning | null;
  fallback?: { reason: string; message: string } | null;
}

export interface AgentConversationSummary {
  conversation_id?: string;
  conversationId?: string;
  title: string;
  preview: string;
  updated_at?: string;
  updatedAt?: string;
  message_count?: number;
  messageCount?: number;
}

export interface AgentConversationMessage {
  message_id?: string;
  messageId?: string;
  role: "user" | "assistant";
  markdown: string;
  created_at?: string;
  createdAt?: string;
  citations?: AgentCitation[];
  actions?: AgentAction[];
}

export interface AgentConversationMemory {
  conversation_id?: string;
  conversationId?: string;
  summary_status?: "empty" | "fresh" | "stale" | "updating";
  summaryStatus?: "empty" | "fresh" | "stale" | "updating";
  recent_message_window?: number;
  recentMessageWindow?: number;
  last_updated_at?: string | null;
  lastUpdatedAt?: string | null;
  summary: Record<string, unknown>;
}

export interface AssessmentProposalScopeItem {
  label: string;
  unitCount?: number;
  unit_count?: number;
  reason: string;
}

export interface AssessmentProposal {
  title: string;
  purpose: string;
  estimatedQuestions?: number;
  estimated_questions?: number;
  estimatedTimeMinutes?: number;
  estimated_time_minutes?: number;
  scope: AssessmentProposalScopeItem[];
  difficultyMix?: Record<string, number>;
  difficulty_mix?: Record<string, number>;
  reductionOptions?: AssessmentReductionOption[];
  reduction_options?: AssessmentReductionOption[];
}

export interface AssessmentReductionOption {
  id: string;
  label: string;
  effect: string;
  estimatedQuestionsAfterReduction?: number;
  estimated_questions_after_reduction?: number;
}

export interface AgentAssessmentWorkflowResponse {
  workflow_id?: string;
  workflowId?: string;
  status:
    | "collecting_self_report"
    | "waiting_user_approval"
    | "assessment_ready"
    | "waiting_assessment_result"
    | "completed"
    | "rejected";
  interrupt?: (AssessmentProposal & { canonicalUnitIds?: string[]; phase?: string; message?: string }) | null;
  actions: AgentAction[];
}

export interface AgentActionResponse {
  accepted: boolean;
  rejected_reason?: string | null;
  rejectedReason?: string | null;
  dry_run?: boolean;
  dryRun?: boolean;
  impact?: Record<string, unknown> | null;
}

export const agentApi = {
  listConversations: () =>
    api.get<AgentConversationSummary[]>("/api/agent/conversations").then((r) => r.data),

  createConversation: () =>
    api.post<AgentConversationSummary>("/api/agent/conversations").then((r) => r.data),

  messages: (conversationId: string) =>
    api
      .get<AgentConversationMessage[]>(`/api/agent/conversations/${conversationId}`)
      .then((r) => r.data),

  memory: (conversationId: string) =>
    api
      .get<AgentConversationMemory>(`/api/agent/conversations/${conversationId}/memory`)
      .then((r) => r.data),

  chat: (payload: {
    message: string;
    conversationId?: string | null;
    routeContext?: Record<string, unknown>;
    traceMode?: "none" | "summary" | "full";
  }) => api.post<AgentChatResponse>("/api/agent/chat", payload).then((r) => r.data),

  startAssessmentWorkflow: (payload: {
    candidateCanonicalUnitIds: string[];
    questionBudget?: number;
    phase?: string;
  }) =>
    api
      .post<AgentAssessmentWorkflowResponse>("/api/agent/assessment-workflows", {
        event: "start",
        ...payload,
      })
      .then((r) => r.data),

  resumeAssessmentWorkflow: (
    workflowId: string,
    decision: { action: "approve" | "reduce" | "reject"; reductionId?: string; questionBudget?: number },
  ) =>
    api
      .post<AgentAssessmentWorkflowResponse>(`/api/agent/assessment-workflows/${workflowId}/resume`, {
        event: "resume",
        decision,
      })
      .then((r) => r.data),

  startAssessmentAction: (payload: {
    canonicalUnitIds: string[];
    phase: string;
    reason: string;
    questionBudget?: number | null;
  }) =>
    api
      .post<AgentActionResponse>("/api/agent/actions/start-assessment", payload)
      .then((r) => r.data),
};

export function getConversationId(value: AgentConversationSummary | AgentChatResponse | AgentConversationMemory) {
  return value.conversationId ?? value.conversation_id ?? "";
}

export function getMessageId(value: AgentConversationMessage | AgentChatResponse) {
  return value.messageId ?? value.message_id ?? "";
}

export function getUpdatedAt(value: AgentConversationSummary) {
  return value.updatedAt ?? value.updated_at ?? "";
}

export function getCreatedAt(value: AgentConversationMessage) {
  return value.createdAt ?? value.created_at ?? "";
}

export function getCitationCanonicalId(value: AgentCitation) {
  return value.canonicalUnitId ?? value.canonical_unit_id ?? "";
}

export function getCitationCourseId(value: AgentCitation) {
  return value.courseId ?? value.course_id ?? "Course";
}

export function getCitationUnitName(value: AgentCitation) {
  return value.unitName ?? value.unit_name ?? "Learning unit";
}

export function getCitationLectureTitle(value: AgentCitation) {
  return value.lectureTitle ?? value.lecture_title ?? "";
}

export function getCitationHref(value: AgentCitation | AgentAction) {
  return value.learnHref ?? value.learn_href ?? null;
}

export function getActionCanonicalIds(value: AgentAction) {
  return value.canonicalUnitIds ?? value.canonical_unit_ids ?? [];
}

export function getActionDisabledReason(value: AgentAction) {
  return value.disabledReason ?? value.disabled_reason ?? null;
}

export function getActionQuestionBudget(value: AgentAction) {
  return value.questionBudget ?? value.question_budget ?? null;
}

export function getWorkflowId(value: AgentAssessmentWorkflowResponse | AgentAction) {
  return value.workflowId ?? value.workflow_id ?? "";
}

export function getProposalQuestionCount(value: AssessmentProposal) {
  return value.estimatedQuestions ?? value.estimated_questions ?? 0;
}

export function getProposalMinutes(value: AssessmentProposal) {
  return value.estimatedTimeMinutes ?? value.estimated_time_minutes ?? 0;
}

export function getProposalDifficultyMix(value: AssessmentProposal) {
  return value.difficultyMix ?? value.difficulty_mix ?? {};
}

export function getProposalReductionOptions(value: AssessmentProposal) {
  return value.reductionOptions ?? value.reduction_options ?? [];
}

export function getScopeUnitCount(value: AssessmentProposalScopeItem) {
  return value.unitCount ?? value.unit_count ?? 0;
}

export function getReductionQuestionCount(value: AssessmentReductionOption) {
  return value.estimatedQuestionsAfterReduction ?? value.estimated_questions_after_reduction ?? 0;
}
