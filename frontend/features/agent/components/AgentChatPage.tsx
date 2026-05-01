"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bot,
  Brain,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  FileText,
  History,
  Info,
  Loader2,
  Map,
  Menu,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  Search,
  Send,
  Sparkles,
  Target,
  User,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import {
  agentApi,
  getActionCanonicalIds,
  getActionDisabledReason,
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
  getUpdatedAt,
  getWorkflowId,
  type AgentAction,
  type AgentAssessmentWorkflowResponse,
  type AgentCitation,
  type AgentConversationMemory,
  type AgentConversationMessage,
  type AgentConversationSummary,
  type AgentWarning,
  type AssessmentProposal,
} from "@/features/agent/api";
import { writeStartedCanonicalAssessment } from "@/lib/canonical-assessment-session";
import type { QuestionForAssessment } from "@/types";

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
};

function createIncomingMessageId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const QUICK_PROMPTS = [
  "Where should I review CNNs?",
  "What should I learn next?",
  "Can I skip the units I already know?",
  "Which DL parts are required for NLP?",
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

function CitationCard({ citation }: { citation: AgentCitation }) {
  const href = getCitationHref(citation);
  const content = (
    <div className="group rounded-2xl border border-slate-200 bg-white p-3 transition hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/10">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-blue-50 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-blue-600">
              {getCitationCourseId(citation)}
            </span>
            {citation.source ? (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {citation.source}
              </span>
            ) : null}
          </div>
          <h4 className="line-clamp-2 text-sm font-black leading-snug text-slate-900 group-hover:text-blue-600">
            {getCitationUnitName(citation)}
          </h4>
          {getCitationLectureTitle(citation) ? (
            <p className="mt-1 line-clamp-1 text-xs font-medium text-slate-500">
              {getCitationLectureTitle(citation)}
            </p>
          ) : null}
          {citation.quote ? <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">{citation.quote}</p> : null}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-50 text-slate-400 transition group-hover:bg-blue-600 group-hover:text-white">
          <ExternalLink className="h-4 w-4" />
        </div>
      </div>
    </div>
  );

  if (!href) return content;
  return (
    <Link href={href} className="block">
      {content}
    </Link>
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

function ActionButton({ action }: { action: AgentAction }) {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const href = getCitationHref(action);
  const disabledReason = getActionDisabledReason(action);
  const disabled = action.eligible === false || Boolean(disabledReason);

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

  if (action.type === "start_assessment") {
    return (
      <button type="button" disabled={disabled || isStarting} onClick={startAssessment} className="w-full">
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

function ChatMessageItem({ message }: { message: UiMessage }) {
  const isUser = message.role === "user";
  const prereqAction = message.actions.find((action) => action.type === "review_prerequisite_path");
  const workflowActions = message.actions.filter(
    (action) => action.type === "start_assessment_workflow" || action.type === "continue_assessment_workflow",
  );
  const simpleActions = message.actions.filter(
    (action) => action.type !== "review_prerequisite_path" && !workflowActions.includes(action),
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
          <p className="whitespace-pre-wrap">{message.markdown}</p>
          {!isUser && message.warning ? <WarningBlock warning={message.warning} /> : null}
        </div>

        {!isUser && message.citations.length > 0 ? (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2 px-1 text-[11px] font-black uppercase tracking-widest text-slate-400">
              <Search className="h-3 w-3" />
              Sources
            </div>
            {message.citations.map((citation, index) => (
              <CitationCard key={getCitationCanonicalId(citation) || index} citation={citation} />
            ))}
          </div>
        ) : null}

        {!isUser && prereqAction ? <PrerequisitePath unitIds={getActionCanonicalIds(prereqAction)} /> : null}

        {!isUser && workflowActions.map((action) => <WorkflowAction key={`${action.type}-${action.label}`} action={action} />)}

        {!isUser && simpleActions.length > 0 ? (
          <div className="mt-3 space-y-2">
            {simpleActions.map((action, index) => (
              <ActionButton key={`${action.type}-${action.label}-${index}`} action={action} />
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
}: {
  sessions: AgentConversationSummary[];
  activeId: string | null;
  isMinimized: boolean;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}) {
  const [filter, setFilter] = useState("");
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
            return (
              <button
                key={id}
                type="button"
                onClick={() => onSelect(id)}
                className={cn(
                  "mb-2 w-full rounded-2xl border p-3 text-left transition",
                  isActive ? "border-blue-100 bg-blue-50 shadow-sm" : "border-transparent hover:bg-slate-50",
                )}
              >
                <div className="mb-1 flex items-center gap-2 text-[10px] font-black uppercase tracking-wider text-slate-400">
                  <span>{formatDateLabel(getUpdatedAt(session))}</span>
                  <span>{session.messageCount ?? session.message_count ?? 0} messages</span>
                </div>
                <p className={cn("truncate text-sm font-black", isActive ? "text-blue-700" : "text-slate-900")}>
                  {session.title || "New chat"}
                </p>
                <p className="mt-1 truncate text-xs font-medium text-slate-500">{session.preview || "No messages yet"}</p>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}

function MemoryModal({
  memory,
  onClose,
}: {
  memory: AgentConversationMemory | null;
  onClose: () => void;
}) {
  const summary = memory?.summary ?? {};
  const entries = Object.entries(summary).filter(([, value]) =>
    Array.isArray(value) ? value.length > 0 : Boolean(value),
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close memory summary"
      />
      <div className="relative max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-3xl bg-white shadow-2xl">
        <header className="flex items-center justify-between border-b border-slate-100 bg-slate-50 p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-600 text-white">
              <Brain className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-950">Session memory</h2>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400">
                {memory?.summaryStatus ?? memory?.summary_status ?? "empty"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-500"
            aria-label="Close memory summary"
          >
            <X className="h-5 w-5" />
          </button>
        </header>
        <div className="max-h-[60vh] overflow-y-auto p-5">
          {entries.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
              No session summary yet. A new chat starts without previous session memory.
            </p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {entries.map(([key, value]) => (
                <section key={key} className="rounded-2xl border border-slate-200 p-4">
                  <h3 className="mb-3 text-[11px] font-black uppercase tracking-widest text-slate-400">
                    {key.replace(/_/g, " ")}
                  </h3>
                  {Array.isArray(value) ? (
                    <div className="flex flex-wrap gap-2">
                      {value.map((item) => (
                        <span key={String(item)} className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">
                          {String(item)}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm leading-6 text-slate-700">{String(value)}</p>
                  )}
                </section>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ContextPanel({
  memory,
  isMinimized,
  onOpenMemory,
}: {
  memory: AgentConversationMemory | null;
  isMinimized: boolean;
  onOpenMemory: () => void;
}) {
  if (isMinimized) {
    return (
      <div className="flex h-full flex-col items-center gap-6 p-4 text-slate-300">
        <Brain className="h-6 w-6" />
        <Map className="h-6 w-6" />
        <FileText className="h-6 w-6" />
      </div>
    );
  }

  const summaryStatus = memory?.summaryStatus ?? memory?.summary_status ?? "empty";
  const recentWindow = memory?.recentMessageWindow ?? memory?.recent_message_window ?? 0;

  return (
    <aside className="h-full overflow-y-auto bg-white">
      <section className="border-b border-slate-200 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
            <Brain className="h-4 w-4" />
            Memory
          </h2>
          <span className="rounded-full bg-green-50 px-2 py-1 text-[10px] font-black uppercase tracking-wider text-green-700">
            {summaryStatus}
          </span>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-bold text-slate-900">Session scoped</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            New chats do not inherit old agent chat history. The assistant can still use scoped lecture tutor memory when relevant.
          </p>
          <p className="mt-3 text-xs font-bold text-slate-500">Recent window: {recentWindow || 10} messages</p>
          <button
            type="button"
            onClick={onOpenMemory}
            className="mt-4 flex min-h-10 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 text-xs font-black uppercase tracking-widest text-white"
          >
            <FileText className="h-4 w-4" />
            View summary
          </button>
        </div>
      </section>

      <section className="border-b border-slate-200 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
          <Map className="h-4 w-4" />
          Scope
        </h2>
        <div className="rounded-2xl border border-slate-200 p-4">
          <p className="text-sm font-black text-slate-900">Current path first</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Answers are scoped to your selected path first. Catalog answers outside the path are marked with a warning.
          </p>
        </div>
      </section>

      <section className="p-5">
        <h2 className="mb-4 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
          <Sparkles className="h-4 w-4" />
          Useful prompts
        </h2>
        <div className="space-y-2 text-sm font-semibold text-slate-600">
          <p>Find where a concept is taught.</p>
          <p>Ask which prerequisites to review.</p>
          <p>Negotiate assessment evidence for replanning.</p>
        </div>
      </section>
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

export default function AgentChatPage() {
  const { user } = useAuthStore();
  const [sessions, setSessions] = useState<AgentConversationSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [memory, setMemory] = useState<AgentConversationMemory | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [leftMinimized, setLeftMinimized] = useState(false);
  const [rightMinimized, setRightMinimized] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoadingSessions(true);
    agentApi
      .listConversations()
      .then((items: AgentConversationSummary[]) => {
        if (!active) return;
        setSessions(items);
        if (!activeSessionId && items.length > 0) {
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
  }, [activeSessionId]);

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      setMemory(null);
      return;
    }
    let active = true;
    setIsLoadingMessages(true);
    Promise.all([agentApi.messages(activeSessionId), agentApi.memory(activeSessionId)])
      .then(([loadedMessages, loadedMemory]) => {
        if (!active) return;
        setMessages(toUiMessages(loadedMessages));
        setMemory(loadedMemory);
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

  const activeSession = useMemo(
    () => sessions.find((session) => getConversationId(session) === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

  const refreshSessions = () => {
    agentApi.listConversations().then(setSessions).catch(() => undefined);
  };

  const newChat = async () => {
    setError(null);
    try {
      const session = await agentApi.createConversation();
      const id = getConversationId(session);
      setSessions((current) => [session, ...current.filter((item) => getConversationId(item) !== id)]);
      setActiveSessionId(id);
      setMessages([]);
      setMemory(null);
      setLeftOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create a new chat.");
    }
  };

  const sendMessage = async (message: string) => {
    setError(null);
    const incomingMessageId = createIncomingMessageId();
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
    setIsThinking(true);
    try {
      const response = await agentApi.chat({
        message,
        incomingMessageId,
        conversationId: activeSessionId,
        traceMode: "summary",
      });
      const conversationId = getConversationId(response);
      if (conversationId && conversationId !== activeSessionId) {
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
        },
      ]);
      refreshSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send message.");
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
          isMinimized={false}
        />
      </div>
    </div>
  );

  const mobileRight = (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/50"
        onClick={() => setRightOpen(false)}
        aria-label="Close context panel"
      />
      <div className="absolute bottom-0 right-0 top-0 w-[320px] border-l border-slate-200 bg-white shadow-2xl">
        <ContextPanel memory={memory} isMinimized={false} onOpenMemory={() => setMemoryOpen(true)} />
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
            <button
              type="button"
              onClick={() => setRightOpen(true)}
              className="flex h-10 w-10 items-center justify-center rounded-xl text-blue-600 hover:bg-blue-50 lg:hidden"
              aria-label="Open context panel"
            >
              <Brain className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => setRightMinimized((value) => !value)}
              className="hidden h-10 w-10 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-100 lg:flex"
              aria-label={rightMinimized ? "Expand context panel" : "Collapse context panel"}
            >
              {rightMinimized ? <PanelRightOpen className="h-5 w-5" /> : <PanelRightClose className="h-5 w-5" />}
            </button>
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
                  <ChatMessageItem key={message.id} message={message} />
                ))}
                {isThinking ? (
                  <div className="flex gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div className="rounded-3xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                      <div className="flex items-center gap-2 text-sm font-semibold text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                        Thinking
                      </div>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </main>

        <Composer onSend={sendMessage} disabled={isThinking} />
      </section>

      <div className={cn("hidden shrink-0 border-l border-slate-200 bg-white transition-all lg:block", rightMinimized ? "w-20" : "w-80")}>
        <ContextPanel memory={memory} isMinimized={rightMinimized} onOpenMemory={() => setMemoryOpen(true)} />
      </div>

      {leftOpen ? mobileLeft : null}
      {rightOpen ? mobileRight : null}
      {memoryOpen ? <MemoryModal memory={memory} onClose={() => setMemoryOpen(false)} /> : null}
    </div>
  );
}
