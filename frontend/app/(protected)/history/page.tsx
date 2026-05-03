"use client";

// app/(protected)/history/page.tsx
// Learning History page:
//   • Stats bar: total sessions, avg score, study time, mini SVG line chart
//   • Filters: type, module, date range
//   • Sortable table (date, type, subject, score, duration)
//   • Expandable rows: per-question breakdown, bloom analysis, misconceptions
//   • Pagination (20 / page)

import { Fragment, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  Award,
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock,
  Filter,
  History as HistoryIcon,
  Lightbulb,
  RotateCcw,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { canonicalSectionApi, historyApi } from "@/lib/api";
import { usePageTitle } from "@/hooks/usePageTitle";
import type {
  BloomLevel,
  CourseSectionListItem,
  HistoryItem,
  HistoryResponse,
  QuestionInteractionDetail,
  SelectedAnswer,
  SessionDetailResponse,
  SessionType,
} from "@/types";
import MarkdownRenderer from "@/components/assessment/MarkdownRenderer";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

const TYPE_LABELS: Record<SessionType, string> = {
  assessment: "Assessment",
  quiz: "Quiz",
  module_test: "Module Test",
  practice: "Practice",
};

const TYPE_COLORS: Record<SessionType, string> = {
  assessment: "bg-violet-100 text-violet-700",
  quiz: "bg-blue-100 text-blue-700",
  module_test: "bg-amber-100 text-amber-700",
  practice: "bg-slate-100 text-slate-600",
};

const CHECKPOINT_LABELS: Record<string, string> = {
  midpoint: "Mid-video quiz",
  end: "End-of-video quiz",
};

const BLOOM_VI: Record<string, string> = {
  remember: "Remember",
  understand: "Understand",
  apply: "Apply",
  analyze: "Analyze",
};

const BLOOM_BAR_COLOR: Record<string, string> = {
  remember: "#38bdf8",
  understand: "#a78bfa",
  apply: "#fbbf24",
  analyze: "#f87171",
};

type SortKey = "started_at" | "session_type" | "subject" | "score_percent" | "duration_seconds";
type SortDir = "asc" | "desc";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDuration(secs: number | null) {
  if (secs === null) return "—";
  if (secs < 60) return `${secs}s`;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function fmtStudyTime(secs: number) {
  if (secs < 60) return `${secs}s`;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function scoreColor(pct: number | null) {
  if (pct === null) return "var(--text-muted)";
  if (pct >= 70) return "#10b981";
  if (pct >= 50) return "#f59e0b";
  return "#ef4444";
}

function questionRowKey(q: QuestionInteractionDetail, index: number) {
  return q.question_id ?? q.canonical_item_id ?? `${q.sequence_position}-${index}`;
}

// ---------------------------------------------------------------------------
// Mini SVG line chart
// ---------------------------------------------------------------------------

function SparkLine({
  data,
  width = 120,
  height = 36,
}: {
  data: { score_percent: number }[];
  width?: number;
  height?: number;
}) {
  if (data.length < 2) {
    return (
      <span className="text-xs text-text-muted">
        Not enough data
      </span>
    );
  }

  const pad = 4;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const max = Math.max(...data.map((d) => d.score_percent));
  const min = Math.min(...data.map((d) => d.score_percent));
  const range = max - min || 1;

  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * w;
    const y = pad + h - ((d.score_percent - min) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const lastPt = pts[pts.length - 1].split(",");
  const lastScore = data[data.length - 1].score_percent;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke="#6366f1"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={pts.join(" ")}
      />
      <circle
        cx={lastPt[0]}
        cy={lastPt[1]}
        r="3"
        fill="#6366f1"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Bloom breakdown bar
// ---------------------------------------------------------------------------

function BloomBar({ breakdown }: { breakdown: Record<string, string> }) {
  const entries = Object.entries(breakdown).filter(([, v]) => v !== "0/0");
  if (entries.length === 0) return null;
  return (
    <div className="space-y-1.5">
      {entries.map(([level, fraction]) => {
        const [c, t] = fraction.split("/").map(Number);
        const pct = t > 0 ? (c / t) * 100 : 0;
        return (
          <div key={level} className="flex items-center gap-2">
            <span className="w-20 text-right text-xs font-medium text-text-muted">
              {BLOOM_VI[level] ?? level}
            </span>
            <div className="flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700 h-2">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${pct}%`, background: BLOOM_BAR_COLOR[level] ?? "#94a3b8" }}
              />
            </div>
            <span className="w-10 text-xs tabular-nums text-text-muted">
              {fraction}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expanded row detail
// ---------------------------------------------------------------------------

function ExpandedDetail({
  sessionId,
}: {
  sessionId: string;
}) {
  const [detail, setDetail] = useState<SessionDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedQIdx, setExpandedQIdx] = useState<number | null>(null);

  useEffect(() => {
    historyApi
      .detail(sessionId)
      .then(setDetail)
      .catch((err) => {
        const d = err?.response?.data?.detail;
        setError(typeof d === "string" ? d : "Unable to load details.");
      })
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex justify-center py-6">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-400 border-t-transparent" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <p className="py-4 text-center text-sm text-red-500">{error || "No data available."}</p>
      
    );
  }

  return (
    <div className="space-y-5 px-1 py-3">
      {detail.source === "inline_video" && detail.checkpoint ? (
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700">
            {CHECKPOINT_LABELS[detail.checkpoint] ?? detail.checkpoint}
          </span>
        </div>
      ) : null}

      {/* Bloom + KCs + misconceptions side-by-side */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Bloom breakdown */}
        <div className="rounded-xl border border-border-subtle bg-surface-page p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">
            <Brain size={12} /> Bloom
          </p>
          <BloomBar breakdown={detail.bloom_breakdown} />
        </div>

        {/* Weak KCs */}
        <div className="rounded-xl border border-border-subtle bg-surface-page p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">
            <BookOpen size={12} /> Weak knowledge
          </p>
          {detail.weak_kcs.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {detail.weak_kcs.map((kc) => (
                <span
                  key={kc}
                  className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700"
                >
                  {kc}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-muted">None</p>
          )}
        </div>

        {/* Misconceptions */}
        <div className="rounded-xl border border-border-subtle bg-surface-page p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">
            <Lightbulb size={12} /> Misconceptions
          </p>
          {detail.misconceptions.length > 0 ? (
            <ul className="space-y-1">
              {detail.misconceptions.map((m) => (
                <li key={m} className="flex items-start gap-1.5 text-xs text-text-body">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-400" />
                  {m}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-muted">Not detected</p>
          )}
        </div>
      </div>

      {/* Per-question list */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Question details ({detail.questions.length} questions)
        </p>
        <div className="space-y-1.5">
          {detail.questions.map((q, i) => (
            <QuestionRow
              key={questionRowKey(q, i)}
              q={q}
              num={i + 1}
              open={expandedQIdx === i}
              onToggle={() => setExpandedQIdx((prev) => (prev === i ? null : i))}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function LinkedReviewPanel({ sessionId }: { sessionId: string }) {
  return (
    <div className="rounded-2xl border border-border-subtle bg-surface-elevated p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-text-strong">
          Review opened from link
        </p>
        <span className="rounded-full bg-surface-page px-2 py-0.5 text-xs text-text-body dark:bg-slate-800 dark:text-slate-300">
          Session {sessionId}
        </span>
      </div>
      <p className="mt-1 text-xs text-text-muted">
        This session is not on the current history page, so the review content was loaded directly.
      </p>
      <ExpandedDetail sessionId={sessionId} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single question row inside expanded detail
// ---------------------------------------------------------------------------

function QuestionRow({
  q,
  num,
  open,
  onToggle,
}: {
  q: QuestionInteractionDetail;
  num: number;
  open: boolean;
  onToggle: () => void;
}) {
  const opts: SelectedAnswer[] = ["A", "B", "C", "D"];
  const optText: Record<SelectedAnswer, string> = {
    A: q.option_a,
    B: q.option_b,
    C: q.option_c,
    D: q.option_d,
  };

  return (
    <div className="overflow-hidden rounded-xl border border-border-subtle">
      {/* Header row */}
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 bg-surface-elevated px-3 py-2.5 text-left transition-colors hover:bg-surface-page dark:hover:bg-slate-800/50"
      >
        {/* Correct / Wrong icon */}
        {q.is_correct ? (
          <CheckCircle2 size={14} className="shrink-0 text-emerald-500" />
        ) : (
          <XCircle size={14} className="shrink-0 text-red-400" />
        )}

        <span className="shrink-0 text-xs font-medium text-text-muted">
          {num}.
        </span>

        {/* Stem preview */}
        <span className="flex-1 truncate text-sm text-text-strong">
          {q.stem_text.replace(/[#*`]/g, "").slice(0, 100)}
        </span>

        {/* Bloom badge */}
        <span className="hidden shrink-0 rounded-full bg-surface-page px-2 py-0.5 text-xs text-text-muted dark:bg-slate-800 sm:inline">
          {BLOOM_VI[q.bloom_level] ?? q.bloom_level}
        </span>

        {/* Time */}
        {q.response_time_ms != null && (
          <span className="shrink-0 text-xs tabular-nums text-text-muted">
            {(q.response_time_ms / 1000).toFixed(1)}s
          </span>
        )}

        {open ? (
          <ChevronUp size={14} className="shrink-0 text-text-muted" />
        ) : (
          <ChevronDown size={14} className="shrink-0 text-text-muted" />
        )}
      </button>

      {/* Expanded options + explanation */}
      {open && (
        <div className="space-y-2 border-t border-border-subtle bg-surface-page px-3 pb-3 pt-2.5">
          {/* Full stem */}
          <div className="mb-3 text-sm leading-relaxed text-text-strong">
            <MarkdownRenderer text={q.stem_text} />
          </div>

          {opts.map((opt) => {
            const isSel = q.selected_answer === opt;
            const isCorr = q.correct_answer === opt;
            return (
              <div
                key={opt}
                className={[
                  "flex items-start gap-2 rounded-lg px-3 py-2 text-sm",
                  isCorr
                    ? "border border-emerald-300 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200"
                    : isSel
                    ? "border border-red-300 bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-200"
                    : "border border-border-subtle text-text-body",
                ].join(" ")}
              >
                <span
                  className={[
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded text-xs font-bold",
                    isCorr ? "bg-emerald-500 text-white"
                      : isSel ? "bg-red-500 text-white"
                      : "bg-slate-200 text-slate-500 dark:bg-slate-700",
                  ].join(" ")}
                >
                  {opt}
                </span>
                <span className="flex-1">{optText[opt]}</span>
                {isCorr && <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-emerald-500" />}
                {isSel && !isCorr && <XCircle size={13} className="mt-0.5 shrink-0 text-red-400" />}
              </div>
            );
          })}

          {q.explanation_text && (
            <div className="flex items-start gap-2 rounded-lg bg-blue-50 px-3 py-2 dark:bg-blue-900/20">
              <Lightbulb size={13} className="mt-0.5 shrink-0 text-blue-500" />
              <div className="text-xs leading-relaxed text-blue-800 dark:text-blue-200">
                <MarkdownRenderer text={q.explanation_text} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sortable column header
// ---------------------------------------------------------------------------

function Th({
  label,
  sortKey,
  current,
  dir,
  onSort,
  className = "",
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: SortDir;
  onSort: (k: SortKey) => void;
  className?: string;
}) {
  const active = current === sortKey;
  return (
    <th
      className={`cursor-pointer select-none whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide ${className}`}
      style={{ color: active ? "var(--color-primary-600, #6366f1)" : "var(--text-muted)" }}
      onClick={() => onSort(sortKey)}
    >
      <span className="flex items-center gap-1">
        {label}
        {active ? (
          dir === "desc" ? <ChevronDown size={12} /> : <ChevronUp size={12} />
        ) : (
          <span className="opacity-30">
            <ChevronDown size={12} />
          </span>
        )}
      </span>
    </th>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function HistoryPage() {
  usePageTitle("AI Learning Hub - History");
  const searchParams = useSearchParams();
  const targetSessionId = searchParams.get("session_id");

  // ── Filter state ─────────────────────────────────────────────────────────
  const [typeFilter, setTypeFilter] = useState<SessionType | "">("");
  const [moduleFilter, setModuleFilter] = useState<string>("");
  const [daysFilter, setDaysFilter] = useState<number | "">("");
  const [sections, setSections] = useState<CourseSectionListItem[]>([]);

  // ── Sort state ────────────────────────────────────────────────────────────
  const [sortKey, setSortKey] = useState<SortKey>("started_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // ── Data state ────────────────────────────────────────────────────────────
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  // ── Expanded rows ─────────────────────────────────────────────────────────
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // ── Load modules for dropdown ─────────────────────────────────────────────
  useEffect(() => {
    canonicalSectionApi.list().then(setSections).catch(() => {});
  }, []);

  // ── Fetch history whenever filters / page change ──────────────────────────
  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await historyApi.list({
        session_type: typeFilter || undefined,
        section_id: moduleFilter || undefined,
        days: daysFilter || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setData(result);
    } catch {
      setError("Unable to load history. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [typeFilter, moduleFilter, daysFilter, page]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
    setExpandedId(targetSessionId ?? null);
  }, [typeFilter, moduleFilter, daysFilter, targetSessionId]);

  useEffect(() => {
    if (targetSessionId) {
      setExpandedId(targetSessionId);
    }
  }, [targetSessionId]);

  // ── Client-side sort of the current page ─────────────────────────────────
  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sortedItems = data
    ? [...data.items].sort((a, b) => {
        let va: string | number | null;
        let vb: string | number | null;
        if (sortKey === "started_at") { va = a.started_at; vb = b.started_at; }
        else if (sortKey === "session_type") { va = a.session_type; vb = b.session_type; }
        else if (sortKey === "subject") { va = a.subject; vb = b.subject; }
        else if (sortKey === "score_percent") { va = a.score_percent; vb = b.score_percent; }
        else { va = a.duration_seconds; vb = b.duration_seconds; }

        if (va === null && vb === null) return 0;
        if (va === null) return 1;
        if (vb === null) return -1;
        const cmp = va < vb ? -1 : va > vb ? 1 : 0;
        return sortDir === "desc" ? -cmp : cmp;
      })
    : [];

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;
  const summary = data?.summary;
  const targetSessionVisible = !!targetSessionId && sortedItems.some((item) => item.session_id === targetSessionId);
  const showLinkedReviewPanel = !!targetSessionId && !loading && !targetSessionVisible;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold text-text-strong">
          Learning history
        </h2>
        <p className="mt-1 text-sm text-text-body">
          Review all learning sessions, results, and detailed analysis.
        </p>
      </div>

      {/* ── Stats summary ──────────────────────────────────────────────── */}
      {summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Total sessions */}
          <div className="card flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-900/30">
              <HistoryIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-body">Total sessions</p>
              <p className="text-xs text-text-muted">
                {summary.completed_sessions} completed
              </p>
            </div>
            <p className="shrink-0 text-2xl font-bold text-text-strong">
              {summary.total_sessions}
            </p>
          </div>

          {/* Avg score */}
          <div className="card flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-900/30">
              <Award className="h-6 w-6 text-amber-600" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-body">Average score</p>
              <p className="text-xs text-text-muted">Completed sessions</p>
            </div>
            <p
              className="shrink-0 text-2xl font-bold"
              style={{ color: summary.avg_score !== null ? scoreColor(summary.avg_score) : "var(--text-muted)" }}
            >
              {summary.avg_score !== null ? `${summary.avg_score.toFixed(1)}%` : "—"}
            </p>
          </div>

          {/* Study time */}
          <div className="card flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-violet-100 dark:bg-violet-900/30">
              <Clock className="h-6 w-6 text-violet-600" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-body">Total time</p>
              <p className="text-xs text-text-muted">Accumulated study time</p>
            </div>
            <p className="shrink-0 text-2xl font-bold text-text-strong">
              {fmtStudyTime(summary.total_study_seconds)}
            </p>
          </div>

          {/* Score trend sparkline */}
          <div className="card flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-100 dark:bg-emerald-900/30">
              <TrendingUp className="h-6 w-6 text-emerald-600" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-body">Score trend</p>
              <p className="text-xs text-text-muted">Across recent sessions</p>
            </div>
            <div className="shrink-0">
              <SparkLine data={summary.score_trend} width={120} height={36} />
            </div>
          </div>
        </div>
      )}

      {/* ── Filters ───────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border-subtle bg-surface-elevated p-3">
        <Filter size={14} className="shrink-0 text-text-muted" />

        {/* Type */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as SessionType | "")}
          className="rounded-lg border border-border-subtle bg-transparent px-2.5 py-1.5 text-sm text-text-strong"
        >
          <option value="">All types</option>
          <option value="assessment">Assessment</option>
          <option value="quiz">Quiz</option>
          <option value="module_test">Module Test</option>
        </select>

        {/* Section */}
        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          className="rounded-lg border border-border-subtle bg-transparent px-2.5 py-1.5 text-sm text-text-strong"
        >
          <option value="">All modules</option>
          {sections.map((section) => (
            <option key={section.id} value={section.id}>
              {section.title}
            </option>
          ))}
        </select>

        {/* Date range */}
        <select
          value={daysFilter}
          onChange={(e) =>
            setDaysFilter(e.target.value ? Number(e.target.value) : "")
          }
          className="rounded-lg border border-border-subtle bg-transparent px-2.5 py-1.5 text-sm text-text-strong"
        >
          <option value="">All time</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
        </select>

        {/* Reset */}
        {(typeFilter || moduleFilter || daysFilter) && (
          <button
            onClick={() => {
              setTypeFilter("");
              setModuleFilter("");
              setDaysFilter("");
            }}
            className="flex items-center gap-1 text-xs text-text-muted"
          >
            <RotateCcw size={11} />
            Clear filters
          </button>
        )}

        {/* Record count */}
        {data && (
          <span className="ml-auto text-xs text-text-muted">
            {data.total} results
          </span>
        )}
      </div>

      {showLinkedReviewPanel && <LinkedReviewPanel sessionId={targetSessionId} />}

      {/* ── Table ─────────────────────────────────────────────────────── */}
      <div className="overflow-hidden rounded-2xl border border-border-subtle">
        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-3 text-sm text-red-600">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-page">
              <tr>
                <Th label="Time" sortKey="started_at" current={sortKey} dir={sortDir} onSort={handleSort} className="pl-5" />
                <Th label="Type" sortKey="session_type" current={sortKey} dir={sortDir} onSort={handleSort} />
                <Th label="Topic / Module" sortKey="subject" current={sortKey} dir={sortDir} onSort={handleSort} />
                <Th label="Score" sortKey="score_percent" current={sortKey} dir={sortDir} onSort={handleSort} />
                <Th label="Duration" sortKey="duration_seconds" current={sortKey} dir={sortDir} onSort={handleSort} />
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Details
                </th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                /* Loading skeleton rows */
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-t border-border-subtle">
                    {Array.from({ length: 6 }).map((__, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" style={{ width: j === 0 ? 80 : j === 2 ? 120 : 60 }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : sortedItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-sm text-text-muted">
                    No learning sessions match the current filters.
                  </td>
                </tr>
              ) : (
                sortedItems.map((item) => {
                  const isExpanded = expandedId === item.session_id;
                  return (
                    <Fragment key={item.session_id}>
                      <tr
                        className={[
                          "border-t border-border-subtle transition-colors",
                          isExpanded ? "bg-surface-page" : "bg-surface-elevated",
                        ].join(" ")}
                      >
                        {/* Date / time */}
                        <td className="pl-5 pr-4 py-3">
                          <p className="text-sm font-medium text-text-strong">
                            {fmtDate(item.started_at)}
                          </p>
                          <p className="text-xs text-text-muted">
                            {fmtTime(item.started_at)}
                          </p>
                        </td>

                        {/* Type badge */}
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${TYPE_COLORS[item.session_type] ?? "bg-slate-100 text-slate-600"}`}
                          >
                            {TYPE_LABELS[item.session_type] ?? item.session_type}
                          </span>
                        </td>

                        {/* Subject */}
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <p
                              className="max-w-[180px] truncate text-sm text-text-strong"
                              title={item.subject}
                            >
                              {item.subject}
                            </p>
                            {item.source === "inline_video" && item.checkpoint ? (
                              <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700">
                                {CHECKPOINT_LABELS[item.checkpoint] ?? item.checkpoint}
                              </span>
                            ) : null}
                          </div>
                        </td>

                        {/* Score */}
                        <td className="px-4 py-3">
                          {item.score_percent !== null ? (
                            <div className="flex items-center gap-2">
                              <span
                                className="text-sm font-semibold tabular-nums"
                                style={{ color: scoreColor(item.score_percent) }}
                              >
                                {item.score_percent.toFixed(1)}%
                              </span>
                              <span className="text-xs text-text-muted">
                                {item.correct_count}/{item.total_questions}
                              </span>
                            </div>
                          ) : (
                            <span className="text-sm text-text-muted">
                              {item.completed_at ? "—" : "In progress"}
                            </span>
                          )}
                        </td>

                        {/* Duration */}
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1 text-sm text-text-body">
                            <Clock size={12} />
                            {fmtDuration(item.duration_seconds)}
                          </span>
                        </td>

                        {/* Expand toggle */}
                        <td className="px-4 py-3">
                          {item.completed_at ? (
                            <button
                              onClick={() =>
                                setExpandedId((prev) =>
                                  prev === item.session_id ? null : item.session_id
                                )
                              }
                              className={[
                                "flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors",
                                isExpanded
                                  ? "bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300"
                                  : "bg-surface-page text-text-body hover:bg-surface-accent-soft hover:text-primary-700 dark:bg-slate-800 dark:text-slate-400",
                              ].join(" ")}
                            >
                              {isExpanded ? (
                                <><ChevronUp size={12} /> Collapse</>
                              ) : (
                                <><ChevronDown size={12} /> Details</>
                              )}
                            </button>
                          ) : (
                            <span className="text-xs text-text-muted">—</span>
                          )}
                        </td>
                      </tr>

                      {/* Expanded detail row */}
                      {isExpanded && (
                        <tr className="border-t border-border-subtle bg-surface-page">
                          <td colSpan={6} className="px-5 pb-4">
                            <ExpandedDetail sessionId={item.session_id} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination ──────────────────────────────────────────────── */}
        {data && totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border-subtle bg-surface-elevated px-5 py-3">
            <p className="text-xs text-text-muted">
              Page {page} / {totalPages} — {data.total} results
            </p>

            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex h-7 w-7 items-center justify-center rounded-lg border border-border-subtle text-text-body disabled:opacity-40"
              >
                <ChevronLeft size={14} />
              </button>

              {/* Page numbers — show ±2 around current */}
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
                .reduce<(number | "…")[]>((acc, p, i, arr) => {
                  if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push("…");
                  acc.push(p);
                  return acc;
                }, [])
                .map((p, i) =>
                  p === "…" ? (
                    <span key={`ellipsis-${i}`} className="px-1 text-xs text-text-muted">
                      …
                    </span>
                  ) : (
                    <button
                      key={p}
                      onClick={() => setPage(p as number)}
                      className={[
                        "flex h-7 w-7 items-center justify-center rounded-lg border text-xs font-medium transition-colors",
                        p === page
                          ? "border-primary-500 bg-primary-500 text-white"
                          : "border-border-subtle text-text-body",
                      ].join(" ")}
                    >
                      {p}
                    </button>
                  )
                )}

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="flex h-7 w-7 items-center justify-center rounded-lg border border-border-subtle text-text-body disabled:opacity-40"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
