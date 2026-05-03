"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  Bot,
  CheckCircle2,
  ChevronRight,
  Check,
  Clock,
  History,
  Info,
  Loader2,
  Map,
  Menu,
  MessageSquare,
  MoreVertical,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Send,
  Target,
  Trash2,
  User,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import {
  agentApi,
  getActionCanonicalId,
  getActionCanonicalIds,
  getActionDisabledReason,
  getActionId,
  getActionQuestionBudget,
  getCitationCanonicalId,
  getCitationCourseId,
  getCitationHref,
  getCitationLectureTitle,
  getCitationUnitName,
  getConversationId,
  getCreatedAt,
  getMessageId,
  getProposalDifficultyMix,
  getProposalMinutes,
  getProposalQuestionCount,
  getProposalReductionOptions,
  getReductionQuestionCount,
  getScopeUnitCount,
  getUnitContextCourseId,
  getUnitContextHref,
  getUnitContextQuizAvailable,
  getUnitContextUnitName,
  getUpdatedAt,
  getWorkflowId,
  type AgentAction,
  type AgentAssessmentWorkflowResponse,
  type AgentChatResponse,
  type AgentCitation,
  type AgentConversationMessage,
  type AgentConversationSummary,
  type AgentUnitContext,
  type AgentWarning,
  type AssessmentProposal,
} from "@/features/agent/api";
import { learningPathApi } from "@/features/learning-path/api";
import { getStatusLabel } from "@/features/learning-path/lib/status";
import { writeStartedCanonicalAssessment } from "@/lib/canonical-assessment-session";
import type { PathItemResponse, QuestionForAssessment } from "@/types";

type UiMessage = {
  id: string;
  role: "user" | "assistant";
  markdown: string;
  createdAt: string;
  confidence?: "grounded" | "partial" | "no_source" | "fallback";
  incomingMessageId?: string;
  citations: AgentCitation[];
  actions: AgentAction[];
  warning?: AgentWarning | null;
  fallback?: AgentChatResponse["fallback"];
  retryMessage?: string;
  retryIncomingMessageId?: string;
};

function createIncomingMessageId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getFallbackErrorCode(fallback: AgentChatResponse["fallback"] | undefined) {
  return fallback?.errorCode ?? fallback?.error_code ?? null;
}

function cleanSourceSummary(value: string) {
  return value
    .replace(/\s*\[ts=\d+(?:\.\d+)?s?\]/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function AssistantMarkdown({ markdown }: { markdown: string }) {
  return (
    <ReactMarkdown
      components={{
        a: ({ children }) => <span>{children}</span>,
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
}

function getClientErrorCode(error: unknown) {
  const responseStatus =
    typeof error === "object" && error !== null && "response" in error
      ? (error as { response?: { status?: number } }).response?.status
      : undefined;
  if (responseStatus) return `AGENT_HTTP_${responseStatus}`;

  const transportCode =
    typeof error === "object" && error !== null && "code" in error
      ? String((error as { code?: unknown }).code ?? "")
      : "";
  const message = error instanceof Error ? error.message.toLowerCase() : "";
  if (transportCode === "ECONNABORTED" || transportCode === "ETIMEDOUT" || message.includes("timeout")) {
    return "AGENT_REQUEST_TIMEOUT";
  }

  return "AGENT_NETWORK_ERROR";
}

function buildAgentClientErrorMessage(
  error: unknown,
  retry: { message: string; incomingMessageId: string },
): UiMessage {
  const errorCode = getClientErrorCode(error);
  return {
    id: `assistant-error-${Date.now()}`,
    role: "assistant",
    markdown: `The AI assistant is temporarily unavailable due to a system incident. Please try again later. Error code: ${errorCode}.`,
    createdAt: new Date().toISOString(),
    confidence: "fallback",
    citations: [],
    actions: [],
    warning: {
      type: "agent_unavailable",
      message: errorCode,
    },
    fallback: {
      reason: "agent_unavailable",
      message: "The agent request failed before a safe answer could be produced.",
      errorCode,
    },
    retryMessage: retry.message,
    retryIncomingMessageId: retry.incomingMessageId,
  };
}

const QUICK_PROMPTS = [
  "Where should I review CNNs?",
  "What should I learn next?",
  "Can I skip the units I already know?",
  "Which DL parts are required for NLP?",
];

const TURN_PROGRESS_STEPS = [
  "Preparing request",
  "Routing intent",
  "Searching current path",
  "Reading sources",
  "Composing answer",
];

function formatDateLabel(value: string) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(value));
  } catch {
    return "";
  }
}

function toUiMessages(messages: AgentConversationMessage[]): UiMessage[] {
  return messages.map((message) => ({
    id: getMessageId(message),
    role: message.role,
    markdown: message.markdown,
    createdAt: getCreatedAt(message),
    citations: message.citations ?? [],
    actions: message.actions ?? [],
  }));
}

function WarningBlock({ warning }: { warning: AgentWarning }) {
  const tone =
    warning.type === "outside_current_path"
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : warning.type === "ambiguous_target"
        ? "border-slate-200 bg-slate-50 text-slate-800"
        : "border-blue-200 bg-blue-50 text-blue-900";
  const Icon = warning.type === "ambiguous_target" ? AlertTriangle : warning.type === "needs_assessment" ? ArrowRight : Info;

  return (
    <div className={cn("mt-3 flex gap-3 rounded-xl border p-3 text-sm leading-6", tone)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <p>{warning.message}</p>
    </div>
  );
}

function isDuplicateWarning(message: UiMessage) {
  return (
    !!message.warning?.message &&
    message.warning.message.trim() === message.markdown.trim()
  );
}

function citationKey(citation: AgentCitation) {
  return getCitationCanonicalId(citation) || getCitationHref(citation) || getCitationUnitName(citation);
}

function isDuplicateOpenUnitAction(action: AgentAction, citations: AgentCitation[]) {
  if (action.type !== "open_unit") return false;
  const actionCanonicalId = getActionCanonicalId(action);
  const actionHref = getCitationHref(action);
  return citations.some((citation) => {
    const citationCanonicalId = getCitationCanonicalId(citation);
    const citationHref = getCitationHref(citation);
    return (
      (actionCanonicalId && citationCanonicalId && actionCanonicalId === citationCanonicalId) ||
      (actionHref && citationHref && actionHref === citationHref)
    );
  });
}

function findPathItemForCitation(citation: AgentCitation, items: PathItemResponse[]) {
  const canonicalId = getCitationCanonicalId(citation);
  const href = getCitationHref(citation);
  return (
    items.find((item) => canonicalId && item.canonical_unit_id === canonicalId) ??
    items.find((item) => href && item.learn_href === href) ??
    null
  );
}

function CitationCard({
  citation,
  isSelected,
  onSelect,
}: {
  citation: AgentCitation;
  isSelected: boolean;
  onSelect: (citation: AgentCitation) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(citation)}
      className={cn(
        "group block w-full rounded-2xl border bg-white p-3 text-left transition hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/10 focus:outline-none focus:ring-2 focus:ring-blue-500/20",
        isSelected ? "border-blue-300 shadow-lg shadow-blue-500/10" : "border-slate-200",
      )}
      aria-label={`View source details: ${getCitationUnitName(citation)}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-blue-50 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-blue-600">
              {getCitationCourseId(citation)}
            </span>
          </div>
          <h4 className="line-clamp-2 text-sm font-black leading-snug text-slate-900 group-hover:text-blue-600">
            {getCitationUnitName(citation)}
          </h4>
          {getCitationLectureTitle(citation) ? (
            <p className="mt-1 line-clamp-1 text-xs font-medium text-slate-500">
              {getCitationLectureTitle(citation)}
            </p>
          ) : null}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-50 text-slate-400 transition group-hover:bg-blue-600 group-hover:text-white">
          <ChevronRight className="h-4 w-4" />
        </div>
      </div>
    </button>
  );
}

function SourceDetailPanel({
  citation,
  unitContext,
  pathItem,
  isLoading,
  error,
  onClose,
}: {
  citation: AgentCitation | null;
  unitContext: AgentUnitContext | null;
  pathItem: PathItemResponse | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  if (!citation) return null;
  const title = getUnitContextUnitName(unitContext) || getCitationUnitName(citation);
  const courseId = getUnitContextCourseId(unitContext) || getCitationCourseId(citation);
  const href = getUnitContextHref(unitContext) || getCitationHref(citation);
  const summary = cleanSourceSummary(unitContext?.summary ?? citation.quote ?? "");
  const sectionTitle = pathItem?.section_title ?? getCitationLectureTitle(citation);
  const statusLabel = pathItem ? getStatusLabel(pathItem.status) : "Not in current plan";
  const duration =
    pathItem?.estimated_hours != null
      ? `${Math.max(1, Math.round(pathItem.estimated_hours * 60))} min`
      : null;

  return (
    <aside className="flex h-full w-full shrink-0 flex-col border-l border-slate-200 bg-white lg:w-[360px] xl:w-[390px]">
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-4">
        <div className="min-w-0">
          <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">Source detail</p>
          <h2 className="truncate text-sm font-black text-slate-950">{courseId}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100"
          aria-label="Close source detail"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <div>
          <p className="mb-2 text-[11px] font-black uppercase tracking-widest text-slate-400">Learning unit</p>
          <h3 className="text-xl font-black leading-tight text-slate-950">{title}</h3>
          {sectionTitle ? <p className="mt-2 text-sm font-semibold leading-6 text-slate-500">{sectionTitle}</p> : null}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <div className="mb-2 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Status
            </div>
            <p className="text-sm font-black text-slate-900">{statusLabel}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <div className="mb-2 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
              <Clock className="h-3.5 w-3.5" />
              Duration
            </div>
            <p className="text-sm font-black text-slate-900">{duration ?? "Unknown"}</p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
            <BookOpen className="h-3.5 w-3.5" />
            Summary
          </div>
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              Loading source context
            </div>
          ) : error ? (
            <p className="text-sm leading-6 text-amber-700">{error}</p>
          ) : summary ? (
            <p className="text-sm leading-6 text-slate-600">{summary}</p>
          ) : (
            <p className="text-sm leading-6 text-slate-500">No summary is available for this source yet.</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="mb-2 text-[11px] font-black uppercase tracking-widest text-slate-400">Quiz</p>
            <p className="text-sm font-black text-slate-900">
              {getUnitContextQuizAvailable(unitContext) || pathItem?.has_quiz_items ? "Available" : "Not available"}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="mb-2 text-[11px] font-black uppercase tracking-widest text-slate-400">Course</p>
            <p className="truncate text-sm font-black text-slate-900">{courseId}</p>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-200 p-4">
        {href ? (
          <Link
            href={href}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 px-4 text-sm font-black text-white shadow-lg shadow-blue-200 transition hover:bg-blue-700"
          >
            Start learning
            <ArrowRight className="h-4 w-4" />
          </Link>
        ) : (
          <button
            type="button"
            disabled
            className="min-h-12 w-full rounded-2xl bg-slate-100 px-4 text-sm font-black text-slate-400"
          >
            Learning link unavailable
          </button>
        )}
      </div>
    </aside>
  );
}

function PrerequisitePath({ unitIds }: { unitIds: string[] }) {
  if (unitIds.length === 0) return null;
  return (
    <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="mb-4 flex items-center gap-2 text-sm font-black text-slate-900">
        <Map className="h-4 w-4 text-blue-600" />
        Suggested prerequisite order
      </div>
      <div className="space-y-4">
        {unitIds.map((unitId, index) => (
          <div key={unitId} className="relative flex gap-3">
            {index < unitIds.length - 1 ? (
              <div className="absolute left-[7px] top-6 h-8 border-l-2 border-dotted border-slate-300" />
            ) : null}
            <span className="relative z-10 mt-1 h-4 w-4 rounded-full border-2 border-blue-500 bg-white" />
            <div>
              <p className="text-sm font-bold text-slate-800">Review {unitId}</p>
              <p className="text-xs text-slate-500">Grounded prerequisite candidate from the path graph.</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AssessmentProposalCard({
  workflow,
  onResume,
}: {
  workflow: AgentAssessmentWorkflowResponse;
  onResume: (workflowId: string, decision: { action: "approve" | "reduce" | "reject"; reductionId?: string; questionBudget?: number }) => Promise<void>;
}) {
  const [isBusy, setIsBusy] = useState(false);
  const proposal = workflow.interrupt;
  const workflowId = getWorkflowId(workflow);

  if (!proposal) {
    return (
      <div className="mt-3 rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-sm font-semibold text-slate-900">Assessment workflow: {workflow.status}</p>
        {workflow.actions.map((action) => (
          <ActionButton key={`${action.type}-${action.label}`} action={action} />
        ))}
      </div>
    );
  }

  const questionCount = getProposalQuestionCount(proposal);
  const minutes = getProposalMinutes(proposal);
  const mix = getProposalDifficultyMix(proposal);
  const reductions = getProposalReductionOptions(proposal);
  const totalMix = (Object.values(mix).reduce((sum: number, value) => sum + Number(value), 0) as number) || 1;

  const runDecision = async (decision: { action: "approve" | "reduce" | "reject"; reductionId?: string; questionBudget?: number }) => {
    if (!workflowId) return;
    setIsBusy(true);
    try {
      await onResume(workflowId, decision);
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <div className="mt-4 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-200/60">
      <div className="border-b border-slate-100 bg-slate-50/80 p-5">
        <span className="rounded-full bg-blue-50 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-blue-700">
          Assessment proposal
        </span>
        <h3 className="mt-4 text-xl font-black tracking-tight text-slate-950">{proposal.title}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">{proposal.purpose}</p>
      </div>
      <div className="space-y-6 p-5">
        <div className="flex gap-10">
          <div>
            <p className="text-4xl font-black tracking-tighter text-slate-950">{questionCount}</p>
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">questions</p>
          </div>
          <div>
            <p className="text-2xl font-black tracking-tight text-slate-950">{minutes} min</p>
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">estimated</p>
          </div>
        </div>

        <div>
          <h4 className="mb-3 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
            <Target className="h-4 w-4" />
            Scope
          </h4>
          <div className="space-y-3">
            {proposal.scope.map((scope) => (
              <div key={scope.label} className="flex gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-xs font-black text-slate-600">
                  {getScopeUnitCount(scope)}
                </span>
                <div>
                  <p className="text-sm font-bold text-slate-900">{scope.label}</p>
                  <p className="text-xs leading-5 text-slate-500">{scope.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="mb-3 text-[11px] font-black uppercase tracking-widest text-slate-400">Difficulty mix</h4>
          <div className="flex h-2 overflow-hidden rounded-full bg-slate-100">
            {Object.entries(mix).map(([level, count]) => (
              <div
                key={level}
                className={cn(
                  "h-full",
                  level === "easy" && "bg-green-400",
                  level === "medium" && "bg-blue-400",
                  level === "hard" && "bg-orange-400",
                  level === "application" && "bg-purple-400",
                )}
                style={{ width: `${(Number(count) / totalMix) * 100}%` }}
              />
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            {Object.entries(mix).map(([level, count]) => (
              <span key={level}>
                {level}: {count}
              </span>
            ))}
          </div>
        </div>

        {reductions.length > 0 ? (
          <div className="grid gap-2">
            {reductions.map((option) => (
              <button
                key={option.id}
                type="button"
                disabled={isBusy}
                onClick={() => runDecision({ action: "reduce", reductionId: option.id })}
                className="rounded-2xl border border-slate-200 p-3 text-left transition hover:border-blue-300 hover:bg-blue-50 disabled:opacity-60"
              >
                <span className="block text-sm font-black text-slate-900">{option.label}</span>
                <span className="mt-1 block text-xs leading-5 text-slate-500">
                  {option.effect} New estimate: {getReductionQuestionCount(option)} questions.
                </span>
              </button>
            ))}
          </div>
        ) : null}

        <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
          <button
            type="button"
            disabled={isBusy}
            onClick={() => runDecision({ action: "approve" })}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-blue-600 px-5 text-sm font-black uppercase tracking-widest text-white shadow-lg shadow-blue-200 transition hover:bg-blue-700 disabled:opacity-60"
          >
            {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <BarChart3 className="h-4 w-4" />}
            Approve assessment
          </button>
          <button
            type="button"
            disabled={isBusy}
            onClick={() => runDecision({ action: "reject" })}
            className="min-h-12 rounded-2xl border border-slate-200 px-5 text-sm font-bold text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}

function ActionButton({
  action,
  conversationId,
  onActionResponse,
}: {
  action: AgentAction;
  conversationId?: string | null;
  onActionResponse?: (response: AgentChatResponse) => void;
}) {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const href = getCitationHref(action);
  const actionId = getActionId(action);
  const disabledReason = getActionDisabledReason(action);
  const disabled = action.eligible === false || Boolean(disabledReason);
  const isPendingConfirmation = action.status === "awaiting_confirmation" && Boolean(actionId);

  const continuePendingAction = async (decision: "approve" | "reject") => {
    if (!conversationId || !actionId || disabled || !onActionResponse) return;
    setIsStarting(true);
    setStartError(null);
    try {
      const response = await agentApi.continueAction({
        conversationId,
        actionId,
        decision,
        incomingMessageId: createIncomingMessageId(),
      });
      onActionResponse(response);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : "Action could not be completed.");
    } finally {
      setIsStarting(false);
    }
  };

  const startAssessment = async () => {
    if (disabled || action.type !== "start_assessment") return;
    const canonicalUnitIds = getActionCanonicalIds(action);
    if (canonicalUnitIds.length === 0) return;
    setIsStarting(true);
    setStartError(null);
    try {
      const response = await agentApi.startAssessmentAction({
        canonicalUnitIds,
        phase: action.defaultPhase ?? action.default_phase ?? "skip_verification",
        reason: "agent_assessment_workflow_approved",
        questionBudget: getActionQuestionBudget(action),
      });
      if (!response.accepted || !response.impact) {
        throw new Error(response.rejectedReason ?? response.rejected_reason ?? "Assessment could not be started.");
      }
      const impact = response.impact as {
        sessionId?: string;
        totalQuestions?: number;
        questions?: unknown[];
        canonicalUnitIds?: string[];
        href?: string;
      };
      if (!impact.sessionId || !Array.isArray(impact.questions)) {
        throw new Error("Assessment response did not include a usable session.");
      }
      writeStartedCanonicalAssessment({
        sessionId: impact.sessionId,
        questions: impact.questions as QuestionForAssessment[],
        canonicalUnitIds: impact.canonicalUnitIds ?? canonicalUnitIds,
        unitNameMap: {},
      });
      router.push(impact.href ?? "/assessment");
    } catch (err) {
      setStartError(err instanceof Error ? err.message : "Assessment could not be started.");
    } finally {
      setIsStarting(false);
    }
  };

  const chooseTargetPath = async () => {
    const targetPathId = getWorkflowId(action);
    if (!conversationId || !targetPathId || disabled || !onActionResponse) return;
    setIsStarting(true);
    setStartError(null);
    try {
      const response = await agentApi.chat({
        message: `choose_path:${targetPathId}`,
        incomingMessageId: createIncomingMessageId(),
        conversationId,
        traceMode: "summary",
      });
      onActionResponse(response);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : "Path selection could not be completed.");
    } finally {
      setIsStarting(false);
    }
  };

  const content = (
    <span
      className={cn(
        "mt-2 flex min-h-12 w-full items-center justify-between gap-3 rounded-2xl border p-3 text-left text-sm font-bold transition",
        disabled
          ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
          : "border-slate-200 bg-white text-slate-900 hover:border-blue-300 hover:bg-blue-50",
      )}
    >
      <span>
        <span className="block">{action.label}</span>
        {disabledReason ? <span className="mt-0.5 block text-xs font-medium">Disabled: {disabledReason}</span> : null}
        {startError ? <span className="mt-0.5 block text-xs font-medium text-red-600">{startError}</span> : null}
      </span>
      {isStarting ? <Loader2 className="h-4 w-4 shrink-0 animate-spin" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
    </span>
  );

  if (isPendingConfirmation) {
    return (
      <div className="space-y-2">
        <button
          type="button"
          disabled={disabled || isStarting}
          onClick={() => continuePendingAction("approve")}
          className="w-full"
        >
          {content}
        </button>
        <button
          type="button"
          disabled={disabled || isStarting}
          onClick={() => continuePendingAction("reject")}
          className="min-h-10 w-full rounded-2xl border border-slate-200 px-4 text-sm font-bold text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
        >
          Not now
        </button>
      </div>
    );
  }

  if (action.type === "start_assessment") {
    return (
      <button type="button" disabled={disabled || isStarting} onClick={startAssessment} className="w-full">
        {content}
      </button>
    );
  }

  if (action.type === "choose_target_path") {
    return (
      <button type="button" disabled={disabled || isStarting} onClick={chooseTargetPath} className="w-full">
        {content}
      </button>
    );
  }

  if (!href || disabled) return <button type="button">{content}</button>;
  return <Link href={href}>{content}</Link>;
}

function WorkflowAction({ action }: { action: AgentAction }) {
  const [workflow, setWorkflow] = useState<AgentAssessmentWorkflowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const canonicalIds = getActionCanonicalIds(action);
  const disabledReason = getActionDisabledReason(action);
  const disabled = action.eligible === false || canonicalIds.length === 0 || Boolean(disabledReason);

  const start = async () => {
    if (disabled) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await agentApi.startAssessmentWorkflow({
        candidateCanonicalUnitIds: canonicalIds,
        questionBudget: Math.min(70, Math.max(10, canonicalIds.length * 4)),
        phase: action.defaultPhase ?? action.default_phase ?? "skip_verification",
      });
      setWorkflow(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not prepare assessment.");
    } finally {
      setIsLoading(false);
    }
  };

  const resume = async (
    workflowId: string,
    decision: { action: "approve" | "reduce" | "reject"; reductionId?: string; questionBudget?: number },
  ) => {
    const response = await agentApi.resumeAssessmentWorkflow(workflowId, decision);
    setWorkflow(response);
  };

  return (
    <div className="mt-3">
      {!workflow ? (
        <button
          type="button"
          disabled={disabled || isLoading}
          onClick={start}
          className="flex min-h-14 w-full items-center justify-between rounded-2xl bg-blue-600 px-4 text-left text-white shadow-lg shadow-blue-200 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
        >
          <span>
            <span className="block text-sm font-black">{action.label}</span>
            <span className="mt-0.5 block text-xs opacity-80">
              {disabledReason ?? `${canonicalIds.length} candidate units`}
            </span>
          </span>
          {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <ChevronRight className="h-5 w-5" />}
        </button>
      ) : (
        <AssessmentProposalCard workflow={workflow} onResume={resume} />
      )}
      {error ? <p className="mt-2 text-sm font-medium text-red-600">{error}</p> : null}
    </div>
  );
}

function ChatMessageItem({
  message,
  conversationId,
  onActionResponse,
  onRetry,
  onSelectCitation,
  selectedCitationKey,
}: {
  message: UiMessage;
  conversationId: string | null;
  onActionResponse: (response: AgentChatResponse) => void;
  onRetry: (message: string, incomingMessageId: string) => void;
  onSelectCitation: (citation: AgentCitation) => void;
  selectedCitationKey: string | null;
}) {
  const isUser = message.role === "user";
  const prereqAction = message.actions.find((action) => action.type === "review_prerequisite_path");
  const workflowActions = message.actions.filter(
    (action) => action.type === "start_assessment_workflow" || action.type === "continue_assessment_workflow",
  );
  const simpleActions = message.actions.filter(
    (action) =>
      action.type !== "review_prerequisite_path" &&
      !workflowActions.includes(action) &&
      !isDuplicateOpenUnitAction(action, message.citations),
  );

  return (
    <div className={cn("flex w-full gap-3", isUser && "justify-end")}>
      {!isUser ? (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white shadow-sm">
          <Bot className="h-5 w-5" />
        </div>
      ) : null}
      <div className={cn("max-w-[92%] md:max-w-[78%]", isUser && "order-first")}>
        <div
          className={cn(
            "rounded-3xl px-4 py-3 text-[15px] leading-7 shadow-sm",
            isUser
              ? "rounded-tr-md bg-slate-950 text-white"
              : "rounded-tl-md border border-slate-200 bg-white text-slate-800",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.markdown}</p>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none leading-7">
              <AssistantMarkdown markdown={message.markdown} />
            </div>
          )}
          {!isUser && message.warning && !isDuplicateWarning(message) ? <WarningBlock warning={message.warning} /> : null}
          {!isUser && !message.warning && getFallbackErrorCode(message.fallback) ? (
            <WarningBlock
              warning={{
                type: "agent_unavailable",
                message: getFallbackErrorCode(message.fallback) ?? "AGENT_ERROR",
              }}
            />
          ) : null}
          {!isUser && getFallbackErrorCode(message.fallback) && message.retryMessage && message.retryIncomingMessageId ? (
            <button
              type="button"
              onClick={() => onRetry(message.retryMessage!, message.retryIncomingMessageId!)}
              className="mt-3 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-black uppercase tracking-wider text-slate-700 shadow-sm transition hover:border-blue-300 hover:text-blue-600"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry
            </button>
          ) : null}
        </div>

        {!isUser && message.citations.length > 0 ? (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2 px-1 text-[11px] font-black uppercase tracking-widest text-slate-400">
              <Search className="h-3 w-3" />
              Sources
            </div>
            {message.citations.map((citation, index) => (
              <CitationCard
                key={citationKey(citation) || index}
                citation={citation}
                isSelected={citationKey(citation) === selectedCitationKey}
                onSelect={onSelectCitation}
              />
            ))}
          </div>
        ) : null}

        {!isUser && prereqAction ? <PrerequisitePath unitIds={getActionCanonicalIds(prereqAction)} /> : null}

        {!isUser && workflowActions.map((action) => <WorkflowAction key={`${action.type}-${action.label}`} action={action} />)}

        {!isUser && simpleActions.length > 0 ? (
          <div className="mt-3 space-y-2">
            {simpleActions.map((action, index) => (
              <ActionButton
                key={`${action.type}-${action.label}-${index}`}
                action={action}
                conversationId={conversationId}
                onActionResponse={onActionResponse}
              />
            ))}
          </div>
        ) : null}
      </div>
      {isUser ? (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500">
          <User className="h-4 w-4" />
        </div>
      ) : null}
    </div>
  );
}

function SessionSidebar({
  sessions,
  activeId,
  isMinimized,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
}: {
  sessions: AgentConversationSummary[];
  activeId: string | null;
  isMinimized: boolean;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [filter, setFilter] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [menuId, setMenuId] = useState<string | null>(null);
  const filtered = sessions.filter((session) => {
    const query = filter.trim().toLowerCase();
    if (!query) return true;
    return `${session.title} ${session.preview}`.toLowerCase().includes(query);
  });

  if (isMinimized) {
    return (
      <div className="flex h-full flex-col items-center gap-4 p-3">
        <button
          type="button"
          onClick={onNewChat}
          className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-200"
          aria-label="New chat"
        >
          <Plus className="h-5 w-5" />
        </button>
        <History className="h-5 w-5 text-slate-300" />
      </div>
    );
  }

  return (
    <aside className="flex h-full flex-col overflow-hidden bg-white">
      <div className="space-y-3 border-b border-slate-200 p-4">
        <button
          type="button"
          onClick={onNewChat}
          className="flex min-h-11 w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 text-sm font-black text-white transition hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          New chat
        </button>
        <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search chats"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
        </label>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {filtered.length === 0 ? (
          <div className="py-10 text-center text-sm font-medium text-slate-400">No chat history yet.</div>
        ) : (
          filtered.map((session) => {
            const id = getConversationId(session);
            const isActive = id === activeId;
            const isEditing = editingId === id;
            return (
              <div
                key={id}
                className={cn(
                  "group relative mb-2 rounded-2xl border p-3 transition",
                  isActive ? "border-blue-100 bg-blue-50 shadow-sm" : "border-transparent hover:bg-slate-50",
                )}
              >
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    if (!isEditing) onSelect(id);
                  }}
                  onKeyDown={(event) => {
                    if (!isEditing && (event.key === "Enter" || event.key === " ")) onSelect(id);
                  }}
                  className="w-full cursor-pointer pr-9 text-left"
                >
                  <div className="mb-1 flex items-center gap-2 text-[10px] font-black uppercase tracking-wider text-slate-400">
                    <span>{formatDateLabel(getUpdatedAt(session))}</span>
                    <span>{session.messageCount ?? session.message_count ?? 0} messages</span>
                  </div>
                  {isEditing ? (
                    <form
                      onSubmit={async (event) => {
                        event.preventDefault();
                        const value = editingTitle.trim();
                        if (value) await onRename(id, value);
                        setEditingId(null);
                        setMenuId(null);
                      }}
                      className="flex items-center gap-1"
                    >
                      <input
                        value={editingTitle}
                        onChange={(event) => setEditingTitle(event.target.value)}
                        onClick={(event) => event.stopPropagation()}
                        autoFocus
                        className="min-w-0 flex-1 rounded-lg border border-blue-200 bg-white px-2 py-1 text-sm font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                      <button
                        type="submit"
                        className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white"
                        aria-label="Save chat title"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                    </form>
                  ) : (
                    <p className={cn("truncate text-sm font-black", isActive ? "text-blue-700" : "text-slate-900")}>
                      {session.title || "New chat"}
                    </p>
                  )}
                  <p className="mt-1 truncate text-xs font-medium text-slate-500">{session.preview || "No messages yet"}</p>
                </div>
                {!isEditing ? (
                  <div className="absolute right-2 top-2">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        setMenuId((current) => (current === id ? null : id));
                      }}
                      className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 opacity-100 transition hover:bg-white hover:text-slate-700 lg:opacity-0 lg:group-hover:opacity-100"
                      aria-label="Chat actions"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                    {menuId === id ? (
                      <div className="absolute right-0 z-20 mt-1 w-36 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 text-sm font-semibold text-slate-700 shadow-xl">
                        <button
                          type="button"
                          onClick={() => {
                            setEditingId(id);
                            setEditingTitle(session.title || "New chat");
                          }}
                          className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-slate-50"
                        >
                          <Pencil className="h-4 w-4" />
                          Rename
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            setMenuId(null);
                            await onDelete(id);
                          }}
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="h-4 w-4" />
                          Delete
                        </button>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}

function EmptyState({ onPrompt }: { onPrompt: (prompt: string) => void }) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl border border-blue-100 bg-blue-50 text-blue-600 shadow-sm">
        <Bot className="h-10 w-10" />
      </div>
      <h1 className="text-3xl font-black tracking-tight text-slate-950">AI Assistant</h1>
      <p className="mt-3 max-w-md text-sm leading-6 text-slate-500">
        Ask about concepts, prerequisites, where to review something, or whether an assessment can shorten your plan.
      </p>
      <div className="mt-8 grid w-full max-w-xl gap-3 sm:grid-cols-2">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onPrompt(prompt)}
            className="rounded-2xl border border-slate-200 bg-white p-4 text-left text-sm font-bold text-slate-800 shadow-sm transition hover:border-blue-300 hover:bg-blue-50"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function Composer({ onSend, disabled }: { onSend: (message: string) => void; disabled: boolean }) {
  const [text, setText] = useState("");
  const send = (event?: FormEvent) => {
    event?.preventDefault();
    const value = text.trim();
    if (!value || disabled) return;
    setText("");
    onSend(value);
  };

  return (
    <div className="border-t border-slate-200 bg-white/95 p-4 backdrop-blur">
      <div className="mx-auto max-w-3xl">
        <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={disabled}
              onClick={() => onSend(prompt)}
              className="shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600 transition hover:border-blue-300 hover:bg-blue-50 disabled:opacity-60"
            >
              {prompt}
            </button>
          ))}
        </div>
        <form onSubmit={send} className="relative flex items-end">
          <label htmlFor="agent-message" className="sr-only">
            Message AI Assistant
          </label>
          <div className="relative flex-1 flex items-center w-full">
            <textarea
              id="agent-message"
              value={text}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  send(event);
                }
              }}
              placeholder="Message AI Assistant..."
              rows={1}
              className="max-h-32 min-h-[48px] w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 py-3 pl-4 pr-14 text-[15px] leading-relaxed shadow-inner outline-none transition-all placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
            <button
              type="submit"
              disabled={disabled || !text.trim()}
              className="absolute right-1.5 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg shadow-blue-200/50 transition-all hover:bg-blue-700 active:scale-95 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-300 disabled:shadow-none"
              aria-label="Send message"
            >
              <Send className="h-[18px] w-[18px]" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function TurnProgress({ stepIndex }: { stepIndex: number }) {
  return (
    <div className="flex gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
        <Bot className="h-5 w-5" />
      </div>
      <div className="min-w-[260px] rounded-3xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
          {TURN_PROGRESS_STEPS[Math.min(stepIndex, TURN_PROGRESS_STEPS.length - 1)]}
        </div>
        <div className="space-y-2">
          {TURN_PROGRESS_STEPS.map((step, index) => {
            const state =
              index < stepIndex ? "done" : index === Math.min(stepIndex, TURN_PROGRESS_STEPS.length - 1) ? "active" : "pending";
            return (
              <div key={step} className="flex items-center gap-2 text-xs font-semibold">
                <span
                  className={cn(
                    "flex h-4 w-4 items-center justify-center rounded-full border",
                    state === "done" && "border-blue-600 bg-blue-600 text-white",
                    state === "active" && "border-blue-600 bg-blue-50 text-blue-600",
                    state === "pending" && "border-slate-200 bg-slate-50 text-slate-300",
                  )}
                >
                  {state === "done" ? <Check className="h-3 w-3" /> : null}
                </span>
                <span className={cn(state === "pending" ? "text-slate-400" : "text-slate-700")}>{step}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function AgentChatPage() {
  const { user } = useAuthStore();
  const userId = user?.id ?? null;
  const [sessions, setSessions] = useState<AgentConversationSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [turnProgressIndex, setTurnProgressIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [leftOpen, setLeftOpen] = useState(false);
  const [leftMinimized, setLeftMinimized] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<AgentCitation | null>(null);
  const [selectedUnitContext, setSelectedUnitContext] = useState<AgentUnitContext | null>(null);
  const [selectedPathItem, setSelectedPathItem] = useState<PathItemResponse | null>(null);
  const [isLoadingSourceDetail, setIsLoadingSourceDetail] = useState(false);
  const [sourceDetailError, setSourceDetailError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const skipNextMessageLoadForSession = useRef<string | null>(null);

  useEffect(() => {
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
    setSelectedCitation(null);
    setSelectedUnitContext(null);
    setSelectedPathItem(null);
    skipNextMessageLoadForSession.current = null;
    if (!userId) {
      setIsLoadingSessions(false);
      return;
    }
    let active = true;
    setIsLoadingSessions(true);
    agentApi
      .listConversations()
      .then((items: AgentConversationSummary[]) => {
        if (!active) return;
        setSessions(items);
        if (items.length > 0) {
          setActiveSessionId(getConversationId(items[0]));
        }
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Could not load conversations.");
      })
      .finally(() => {
        if (active) setIsLoadingSessions(false);
      });
    return () => {
      active = false;
    };
  }, [userId]);

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      setSelectedCitation(null);
      setSelectedUnitContext(null);
      setSelectedPathItem(null);
      return;
    }
    setSelectedCitation(null);
    setSelectedUnitContext(null);
    setSelectedPathItem(null);
    if (skipNextMessageLoadForSession.current === activeSessionId) {
      skipNextMessageLoadForSession.current = null;
      setIsLoadingMessages(false);
      return;
    }
    let active = true;
    setIsLoadingMessages(true);
    agentApi
      .messages(activeSessionId)
      .then((loadedMessages) => {
        if (!active) return;
        setMessages(toUiMessages(loadedMessages));
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Could not load this conversation.");
      })
      .finally(() => {
        if (active) setIsLoadingMessages(false);
      });
    return () => {
      active = false;
    };
  }, [activeSessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    if (!isThinking) {
      setTurnProgressIndex(0);
      return;
    }
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      setTurnProgressIndex(Math.min(TURN_PROGRESS_STEPS.length - 1, Math.floor(elapsed / 1200)));
    }, 350);
    return () => window.clearInterval(timer);
  }, [isThinking]);

  const activeSession = useMemo(
    () => sessions.find((session) => getConversationId(session) === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

  const refreshSessions = () => {
    agentApi.listConversations().then(setSessions).catch(() => undefined);
  };

  const renameSession = async (id: string, title: string) => {
    const updated = await agentApi.renameConversation(id, title);
    setSessions((current) => current.map((session) => (getConversationId(session) === id ? updated : session)));
  };

  const deleteSession = async (id: string) => {
    if (!window.confirm("Delete this agent chat history? This will not delete your learning progress.")) return;
    await agentApi.deleteConversation(id);
    const remaining = sessions.filter((session) => getConversationId(session) !== id);
    setSessions(remaining);
    if (activeSessionId === id) {
      setActiveSessionId(remaining[0] ? getConversationId(remaining[0]) : null);
      setMessages([]);
      setSelectedCitation(null);
      setSelectedUnitContext(null);
      setSelectedPathItem(null);
    }
  };

  const selectCitation = async (citation: AgentCitation) => {
    const canonicalId = getCitationCanonicalId(citation);
    setSelectedCitation(citation);
    setSelectedUnitContext(null);
    setSelectedPathItem(null);
    setSourceDetailError(null);
    if (!canonicalId) {
      setSourceDetailError("This source does not expose a unit id yet.");
      return;
    }
    setIsLoadingSourceDetail(true);
    const [contextResult, pathResult] = await Promise.allSettled([
      agentApi.unitContext(canonicalId),
      learningPathApi.getLearningPath(),
    ]);
    if (contextResult.status === "fulfilled") {
      setSelectedUnitContext(contextResult.value);
    } else {
      setSourceDetailError("Could not load the full source context.");
    }
    if (pathResult.status === "fulfilled") {
      setSelectedPathItem(findPathItemForCitation(citation, pathResult.value.items));
    }
    setIsLoadingSourceDetail(false);
  };

  const appendAgentResponse = (
    response: AgentChatResponse,
    retry?: { message: string; incomingMessageId: string },
  ) => {
    const conversationId = getConversationId(response);
    if (conversationId && conversationId !== activeSessionId) {
      skipNextMessageLoadForSession.current = conversationId;
      setActiveSessionId(conversationId);
    }
    setMessages((current) => [
      ...current,
      {
        id: getMessageId(response) || `assistant-${Date.now()}`,
        role: "assistant",
        markdown: response.answer.markdown,
        createdAt: new Date().toISOString(),
        confidence: response.answer.confidence,
        citations: response.citations ?? [],
        actions: response.actions ?? [],
        warning: response.warning,
        fallback: response.fallback,
        retryMessage: getFallbackErrorCode(response.fallback) ? retry?.message : undefined,
        retryIncomingMessageId: getFallbackErrorCode(response.fallback) ? retry?.incomingMessageId : undefined,
      },
    ]);
    refreshSessions();
  };

  const newChat = async () => {
    setError(null);
    try {
      const session = await agentApi.createConversation();
      const id = getConversationId(session);
      setSessions((current) => [session, ...current.filter((item) => getConversationId(item) !== id)]);
      setActiveSessionId(id);
      setMessages([]);
      setSelectedCitation(null);
      setSelectedUnitContext(null);
      setSelectedPathItem(null);
      setLeftOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create a new chat.");
    }
  };

  const sendMessage = async (
    message: string,
    options: { incomingMessageId?: string; appendUser?: boolean } = {},
  ) => {
    setError(null);
    const incomingMessageId = options.incomingMessageId ?? createIncomingMessageId();
    if (options.appendUser !== false) {
      const userMessage: UiMessage = {
        id: `local-${Date.now()}`,
        role: "user",
        markdown: message,
        createdAt: new Date().toISOString(),
        incomingMessageId,
        citations: [],
        actions: [],
      };
      setMessages((current) => [...current, userMessage]);
    }
    setTurnProgressIndex(0);
    setIsThinking(true);
    try {
      const response = await agentApi.chat({
        message,
        incomingMessageId,
        conversationId: activeSessionId,
        traceMode: "summary",
      });
      appendAgentResponse(response, { message, incomingMessageId });
    } catch (err) {
      setMessages((current) => [
        ...current,
        buildAgentClientErrorMessage(err, { message, incomingMessageId }),
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  const mobileLeft = (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/50"
        onClick={() => setLeftOpen(false)}
        aria-label="Close chat history"
      />
      <div className="absolute bottom-0 left-0 top-0 w-[290px] border-r border-slate-200 bg-white shadow-2xl">
        <SessionSidebar
          sessions={sessions}
          activeId={activeSessionId}
          onSelect={(id) => {
            setActiveSessionId(id);
            setLeftOpen(false);
          }}
          onNewChat={newChat}
          onRename={renameSession}
          onDelete={deleteSession}
          isMinimized={false}
        />
      </div>
    </div>
  );

  return (
    <div className="flex h-full min-h-0 overflow-hidden bg-slate-50">
      <div className={cn("hidden shrink-0 border-r border-slate-200 bg-white transition-all lg:block", leftMinimized ? "w-20" : "w-72")}>
        <SessionSidebar
          sessions={sessions}
          activeId={activeSessionId}
          onSelect={setActiveSessionId}
          onNewChat={newChat}
          onRename={renameSession}
          onDelete={deleteSession}
          isMinimized={leftMinimized}
        />
      </div>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setLeftOpen(true)}
              className="flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 hover:bg-slate-100 lg:hidden"
              aria-label="Open chat history"
            >
              <Menu className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => setLeftMinimized((value) => !value)}
              className="hidden h-10 w-10 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-100 lg:flex"
              aria-label={leftMinimized ? "Expand chat history" : "Collapse chat history"}
            >
              {leftMinimized ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            </button>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-black tracking-tight text-slate-950">AI Assistant</h1>
              <p className="truncate text-xs font-bold uppercase tracking-widest text-slate-400">
                {activeSession?.title || "Learning planner chat"} · {user?.full_name || "Learner"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isLoadingSessions ? <Loader2 className="h-4 w-4 animate-spin text-slate-400" /> : null}
          </div>
        </header>

        <main ref={scrollRef} className="relative flex-1 overflow-y-auto">
          <div className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{ backgroundImage: "radial-gradient(circle, #1e293b 1px, transparent 1px)", backgroundSize: "28px 28px" }} />
          <div className="relative mx-auto max-w-4xl space-y-6 px-4 py-8">
            {error ? (
              <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-medium text-red-700">
                {error}
              </div>
            ) : null}
            {isLoadingMessages ? (
              <div className="flex min-h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              </div>
            ) : messages.length === 0 ? (
              <EmptyState onPrompt={sendMessage} />
            ) : (
              <>
                {messages.map((message) => (
                  <ChatMessageItem
                    key={message.id}
                    message={message}
                    conversationId={activeSessionId}
                    onActionResponse={appendAgentResponse}
                    onSelectCitation={selectCitation}
                    selectedCitationKey={selectedCitation ? citationKey(selectedCitation) : null}
                    onRetry={(retryMessage, retryIncomingMessageId) =>
                      sendMessage(retryMessage, {
                        incomingMessageId: retryIncomingMessageId,
                        appendUser: false,
                      })
                    }
                  />
                ))}
                {isThinking ? (
                  <TurnProgress stepIndex={turnProgressIndex} />
                ) : null}
              </>
            )}
          </div>
        </main>

        <Composer onSend={sendMessage} disabled={isThinking} />
      </section>

      {selectedCitation ? (
        <div className="hidden h-full w-[360px] shrink-0 md:block xl:w-[390px]" data-testid="agent-source-sidebar">
          <SourceDetailPanel
            citation={selectedCitation}
            unitContext={selectedUnitContext}
            pathItem={selectedPathItem}
            isLoading={isLoadingSourceDetail}
            error={sourceDetailError}
            onClose={() => setSelectedCitation(null)}
          />
        </div>
      ) : null}

      {selectedCitation ? (
        <div className="fixed inset-0 z-50 md:hidden" data-testid="agent-source-drawer">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/50"
            onClick={() => setSelectedCitation(null)}
            aria-label="Close source detail"
          />
          <div className="absolute bottom-0 right-0 top-0 w-full max-w-[390px] bg-white shadow-2xl">
            <SourceDetailPanel
              citation={selectedCitation}
              unitContext={selectedUnitContext}
              pathItem={selectedPathItem}
              isLoading={isLoadingSourceDetail}
              error={sourceDetailError}
              onClose={() => setSelectedCitation(null)}
            />
          </div>
        </div>
      ) : null}

      {leftOpen ? mobileLeft : null}
    </div>
  );
}
