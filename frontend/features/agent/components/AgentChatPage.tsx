"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
  AlertTriangle,
  ArrowRight,
  ArrowUp,
  BarChart3,
  BookOpen,
  Bot,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  Check,
  Clock,
  History,
  Info,
  Loader2,
  Map,
  Menu,
  MoreVertical,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Sparkles,
  Square,
  Target,
  Trash2,
  User,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  CHAT_MODEL_OPTIONS,
  CHAT_MODEL_STORAGE_KEYS,
  DEFAULT_CHAT_MODEL_AVAILABILITY,
  fallbackUnavailableChatModel,
  getChatModelAvailability,
  isChatModelAvailable,
  readStoredChatModelId,
  writeStoredChatModelId,
  type ChatModelAvailability,
  type ChatModelId,
} from "@/lib/chat-model-options";
import { useAuthStore } from "@/stores/authStore";
import {
  createLearningProfileForPath,
  SUPPORTED_LEARNING_PATHS,
  type PlannerPathKey,
} from "@/features/learning-path/profile";
import { useLearningPathStore } from "@/features/learning-path/store";
import {
  agentApi,
  getActionCanonicalId,
  getActionCanonicalIds,
  getActionDisabledReason,
  getActionPrerequisitePath,
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
  getPrerequisiteNodeCanonicalId,
  getPrerequisiteNodeHref,
  getPrerequisiteNodeMasteryLcb,
  getPrerequisiteNodeName,
  getReductionQuestionCount,
  getScopeUnitCount,
  getUnitContextCourseId,
  getUnitContextHref,
  getUnitContextQuizAvailable,
  getUnitContextUnitName,
  getUpdatedAt,
  getWorkflowId,
  isStreamChunk,
  isStreamDone,
  isStreamStatus,
  isStreamThought,
  type AgentAction,
  type AgentPrerequisitePathNode,
  type AgentAssessmentWorkflowResponse,
  type AgentChatResponse,
  type AgentCitation,
  type AgentConversationMessage,
  type AgentConversationSummary,
  type AgentToolMode,
  type AgentUnitContext,
  type AgentWarning,
  type AssessmentProposal,
} from "@/features/agent/api";
import { readAgentRouteContext } from "@/features/agent/route-context";
import {
  applyAgentActivityStatus,
  applyAgentActivityThought,
  completeAgentActivity,
  createAgentActivity,
  getAgentActivityElapsedMs,
  getAgentActivityHeader,
  type AgentActivitySnapshot,
} from "@/features/agent/lib/activity";
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
  activity?: AgentActivitySnapshot;
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

function AssistantMarkdown({ markdown, citations = [] }: { markdown: string; citations?: AgentCitation[] }) {
  const allowedExternalHrefs = new Set(
    citations
      .filter(isExternalCitation)
      .map((citation) => getCitationHref(citation))
      .filter((href): href is string => Boolean(href)),
  );
  return (
    <ReactMarkdown
      components={{
        a: ({ children, href }) =>
          href && allowedExternalHrefs.has(href) ? (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-primary-700 underline decoration-primary-300 underline-offset-2 transition hover:text-primary-900 dark:text-primary-300"
            >
              {children}
            </a>
          ) : (
            <span>{children}</span>
          ),
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
  "Show me the prerequisite chain for Mask R-CNN",
  "I want to optimize my learning path",
  "Can I switch to another path?",
];

const COPILOT_BENEFITS = ["Path-aware", "Source-backed", "Actionable next steps"];

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
      ? "state-warning border"
      : warning.type === "ambiguous_target"
        ? "border-border-subtle bg-surface-page text-text-body"
        : warning.type === "agent_unavailable"
          ? "state-error border"
          : "insight-card";
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

function isExternalCitation(citation: AgentCitation) {
  const source = citation.source?.toLowerCase();
  const courseId = getCitationCourseId(citation).toUpperCase();
  const canonicalId = getCitationCanonicalId(citation);
  return (
    source === "web" ||
    source === "paper" ||
    courseId === "WEB" ||
    courseId === "PAPER" ||
    canonicalId.startsWith("external::")
  );
}

function getCitationPathTags(citation: AgentCitation) {
  const courseId = getCitationCourseId(citation).toLowerCase();
  if (courseId === "cs230") return ["CV", "NLP"];
  if (courseId === "cs231n") return ["CV"];
  if (courseId === "cs224n") return ["NLP"];
  return [];
}

function getCitationPathTagClass(tag: string) {
  if (tag === "CV") {
    return "border-amber-200 bg-amber-100 text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200";
  }
  return "border-sky-200 bg-sky-100 text-sky-800 dark:border-sky-800/60 dark:bg-sky-950/40 dark:text-sky-200";
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
  const pathTags = getCitationPathTags(citation);
  return (
    <button
      type="button"
      onClick={() => onSelect(citation)}
      className={cn(
        "group block w-full rounded-2xl border bg-surface-card p-3 text-left transition hover:border-primary-200 hover:bg-surface-accent-soft/40 hover:shadow-brand-soft focus:outline-none focus:ring-2 focus:ring-primary-600/20",
        isSelected ? "border-primary-200 shadow-brand-soft" : "border-border-subtle",
      )}
      aria-label={`View source details: ${getCitationUnitName(citation)}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-surface-accent-soft px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary-700 dark:text-primary-300">
              {getCitationCourseId(citation)}
            </span>
            {pathTags.map((pathTag) => (
              <span
                key={pathTag}
                className={cn(
                  "rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase",
                  getCitationPathTagClass(pathTag),
                )}
              >
                {pathTag}
              </span>
            ))}
          </div>
          <h4 className="line-clamp-2 text-sm font-semibold leading-snug text-text-strong group-hover:text-primary-700 dark:group-hover:text-primary-300">
            {getCitationUnitName(citation)}
          </h4>
          {getCitationLectureTitle(citation) ? (
            <p className="mt-1 line-clamp-1 text-xs font-medium text-text-muted">
              {getCitationLectureTitle(citation)}
            </p>
          ) : null}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-surface-page text-text-muted transition group-hover:bg-surface-accent-soft group-hover:text-primary-700">
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
    <aside className="flex h-full w-full shrink-0 flex-col border-l border-border-subtle bg-surface-card lg:w-[360px] xl:w-[390px]">
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-border-subtle px-4">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-widest text-primary-700 dark:text-primary-300">Evidence</p>
          <h2 className="truncate text-sm font-semibold text-text-strong">{courseId}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-text-muted transition hover:bg-surface-page"
          aria-label="Close source detail"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-text-muted">Learning unit</p>
          <h3 className="text-xl font-semibold leading-tight text-text-strong">{title}</h3>
          {sectionTitle ? <p className="mt-2 text-sm font-medium leading-6 text-text-body">{sectionTitle}</p> : null}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-border-subtle bg-surface-page p-3">
            <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-text-muted">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Status
            </div>
            <p className="text-sm font-semibold text-text-strong">{statusLabel}</p>
          </div>
          <div className="rounded-2xl border border-border-subtle bg-surface-page p-3">
            <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-text-muted">
              <Clock className="h-3.5 w-3.5" />
              Duration
            </div>
            <p className="text-sm font-semibold text-text-strong">{duration ?? "Unknown"}</p>
          </div>
        </div>

        <div className="insight-card p-4">
          <div className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest">
            <BookOpen className="h-3.5 w-3.5" />
            Summary
          </div>
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading source context
            </div>
          ) : error ? (
            <p className="text-sm leading-6">{error}</p>
          ) : summary ? (
            <p className="text-sm leading-6">{summary}</p>
          ) : (
            <p className="text-sm leading-6">No summary is available for this source yet.</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-border-subtle bg-surface-page p-3">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-text-muted">Quiz</p>
            <p className="text-sm font-semibold text-text-strong">
              {getUnitContextQuizAvailable(unitContext) || pathItem?.has_quiz_items ? "Available" : "Not available"}
            </p>
          </div>
          <div className="rounded-2xl border border-border-subtle bg-surface-page p-3">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-text-muted">Course</p>
            <p className="truncate text-sm font-semibold text-text-strong">{courseId}</p>
          </div>
        </div>
      </div>

      <div className="border-t border-border-subtle p-4">
        {href ? (
          <Link
            href={href}
            className="btn-primary min-h-12 w-full px-4"
          >
            Start learning
            <ArrowRight className="h-4 w-4" />
          </Link>
        ) : (
          <button
            type="button"
            disabled
            className="min-h-12 w-full rounded-2xl bg-surface-page px-4 text-sm font-semibold text-text-muted"
          >
            Learning link unavailable
          </button>
        )}
      </div>
    </aside>
  );
}

function getPrerequisiteStatusMeta(status: AgentPrerequisitePathNode["status"] | undefined) {
  switch (status) {
    case "mastered":
      return { label: "Mastered", className: "bg-state-success-bg text-state-success-fg", icon: CheckCircle2 };
    case "completed":
      return { label: "Completed", className: "bg-state-success-bg text-state-success-fg", icon: CheckCircle2 };
    case "skipped":
      return { label: "Skipped", className: "bg-state-success-bg text-state-success-fg", icon: CheckCircle2 };
    case "in_progress":
      return { label: "In progress", className: "bg-surface-accent-soft text-primary-700", icon: Clock };
    case "target":
      return { label: "Current topic", className: "bg-surface-accent-soft text-primary-700", icon: Target };
    case "needs_review":
      return { label: "Review first", className: "bg-state-warning-bg text-state-warning-fg", icon: BookOpen };
    default:
      return { label: "Review", className: "bg-surface-page text-text-muted", icon: BookOpen };
  }
}

function PrerequisitePath({
  action,
  onSelectUnit,
}: {
  action: AgentAction;
  onSelectUnit: (node: AgentPrerequisitePathNode) => void;
}) {
  const path = getActionPrerequisitePath(action);
  const nodes =
    path?.nodes && path.nodes.length > 0
      ? path.nodes
      : getActionCanonicalIds(action).map(
        (unitId): AgentPrerequisitePathNode => ({
          canonicalUnitId: unitId,
          unitName: unitId,
          role: "prerequisite",
          status: "needs_review",
        }),
      );

  if (nodes.length === 0) return null;
  return (
    <div className="mt-3 rounded-2xl border border-border-subtle bg-surface-page p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-strong">
          <Map className="h-4 w-4 text-primary-700" />
          Suggested prerequisite order
        </div>
        <span className="shrink-0 rounded-full bg-surface-card px-2.5 py-1 text-[11px] font-semibold text-text-muted">
          {nodes.length} units
        </span>
      </div>
      <div className="space-y-4">
        {nodes.map((node, index) => {
          const unitId = getPrerequisiteNodeCanonicalId(node) || `${node.role}-${index}`;
          const unitName = getPrerequisiteNodeName(node);
          const masteryLcb = getPrerequisiteNodeMasteryLcb(node);
          const statusMeta = getPrerequisiteStatusMeta(node.status);
          const StatusIcon = statusMeta.icon;
          const canOpenSource = Boolean(getPrerequisiteNodeCanonicalId(node));
          return (
            <div key={`${unitId}-${index}`} className="relative flex gap-3">
              {index < nodes.length - 1 ? (
                <div className="absolute left-[13px] top-9 h-9 border-l-2 border-dotted border-border-subtle" />
              ) : null}
              <span
                className={cn(
                  "relative z-10 mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border bg-surface-card",
                  node.role === "target" ? "border-primary-500 text-primary-700" : "border-border-subtle text-text-muted",
                )}
              >
                {index < nodes.length - 1 ? <ArrowRight className="h-3.5 w-3.5" /> : <Target className="h-3.5 w-3.5" />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  {canOpenSource ? (
                    <button
                      type="button"
                      onClick={() => onSelectUnit(node)}
                      className="text-left text-sm font-semibold text-text-strong transition hover:text-primary-700"
                      aria-label={`View source details: ${unitName}`}
                    >
                      {unitName}
                    </button>
                  ) : (
                    <p className="text-sm font-semibold text-text-strong">{unitName}</p>
                  )}
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold",
                      statusMeta.className,
                    )}
                  >
                    <StatusIcon className="h-3 w-3" />
                    {statusMeta.label}
                  </span>
                  {masteryLcb !== null && node.status === "mastered" ? (
                    <span className="text-[11px] font-medium text-text-muted">{Math.round(masteryLcb * 100)}% mastery</span>
                  ) : null}
                </div>
                {node.reason ? <p className="mt-1 text-xs leading-5 text-text-muted">{node.reason}</p> : null}
              </div>
            </div>
          );
        })}
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
      <div className="mt-3 rounded-2xl border border-border-subtle bg-surface-card p-4">
        <p className="text-sm font-semibold text-text-strong">Assessment workflow: {workflow.status}</p>
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
    <div className="card-glass mt-4 overflow-hidden p-0">
      <div className="border-b border-border-subtle bg-surface-page/80 p-5">
        <span className="rounded-full bg-surface-accent-soft px-3 py-1 text-[11px] font-bold uppercase tracking-widest text-primary-700 dark:text-primary-300">
          Assessment proposal
        </span>
        <h3 className="mt-4 text-xl font-semibold tracking-tight text-text-strong">{proposal.title}</h3>
        <p className="mt-2 text-sm leading-6 text-text-body">{proposal.purpose}</p>
      </div>
      <div className="space-y-6 p-5">
        <div className="flex gap-10">
          <div>
            <p className="text-4xl font-semibold tracking-tighter text-text-strong">{questionCount}</p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-text-muted">questions</p>
          </div>
          <div>
            <p className="text-2xl font-semibold tracking-tight text-text-strong">{minutes} min</p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-text-muted">estimated</p>
          </div>
        </div>

        <div>
          <h4 className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-text-muted">
            <Target className="h-4 w-4" />
            Scope
          </h4>
          <div className="space-y-3">
            {proposal.scope.map((scope) => (
              <div key={scope.label} className="flex gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-surface-accent-soft text-xs font-bold text-primary-700">
                  {getScopeUnitCount(scope)}
                </span>
                <div>
                  <p className="text-sm font-semibold text-text-strong">{scope.label}</p>
                  <p className="text-xs leading-5 text-text-muted">{scope.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="mb-3 text-[11px] font-bold uppercase tracking-widest text-text-muted">Difficulty mix</h4>
          <div className="flex h-2 overflow-hidden rounded-full bg-surface-page">
            {Object.entries(mix).map(([level, count]) => (
              <div
                key={level}
                className={cn(
                  "h-full",
                  level === "easy" && "bg-state-success-fg",
                  level === "medium" && "bg-state-warning-fg",
                  level === "hard" && "bg-state-error-fg",
                  level === "application" && "bg-bloom-apply",
                )}
                style={{ width: `${(Number(count) / totalMix) * 100}%` }}
              />
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-[10px] font-bold uppercase tracking-wider text-text-muted">
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
                className="rounded-2xl border border-border-subtle bg-surface-card p-3 text-left transition hover:border-primary-200 hover:bg-surface-accent-soft/40 disabled:opacity-60"
              >
                <span className="block text-sm font-semibold text-text-strong">{option.label}</span>
                <span className="mt-1 block text-xs leading-5 text-text-muted">
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
            className="btn-primary min-h-12 px-5 text-sm uppercase tracking-widest disabled:opacity-60"
          >
            {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <BarChart3 className="h-4 w-4" />}
            Approve assessment
          </button>
          <button
            type="button"
            disabled={isBusy}
            onClick={() => runDecision({ action: "reject" })}
            className="btn-secondary min-h-12 px-5 text-sm disabled:opacity-60"
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

  const chooseTopic = async () => {
    const topicUnitId = getActionCanonicalId(action);
    if (!conversationId || !topicUnitId || disabled || !onActionResponse) return;
    setIsStarting(true);
    setStartError(null);
    try {
      const response = await agentApi.chat({
        message: `choose_topic:${topicUnitId}`,
        incomingMessageId: createIncomingMessageId(),
        conversationId,
        traceMode: "summary",
      });
      onActionResponse(response);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : "Topic selection could not be completed.");
    } finally {
      setIsStarting(false);
    }
  };

  const content = (
    <span
      className={cn(
        "mt-2 flex min-h-12 w-full items-center justify-between gap-3 rounded-2xl border p-3 text-left text-sm font-semibold transition",
        disabled
          ? "cursor-not-allowed border-border-subtle bg-surface-page text-text-muted"
          : "border-border-subtle bg-surface-card text-text-strong hover:border-primary-200 hover:bg-surface-accent-soft/40",
      )}
    >
      <span>
        <span className="block">{action.label}</span>
        {disabledReason ? <span className="mt-0.5 block text-xs font-medium">Disabled: {disabledReason}</span> : null}
        {startError ? <span className="mt-0.5 block text-xs font-medium text-state-error-fg">{startError}</span> : null}
      </span>
      {isStarting ? <Loader2 className="h-4 w-4 shrink-0 animate-spin" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
    </span>
  );

  if (action.type === "request_replan") {
    return (
      <Link
        href="/replan?source=agent&returnTo=%2Fagent"
        className="group relative mt-3 flex w-full items-center gap-4 overflow-hidden rounded-2xl border border-cyan-200/70 bg-gradient-to-br from-cyan-50 via-white to-indigo-50 p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-cyan-300 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      >
        <span
          aria-hidden
          className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-cyan-300/20 blur-2xl transition group-hover:bg-cyan-300/30"
        />
        <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-500 text-white shadow-sm">
          <Sparkles className="h-5 w-5" />
        </span>
        <span className="relative flex min-w-0 flex-1 flex-col">
          <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-700">
            AI Action
          </span>
          <span className="truncate text-sm font-bold text-slate-900">
            {action.label}
          </span>
          <span className="mt-0.5 text-xs text-slate-600">
            Tell me what you already know — I'll re-optimize your learning path.
          </span>
        </span>
        <span className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-cyan-700 shadow-sm transition group-hover:bg-cyan-600 group-hover:text-white">
          <ArrowRight className="h-4 w-4" />
        </span>
      </Link>
    );
  }

  if (action.type === "request_path_switch") {
    return (
      <PathSwitchAction
        action={action}
        conversationId={conversationId}
        onActionResponse={onActionResponse}
      />
    );
  }

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
          className="btn-secondary min-h-10 w-full px-4 text-sm disabled:opacity-60"
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

  if (action.type === "choose_topic") {
    return (
      <button type="button" disabled={disabled || isStarting} onClick={chooseTopic} className="w-full">
        {content}
      </button>
    );
  }

  if (!href || disabled) return <button type="button">{content}</button>;
  return <Link href={href}>{content}</Link>;
}

function isPlannerPathKey(value: string | null | undefined): value is PlannerPathKey {
  return Boolean(value && value in SUPPORTED_LEARNING_PATHS);
}

function PathSwitchAction({
  action,
  conversationId,
  onActionResponse,
}: {
  action: AgentAction;
  conversationId?: string | null;
  onActionResponse?: (response: AgentChatResponse) => void;
}) {
  const profile = useLearningPathStore((s) => s.profile);
  const setProfile = useLearningPathStore((s) => s.setProfile);
  const requestedPath = getWorkflowId(action);
  const actionId = getActionId(action);
  const initialPath = isPlannerPathKey(requestedPath)
    ? requestedPath
    : profile?.pathKey ?? "computer_vision";
  const [selectedPath, setSelectedPath] = useState<PlannerPathKey>(initialPath);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [switchedTo, setSwitchedTo] = useState<PlannerPathKey | null>(null);
  const target = SUPPORTED_LEARNING_PATHS[selectedPath];
  const isCurrent = profile?.pathKey === selectedPath;

  const applyPathChange = async () => {
    if (!conversationId || !actionId || !onActionResponse) {
      setCommitError("Path change could not be completed from this card.");
      setShowConfirm(false);
      return;
    }
    setIsCommitting(true);
    setCommitError(null);
    try {
      const response = await agentApi.continueAction({
        conversationId,
        actionId,
        decision: "approve",
        editPayload: { targetPathId: selectedPath },
        incomingMessageId: createIncomingMessageId(),
      });
      setProfile(
        createLearningProfileForPath(selectedPath, {
          weeklyHours: profile?.weeklyHours ?? null,
          source: "manual",
        }),
      );
      setSwitchedTo(selectedPath);
      setShowConfirm(false);
      onActionResponse(response);
    } catch (err) {
      setCommitError(err instanceof Error ? err.message : "Path change could not be completed.");
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="mt-2 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
          <Map className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-black text-slate-900">{action.label || "Change path"}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Select a target path. The change is applied only after confirmation.
          </p>
        </div>
      </div>

      <label className="mt-3 block text-xs font-black uppercase tracking-wider text-slate-500" htmlFor={`path-switch-${action.label}`}>
        Target learning path
      </label>
      <select
        id={`path-switch-${action.label}`}
        aria-label="Target learning path"
        value={selectedPath}
        onChange={(event) => {
          setSelectedPath(event.target.value as PlannerPathKey);
          setSwitchedTo(null);
        }}
        className="mt-1 min-h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
      >
        {(Object.keys(SUPPORTED_LEARNING_PATHS) as PlannerPathKey[]).map((pathKey) => {
          const path = SUPPORTED_LEARNING_PATHS[pathKey];
          return (
            <option key={pathKey} value={pathKey}>
              {path.label}{pathKey === profile?.pathKey ? " (current)" : ""}
            </option>
          );
        })}
      </select>
      <p className="mt-1 text-xs text-slate-500">{target.selectedCourseIds.join(" -> ")}</p>

      <button
        type="button"
        disabled={isCurrent}
        onClick={() => setShowConfirm(true)}
        className="mt-3 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-black text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
      >
        <ArrowRight className="h-4 w-4" />
        Repath
      </button>
      {isCurrent ? <p className="mt-2 text-xs font-medium text-slate-500">This is already your active path.</p> : null}
      {commitError ? <p className="mt-2 text-xs font-bold text-red-600">{commitError}</p> : null}
      {switchedTo ? (
        <p className="mt-2 text-xs font-bold text-emerald-700">
          Active path changed to {SUPPORTED_LEARNING_PATHS[switchedTo].label}.
        </p>
      ) : null}

      {showConfirm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Confirm path change"
            className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl"
          >
            <p className="text-base font-black text-slate-900">Confirm path change</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Are you sure you want to switch to {target.label}? Your planner will rebuild around this path.
            </p>
            <div className="mt-5 grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={isCommitting}
                onClick={() => setShowConfirm(false)}
                className="min-h-11 rounded-xl border border-slate-200 px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isCommitting}
                onClick={applyPathChange}
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-black text-white transition hover:bg-blue-700 disabled:opacity-60"
              >
                {isCommitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Change path
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
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
          className="btn-primary flex min-h-14 w-full justify-between px-4 text-left disabled:cursor-not-allowed disabled:opacity-60"
        >
          <span>
            <span className="block text-sm font-semibold">{action.label}</span>
            <span className="mt-0.5 block text-xs opacity-80">
              {disabledReason ?? `${canonicalIds.length} candidate units`}
            </span>
          </span>
          {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <ChevronRight className="h-5 w-5" />}
        </button>
      ) : (
        <AssessmentProposalCard workflow={workflow} onResume={resume} />
      )}
      {error ? <p className="mt-2 text-sm font-medium text-state-error-fg">{error}</p> : null}
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
  const sourceCardCitations = message.citations.filter((citation) => !isExternalCitation(citation));
  const simpleActions = message.actions.filter(
    (action) =>
      action.type !== "review_prerequisite_path" &&
      !workflowActions.includes(action) &&
      !isDuplicateOpenUnitAction(action, message.citations),
  );
  const selectPrerequisiteUnit = (node: AgentPrerequisitePathNode) => {
    onSelectCitation({
      canonicalUnitId: getPrerequisiteNodeCanonicalId(node),
      unitName: getPrerequisiteNodeName(node),
      learnHref: getPrerequisiteNodeHref(node),
      lectureTitle: node.role === "target" ? "Current topic" : "Suggested prerequisite",
      quote: node.reason ?? null,
      source: "planner",
    });
  };

  return (
    <div className={cn("flex w-full gap-3", isUser && "justify-end")}>
      {!isUser ? (
        <div className="hero-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white shadow-sm">
          <Bot className="h-5 w-5" />
        </div>
      ) : null}
      <div className={cn("max-w-[92%] md:max-w-[78%]", !isUser && "space-y-3", isUser && "order-first")}>
        {!isUser && message.activity ? <AgentActivityCard activity={message.activity} /> : null}
        <div
          className={cn(
            "rounded-3xl px-4 py-3 text-[15px] leading-7 shadow-sm",
            isUser
              ? "rounded-tr-md bg-brand-ink text-brand-ink-fg"
              : "rounded-tl-md border border-border-subtle bg-surface-card text-text-body",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.markdown}</p>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none leading-7 dark:prose-invert">
              <AssistantMarkdown markdown={message.markdown} citations={message.citations} />
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
              className="btn-secondary mt-3 px-3 py-1.5 text-xs uppercase tracking-wider"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry
            </button>
          ) : null}
        </div>

        {!isUser && sourceCardCitations.length > 0 ? (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2 px-1 text-[11px] font-bold uppercase tracking-widest text-text-muted">
              <Search className="h-3 w-3" />
              Sources
            </div>
            {sourceCardCitations.map((citation, index) => (
              <CitationCard
                key={citationKey(citation) || index}
                citation={citation}
                isSelected={citationKey(citation) === selectedCitationKey}
                onSelect={onSelectCitation}
              />
            ))}
          </div>
        ) : null}

        {!isUser && prereqAction ? (
          <PrerequisitePath action={prereqAction} onSelectUnit={selectPrerequisiteUnit} />
        ) : null}

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
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-surface-card text-text-muted">
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
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuId) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (!menuRef.current) return;
      if (menuRef.current.contains(event.target as Node)) return;
      setMenuId(null);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuId(null);
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuId]);

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
          className="btn-primary h-12 w-12 p-0"
          aria-label="New chat"
        >
          <Plus className="h-5 w-5" />
        </button>
        <History className="h-5 w-5 text-text-muted" />
      </div>
    );
  }

  return (
    <aside className="flex h-full flex-col overflow-hidden bg-surface-card">
      <div className="space-y-3 border-b border-border-subtle p-4">
        <button
          type="button"
          onClick={onNewChat}
          className="btn-primary min-h-11 w-full text-sm"
        >
          <Plus className="h-4 w-4" />
          New chat
        </button>
        <label className="flex items-center gap-2 rounded-2xl border border-border-subtle bg-surface-page px-3 py-2">
          <Search className="h-4 w-4 text-text-muted" />
          <input
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search chats"
            className="min-w-0 flex-1 bg-transparent text-sm text-text-strong outline-none placeholder:text-text-muted"
          />
        </label>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {filtered.length === 0 ? (
          <div className="py-10 text-center text-sm font-medium text-text-muted">No chat history yet.</div>
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
                  isActive ? "border-primary-200 bg-surface-accent-soft shadow-sm" : "border-transparent hover:bg-surface-page",
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
                  <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-text-muted">
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
                        className="min-w-0 flex-1 rounded-lg border border-primary-200 bg-surface-card px-2 py-1 text-sm font-semibold text-text-strong outline-none focus:ring-2 focus:ring-primary-600/20"
                      />
                      <button
                        type="submit"
                        className="btn-primary h-8 w-8 rounded-lg p-0"
                        aria-label="Save chat title"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                    </form>
                  ) : (
                    <p className={cn("truncate text-sm font-semibold", isActive ? "text-primary-700 dark:text-primary-300" : "text-text-strong")}>
                      {session.title || "New chat"}
                    </p>
                  )}
                  <p className="mt-1 truncate text-xs font-medium text-text-muted">{session.preview || "No messages yet"}</p>
                </div>
                {!isEditing ? (
                  <div className="absolute right-2 top-2" ref={menuId === id ? menuRef : undefined}>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        setMenuId((current) => (current === id ? null : id));
                      }}
                      className="flex h-8 w-8 items-center justify-center rounded-lg text-text-muted opacity-100 transition hover:bg-surface-card hover:text-text-strong lg:opacity-0 lg:group-hover:opacity-100"
                      aria-label="Chat actions"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                    {menuId === id ? (
                      <div className="absolute right-0 z-20 mt-1 w-36 overflow-hidden rounded-xl border border-border-subtle bg-surface-card py-1 text-sm font-semibold text-text-body shadow-xl">
                        <button
                          type="button"
                          onClick={() => {
                            setEditingId(id);
                            setEditingTitle(session.title || "New chat");
                          }}
                          className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-surface-page"
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
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-state-error-fg hover:bg-state-error-bg"
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
    <div className="flex min-h-[58vh] flex-col items-center justify-center px-4 text-center">
      <div className="card-glass w-full max-w-3xl">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-3xl hero-gradient text-white shadow-brand-soft">
          <Bot className="h-10 w-10" />
        </div>
        <h1 className="font-serif text-[36px] font-medium tracking-[-0.01em] text-text-strong">AI Learning Copilot</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-text-body">
          Get grounded help from your current learning path. Ask about prerequisites, weak areas, or the next best step.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {COPILOT_BENEFITS.map((benefit) => (
            <span key={benefit} className="rounded-full bg-surface-accent-soft px-3 py-1 text-xs font-semibold text-primary-700 dark:text-primary-300">
              {benefit}
            </span>
          ))}
        </div>
        <div className="mt-8 grid w-full gap-3 sm:grid-cols-2">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onPrompt(prompt)}
              className="rounded-2xl border border-border-subtle bg-white/80 p-4 text-left text-sm font-semibold text-text-strong shadow-sm transition hover:border-primary-200 hover:bg-surface-accent-soft"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Composer({
  onSend,
  disabled,
  isStreaming,
  onStop,
  toolMode,
  onToolModeChange,
  chatModelId,
  onChatModelChange,
  chatModelAvailability,
}: {
  onSend: (message: string) => void;
  disabled: boolean;
  isStreaming: boolean;
  onStop: () => void;
  toolMode: AgentToolMode;
  onToolModeChange: (mode: AgentToolMode) => void;
  chatModelId: ChatModelId;
  onChatModelChange: (modelId: ChatModelId) => void;
  chatModelAvailability: ChatModelAvailability[];
}) {
  const [text, setText] = useState("");
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const selectedChatModel = CHAT_MODEL_OPTIONS.find((option) => option.id === chatModelId) ?? CHAT_MODEL_OPTIONS[0];
  const send = (event?: FormEvent) => {
    event?.preventDefault();
    const value = text.trim();
    if (!value || disabled) return;
    setText("");
    onSend(value);
  };

  useEffect(() => {
    if (disabled) {
      setIsModelMenuOpen(false);
    }
  }, [disabled]);

  return (
    <div className="border-t border-border-subtle bg-surface-page/80 p-4 backdrop-blur">
      <div className="mx-auto max-w-4xl">
        <div
          className="overflow-visible rounded-2xl border border-border-subtle bg-surface-card shadow-[0_1px_8px_rgba(0,0,0,0.03)]"
          data-testid="agent-composer-card"
        >
          <form onSubmit={send}>
            <label htmlFor="agent-message" className="sr-only">
              Message AI Assistant
            </label>
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
              placeholder="Ask about your learning path..."
              rows={1}
              className="w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-[15px] leading-relaxed text-text-strong outline-none placeholder:text-text-muted min-h-[52px] max-h-[200px]"
            />
            <div className="flex items-center gap-2 border-t border-border-subtle/35 px-3 py-2">
              <div className="flex items-center gap-1.5" data-testid="agent-tool-mode-selector">
                {[
                  { value: "course" as const, label: "Course", icon: BookOpen },
                  { value: "web_papers" as const, label: "Search", icon: Search },
                ].map((mode) => {
                  const Icon = mode.icon;
                  const isActive = toolMode === mode.value;
                  return (
                    <button
                      key={mode.value}
                      type="button"
                      disabled={disabled}
                      onClick={() => onToolModeChange(mode.value)}
                      className={cn(
                        "inline-flex h-[28px] items-center gap-1.5 rounded-full px-2.5 text-[11px] font-medium transition disabled:opacity-60",
                        isActive
                          ? "border border-primary-200 bg-surface-accent-soft text-primary-700 dark:text-primary-300"
                          : "text-text-muted hover:text-text-strong",
                      )}
                      aria-pressed={isActive}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span>{mode.label}</span>
                    </button>
                  );
                })}
              </div>
              <div className="h-3.5 w-px bg-border-subtle/30" />
              <div
                className="relative flex items-center"
                data-testid="agent-chat-model-selector"
                onBlur={(event) => {
                  const nextFocus = event.relatedTarget as Node | null;
                  if (!event.currentTarget.contains(nextFocus)) {
                    setIsModelMenuOpen(false);
                  }
                }}
              >
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => setIsModelMenuOpen((open) => !open)}
                  className="inline-flex h-[28px] max-w-[150px] items-center gap-1.5 rounded-full border border-primary-200 bg-surface-accent-soft px-2.5 text-[11px] font-medium text-primary-700 transition hover:border-primary-300 disabled:cursor-not-allowed disabled:opacity-60 dark:text-primary-300 sm:max-w-[210px]"
                  aria-label={`Agent model: ${selectedChatModel.label}`}
                  aria-expanded={isModelMenuOpen}
                  aria-haspopup="menu"
                >
                  <Bot className="h-3 w-3 shrink-0" />
                  <span className="truncate">{selectedChatModel.label}</span>
                  <ChevronDown
                    className={cn(
                      "h-3 w-3 shrink-0 transition-transform",
                      isModelMenuOpen && "rotate-180",
                    )}
                  />
                </button>
                {isModelMenuOpen ? (
                  <div
                    role="menu"
                    className="absolute bottom-full left-0 z-30 mb-2 w-56 overflow-hidden rounded-xl border border-border-subtle bg-surface-card p-1.5 shadow-[0_12px_32px_rgba(15,23,42,0.14)]"
                  >
                    {CHAT_MODEL_OPTIONS.map((option) => {
                      const availability = getChatModelAvailability(chatModelAvailability, option.id);
                      const isActive = chatModelId === option.id;
                      const isUnavailable = !availability.available;
                      const statusLabel = isUnavailable ? availability.status : null;
                      return (
                        <button
                          key={option.id}
                          type="button"
                          role="menuitemradio"
                          disabled={disabled || isUnavailable}
                          aria-checked={isActive}
                          onClick={() => {
                            onChatModelChange(option.id);
                            setIsModelMenuOpen(false);
                          }}
                          title={isUnavailable ? `${option.label} is ${availability.status}` : option.label}
                          className={cn(
                            "flex min-h-9 w-full items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
                            isActive
                              ? "bg-surface-accent-soft text-primary-700 dark:text-primary-300"
                              : "text-text-muted hover:bg-surface-page hover:text-text-strong",
                          )}
                        >
                          <Bot className="h-3.5 w-3.5 shrink-0" />
                          <span className="min-w-0 flex-1 truncate">{option.label}</span>
                          {statusLabel ? (
                            <span className="shrink-0 rounded-full bg-rose-500/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-rose-700 dark:text-rose-300">
                              {statusLabel}
                            </span>
                          ) : null}
                          {isActive ? <Check className="h-3.5 w-3.5 shrink-0" /> : null}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
              <div className="ml-auto">
                {isStreaming ? (
                  <button
                    type="button"
                    onClick={onStop}
                    className="flex h-[29px] w-[29px] items-center justify-center rounded-full border border-border-subtle bg-surface-card p-0 text-text-muted transition hover:bg-surface-page hover:text-text-strong"
                    aria-label="Stop generating"
                  >
                    <Square className="h-[12px] w-[12px]" fill="currentColor" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={disabled || !text.trim()}
                    className={cn(
                      "flex h-[29px] w-[29px] items-center justify-center rounded-full p-0 text-white transition disabled:cursor-not-allowed disabled:opacity-25 disabled:shadow-none",
                      "bg-primary-600 shadow-[0_4px_12px_rgba(79,70,229,0.15)] hover:shadow-[0_6px_16px_rgba(79,70,229,0.22)]",
                    )}
                    aria-label="Send message"
                  >
                    <ArrowUp className="h-[15px] w-[15px]" strokeWidth={2.5} />
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function getCurrentActivityLine(activity: AgentActivitySnapshot) {
  const step = activity.steps[activity.steps.length - 1];
  if (!step) return "Preparing request";
  return step.detail ? `${step.title} · ${step.detail}` : step.title;
}

function AgentActivityCard({ activity }: { activity: AgentActivitySnapshot }) {
  const [now, setNow] = useState(Date.now());
  const [isExpanded, setIsExpanded] = useState(false);
  const completed = activity.completedAt !== undefined;
  const elapsedMs = getAgentActivityElapsedMs(activity, now);
  const header = getAgentActivityHeader({ elapsedMs, completed });
  const currentLine = getCurrentActivityLine(activity);

  useEffect(() => {
    if (activity.completedAt !== undefined || typeof window === "undefined") return;
    const intervalId = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, [activity.completedAt]);

  useEffect(() => {
    if (activity.completedAt !== undefined) {
      setIsExpanded(false);
    }
  }, [activity.completedAt]);

  return (
    <div className="w-full max-w-xl rounded-2xl border border-border-subtle/70 bg-surface-card/55 px-3 py-2.5 text-text-muted shadow-sm backdrop-blur-sm">
      <button
        type="button"
        onClick={() => setIsExpanded((current) => !current)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={isExpanded}
      >
        <span className="flex min-w-0 items-center gap-2.5">
          <span
            className={cn(
              "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-surface-page text-primary-700",
              !completed && "border-primary-200 text-primary-700 dark:text-primary-300",
            )}
          >
            {completed ? <Check className="h-3.5 w-3.5" /> : <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-text-body">{header}</span>
            {!completed ? <span className="mt-0.5 block truncate text-xs text-text-muted">{currentLine}</span> : null}
          </span>
        </span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform", isExpanded && "rotate-180")} />
      </button>

      {isExpanded ? (
        <div className="mt-3 border-l border-border-subtle pl-4">
          <div className="space-y-3">
            {activity.steps.map((step) => (
              <div key={step.id} className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-text-muted" />
                <p className="text-sm font-semibold text-text-body">{step.title}</p>
                {step.detail ? <p className="mt-0.5 text-sm leading-6 text-text-muted">{step.detail}</p> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function StreamingTurn({
  markdown,
  activity,
}: {
  markdown: string | null;
  activity: AgentActivitySnapshot | null;
}) {
  return (
    <div className="flex w-full gap-3">
      <div className="hero-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white shadow-sm">
        <Bot className="h-5 w-5" />
      </div>
      <div className="max-w-[92%] space-y-3 md:max-w-[78%]">
        {activity ? <AgentActivityCard activity={activity} /> : null}
        {markdown !== null ? (
          <div className="rounded-3xl rounded-tl-md border border-border-subtle bg-surface-card px-4 py-3 text-[15px] leading-7 shadow-sm">
            <div className="prose prose-sm prose-slate max-w-none leading-7 dark:prose-invert">
              <AssistantMarkdown markdown={markdown} />
              <span className="inline-block h-5 w-1 animate-pulse rounded-sm bg-primary-400 align-text-bottom" />
            </div>
          </div>
        ) : null}
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
  const [streamActivity, setStreamActivity] = useState<AgentActivitySnapshot | null>(null);
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamActivityRef = useRef<AgentActivitySnapshot | null>(null);
  const [toolMode, setToolMode] = useState<AgentToolMode>("course");
  const [chatModelId, setChatModelId] = useState<ChatModelId>("default");
  const [chatModelAvailability, setChatModelAvailability] = useState<ChatModelAvailability[]>(
    DEFAULT_CHAT_MODEL_AVAILABILITY,
  );
  const [error, setError] = useState<string | null>(null);
  const [leftOpen, setLeftOpen] = useState(false);
  const [leftMinimized, setLeftMinimized] = useState(false);
  const SIDEBAR_MIN = 220;
  const SIDEBAR_MAX = 480;
  const SIDEBAR_DEFAULT = 288;
  const [sidebarWidth, setSidebarWidth] = useState<number>(SIDEBAR_DEFAULT);
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("agent.sidebarWidth");
    if (!stored) return;
    const parsed = Number.parseInt(stored, 10);
    if (Number.isFinite(parsed) && parsed >= SIDEBAR_MIN && parsed <= SIDEBAR_MAX) {
      setSidebarWidth(parsed);
    }
  }, []);

  useEffect(() => {
    setChatModelId(readStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.agent));
  }, []);

  useEffect(() => {
    let active = true;
    agentApi
      .modelAvailability()
      .then(({ models }) => {
        if (!active) return;
        setChatModelAvailability(models);
        setChatModelId((current) => {
          const next = fallbackUnavailableChatModel(models, current);
          if (next !== current) {
            writeStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.agent, next);
          }
          return next;
        });
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const changeChatModel = (modelId: ChatModelId) => {
    if (!isChatModelAvailable(chatModelAvailability, modelId)) return;
    setChatModelId(modelId);
    writeStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.agent, modelId);
  };

  useEffect(() => {
    if (!isResizingSidebar) return;
    const handleMove = (event: MouseEvent) => {
      const next = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, event.clientX));
      setSidebarWidth(next);
    };
    const handleUp = () => {
      setIsResizingSidebar(false);
      try {
        window.localStorage.setItem("agent.sidebarWidth", String(sidebarWidth));
      } catch { }
    };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, [isResizingSidebar, sidebarWidth]);
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
  }, [messages, isThinking, streamingText, streamActivity]);

  useEffect(() => {
    if (!isThinking) {
      setStreamActivity(null);
      streamActivityRef.current = null;
      setStreamingText(null);
    }
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
    if (isExternalCitation(citation)) {
      const href = getCitationHref(citation);
      if (href) {
        window.open(href, "_blank", "noopener,noreferrer");
      }
      return;
    }
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
    retry?: { message: string; incomingMessageId: string; activity?: AgentActivitySnapshot },
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
        activity: retry?.activity,
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

  const stopStream = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsThinking(false);
  };

  const updateStreamActivity = (updater: (activity: AgentActivitySnapshot) => AgentActivitySnapshot) => {
    setStreamActivity((current) => {
      const base = current ?? streamActivityRef.current;
      if (!base) return current;
      const next = updater(base);
      streamActivityRef.current = next;
      return next;
    });
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
    } else {
      setMessages((current) =>
        current.filter(
          (item) =>
            item.role !== "assistant" ||
            !getFallbackErrorCode(item.fallback) ||
            item.retryIncomingMessageId !== incomingMessageId,
        ),
      );
    }
    const initialActivity = createAgentActivity({ message, startedAt: Date.now() });
    streamActivityRef.current = applyAgentActivityStatus(initialActivity, "Preparing request");
    setStreamActivity(streamActivityRef.current);
    setStreamingText(null);
    setIsThinking(true);

    let fullText = "";

    try {
      const safeChatModelId = fallbackUnavailableChatModel(chatModelAvailability, chatModelId);
      if (safeChatModelId !== chatModelId) {
        setChatModelId(safeChatModelId);
        writeStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.agent, safeChatModelId);
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;
      const routeContext = readAgentRouteContext();

      const stream = await agentApi.chatStream(
        {
          message,
          incomingMessageId,
          conversationId: activeSessionId,
          traceMode: "summary",
          ...(routeContext ? { routeContext } : {}),
          ...(toolMode === "web_papers" ? { toolMode } : {}),
          ...(safeChatModelId !== "default" ? { chatModelId: safeChatModelId } : {}),
        },
        controller.signal,
      );

      for await (const event of stream) {
        if (controller.signal.aborted) break;
        if (isStreamStatus(event)) {
          updateStreamActivity((activity) => applyAgentActivityStatus(activity, event.status));
        } else if (isStreamThought(event)) {
          updateStreamActivity((activity) => applyAgentActivityThought(activity, event.thought));
        } else if (isStreamChunk(event)) {
          fullText += event.chunk;
          setStreamingText(fullText);
        } else if (isStreamDone(event)) {
          const completedActivity = completeAgentActivity(streamActivityRef.current ?? initialActivity, {
            completedAt: Date.now(),
            citationCount: event.done.citations?.length ?? 0,
          });
          streamActivityRef.current = completedActivity;
          setStreamingText(null);
          setStreamActivity(null);
          appendAgentResponse(event.done, { message, incomingMessageId, activity: completedActivity });
        }
      }
    } catch (err) {
      console.error("[stream] error:", err);
      if (err instanceof DOMException && err.name === "AbortError") {
        if (fullText) {
          const completedActivity = completeAgentActivity(streamActivityRef.current ?? initialActivity, {
            completedAt: Date.now(),
          });
          setMessages((current) => [
            ...current,
            {
              id: `assistant-stream-${Date.now()}`,
              role: "assistant",
              markdown: fullText,
              createdAt: new Date().toISOString(),
              confidence: "partial",
              citations: [],
              actions: [],
              activity: completedActivity,
            },
          ]);
        }
        setStreamingText(null);
      } else {
        setStreamingText(null);
        setMessages((current) => [
          ...current,
          buildAgentClientErrorMessage(err, { message, incomingMessageId }),
        ]);
      }
    } finally {
      abortControllerRef.current = null;
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
      <div className="absolute bottom-0 left-0 top-0 w-[290px] border-r border-border-subtle bg-surface-card shadow-2xl">
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
    <div className="relative flex h-full min-h-0 overflow-hidden bg-surface-page text-text-strong">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.12),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(34,211,238,0.12),_transparent_30%)]" />
      <div
        className={cn(
          "relative hidden shrink-0 border-r border-border-subtle bg-surface-card lg:block",
          leftMinimized ? "w-20" : "",
          isResizingSidebar ? "" : "transition-[width] duration-150",
        )}
        style={leftMinimized ? undefined : { width: sidebarWidth }}
      >
        <SessionSidebar
          sessions={sessions}
          activeId={activeSessionId}
          onSelect={setActiveSessionId}
          onNewChat={newChat}
          onRename={renameSession}
          onDelete={deleteSession}
          isMinimized={leftMinimized}
        />
        {!leftMinimized ? (
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize chat history sidebar"
            onMouseDown={(event) => {
              event.preventDefault();
              setIsResizingSidebar(true);
            }}
            onDoubleClick={() => {
              setSidebarWidth(SIDEBAR_DEFAULT);
              try {
                window.localStorage.setItem("agent.sidebarWidth", String(SIDEBAR_DEFAULT));
              } catch { }
            }}
            className={cn(
              "group absolute top-0 -right-1 z-10 flex h-full w-2 cursor-col-resize items-center justify-center",
              "before:absolute before:inset-y-0 before:left-1/2 before:w-px before:-translate-x-1/2 before:bg-transparent before:transition before:content-['']",
              "hover:before:bg-cyan-400/60",
              isResizingSidebar && "before:bg-cyan-500",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "h-10 w-1 rounded-full bg-border-subtle transition group-hover:bg-cyan-400",
                isResizingSidebar && "bg-cyan-500",
              )}
            />
          </div>
        ) : null}
      </div>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="relative flex h-20 shrink-0 items-center justify-between border-b border-border-subtle bg-white/80 px-4 backdrop-blur">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setLeftOpen(true)}
              className="flex h-10 w-10 items-center justify-center rounded-xl text-text-muted hover:bg-surface-page lg:hidden"
              aria-label="Open chat history"
            >
              <Menu className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => setLeftMinimized((value) => !value)}
              className="hidden h-10 w-10 items-center justify-center rounded-xl text-text-muted hover:bg-surface-page lg:flex"
              aria-label={leftMinimized ? "Expand chat history" : "Collapse chat history"}
            >
              {leftMinimized ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            </button>
            <div className="hero-gradient hidden h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-white shadow-brand-soft sm:flex">
              <Bot className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-lg font-semibold tracking-tight text-text-strong">AI Learning Copilot</h1>
                <span className="hidden rounded-full bg-surface-accent-soft px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary-700 dark:text-primary-300 md:inline-flex">
                  Grounded in your learning path
                </span>
              </div>
              <p className="truncate text-xs font-medium text-text-muted">
                {activeSession?.title || "Ask about your path, prerequisites, weak areas, or next step."} · {user?.full_name || "Learner"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isLoadingSessions ? <Loader2 className="h-4 w-4 animate-spin text-text-muted" /> : null}
          </div>
        </header>

        <main ref={scrollRef} className="relative flex-1 overflow-y-auto" style={{ maskImage: "linear-gradient(to bottom, transparent 0px, #000 32px, #000 calc(100% - 40px), transparent 100%)" }}>
          <div className="pointer-events-none absolute inset-0 opacity-[0.035]" style={{ backgroundImage: "radial-gradient(circle, var(--text-strong) 1px, transparent 1px)", backgroundSize: "28px 28px" }} />
          <div className="relative mx-auto max-w-4xl space-y-6 px-4 py-8">
            {error ? (
              <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-medium text-red-700">
                {error}
              </div>
            ) : null}
            {isLoadingMessages ? (
              <div className="flex min-h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary-700" />
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
                {isThinking || streamingText !== null || streamActivity ? (
                  <StreamingTurn markdown={streamingText} activity={streamActivity} />
                ) : null}
              </>
            )}
          </div>
        </main>

        <Composer
          onSend={sendMessage}
          disabled={isThinking}
          isStreaming={isThinking}
          onStop={stopStream}
          toolMode={toolMode}
          onToolModeChange={setToolMode}
          chatModelId={chatModelId}
          onChatModelChange={changeChatModel}
          chatModelAvailability={chatModelAvailability}
        />
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
          <div className="absolute bottom-0 right-0 top-0 w-full max-w-[390px] bg-surface-card shadow-2xl">
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
