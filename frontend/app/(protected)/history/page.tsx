"use client";

// app/(protected)/history/page.tsx
// Learning History page:
//   • Stats bar: total sessions, avg score, study time, mini SVG line chart
//   • Filters: type, module, date range
//   • Sortable table (date, type, subject, score, duration)
//   • Expandable rows: per-question breakdown, bloom analysis, misconceptions
//   • Pagination (20 / page)

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock,
  Filter,
  Lightbulb,
  RotateCcw,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { contentApi, historyApi } from "@/lib/api";
import type {
  BloomLevel,
  HistoryItem,
  HistoryResponse,
  ModuleListItem,
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
  practice: "Luyện tập",
};

const TYPE_COLORS: Record<SessionType, string> = {
  assessment: "bg-violet-100 text-violet-700",
  quiz: "bg-blue-100 text-blue-700",
  module_test: "bg-amber-100 text-amber-700",
  practice: "bg-slate-100 text-slate-600",
};

const BLOOM_VI: Record<string, string> = {
  remember: "Nhớ",
  understand: "Hiểu",
  apply: "Áp dụng",
  analyze: "Phân tích",
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
  return new Date(iso).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString("vi-VN", {
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
      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
        Chưa đủ dữ liệu
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
            <span className="w-20 text-right text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              {BLOOM_VI[level] ?? level}
            </span>
            <div className="flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700 h-2">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${pct}%`, background: BLOOM_BAR_COLOR[level] ?? "#94a3b8" }}
              />
            </div>
            <span className="w-10 text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
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
  sessionType,
}: {
  sessionId: string;
  sessionType: SessionType;
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
        setError(typeof d === "string" ? d : "Không thể tải chi tiết.");
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
      <p className="py-4 text-center text-sm text-red-500">{error || "Không có dữ liệu."}</p>
    );
  }

  return (
    <div className="space-y-5 px-1 py-3">
      {/* Bloom + KCs + misconceptions side-by-side */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Bloom breakdown */}
        <div
          className="rounded-xl border p-3"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
        >
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            <Brain size={12} /> Bloom
          </p>
          <BloomBar breakdown={detail.bloom_breakdown} />
        </div>

        {/* Weak KCs */}
        <div
          className="rounded-xl border p-3"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
        >
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            <BookOpen size={12} /> Kiến thức yếu
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
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Không có</p>
          )}
        </div>

        {/* Misconceptions */}
        <div
          className="rounded-xl border p-3"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
        >
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            <Lightbulb size={12} /> Hiểu nhầm
          </p>
          {detail.misconceptions.length > 0 ? (
            <ul className="space-y-1">
              {detail.misconceptions.map((m) => (
                <li key={m} className="flex items-start gap-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-400" />
                  {m}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Không phát hiện</p>
          )}
        </div>
      </div>

      {/* Per-question list */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Chi tiết từng câu ({detail.questions.length} câu)
        </p>
        <div className="space-y-1.5">
          {detail.questions.map((q, i) => (
            <QuestionRow
              key={q.question_id}
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
    <div
      className="overflow-hidden rounded-xl border"
      style={{ borderColor: "var(--border)" }}
    >
      {/* Header row */}
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
        style={{ background: "var(--bg-elevated)" }}
      >
        {/* Correct / Wrong icon */}
        {q.is_correct ? (
          <CheckCircle2 size={14} className="shrink-0 text-emerald-500" />
        ) : (
          <XCircle size={14} className="shrink-0 text-red-400" />
        )}

        <span className="shrink-0 text-xs font-medium" style={{ color: "var(--text-muted)" }}>
          {num}.
        </span>

        {/* Stem preview */}
        <span className="flex-1 truncate text-sm" style={{ color: "var(--text-primary)" }}>
          {q.stem_text.replace(/[#*`]/g, "").slice(0, 100)}
        </span>

        {/* Bloom badge */}
        <span className="hidden shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800 sm:inline" style={{ color: "var(--text-muted)" }}>
          {BLOOM_VI[q.bloom_level] ?? q.bloom_level}
        </span>

        {/* Time */}
        {q.response_time_ms != null && (
          <span className="shrink-0 text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
            {(q.response_time_ms / 1000).toFixed(1)}s
          </span>
        )}

        {open ? (
          <ChevronUp size={14} className="shrink-0" style={{ color: "var(--text-muted)" }} />
        ) : (
          <ChevronDown size={14} className="shrink-0" style={{ color: "var(--text-muted)" }} />
        )}
      </button>

      {/* Expanded options + explanation */}
      {open && (
        <div
          className="border-t px-3 pb-3 pt-2.5 space-y-2"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
        >
          {/* Full stem */}
          <div className="mb-3 text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
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
                    : "border",
                ].join(" ")}
                style={!isCorr && !isSel ? { borderColor: "var(--border)", color: "var(--text-secondary)" } : {}}
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
  // ── Filter state ─────────────────────────────────────────────────────────
  const [typeFilter, setTypeFilter] = useState<SessionType | "">("");
  const [moduleFilter, setModuleFilter] = useState<string>("");
  const [daysFilter, setDaysFilter] = useState<number | "">("");
  const [modules, setModules] = useState<ModuleListItem[]>([]);

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
    contentApi.modules().then(setModules).catch(() => {});
  }, []);

  // ── Fetch history whenever filters / page change ──────────────────────────
  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await historyApi.list({
        session_type: typeFilter || undefined,
        module_id: moduleFilter || undefined,
        days: daysFilter || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setData(result);
    } catch {
      setError("Không thể tải lịch sử. Vui lòng thử lại.");
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
    setExpandedId(null);
  }, [typeFilter, moduleFilter, daysFilter]);

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

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Lịch sử học tập
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Xem lại tất cả phiên học, kết quả và phân tích chi tiết.
        </p>
      </div>

      {/* ── Stats summary ──────────────────────────────────────────────── */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {/* Total sessions */}
          <div className="card py-3 px-4">
            <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              Tổng phiên học
            </p>
            <p className="mt-1 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              {summary.total_sessions}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {summary.completed_sessions} hoàn thành
            </p>
          </div>

          {/* Avg score */}
          <div className="card py-3 px-4">
            <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              Điểm trung bình
            </p>
            <p
              className="mt-1 text-2xl font-bold"
              style={{ color: summary.avg_score !== null ? scoreColor(summary.avg_score) : "var(--text-muted)" }}
            >
              {summary.avg_score !== null ? `${summary.avg_score.toFixed(1)}%` : "—"}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Các phiên hoàn thành
            </p>
          </div>

          {/* Study time */}
          <div className="card py-3 px-4">
            <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              Tổng thời gian
            </p>
            <p className="mt-1 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              {fmtStudyTime(summary.total_study_seconds)}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Thời gian học tích lũy
            </p>
          </div>

          {/* Score trend sparkline */}
          <div className="card py-3 px-4">
            <p className="mb-1 flex items-center gap-1 text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              <TrendingUp size={11} /> Xu hướng điểm
            </p>
            <SparkLine data={summary.score_trend} width={140} height={40} />
          </div>
        </div>
      )}

      {/* ── Filters ───────────────────────────────────────────────────── */}
      <div
        className="flex flex-wrap items-center gap-3 rounded-xl border p-3"
        style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
      >
        <Filter size={14} style={{ color: "var(--text-muted)" }} className="shrink-0" />

        {/* Type */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as SessionType | "")}
          className="rounded-lg border bg-transparent px-2.5 py-1.5 text-sm"
          style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          <option value="">Tất cả loại</option>
          <option value="assessment">Assessment</option>
          <option value="quiz">Quiz</option>
          <option value="module_test">Module Test</option>
        </select>

        {/* Module */}
        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          className="rounded-lg border bg-transparent px-2.5 py-1.5 text-sm"
          style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          <option value="">Tất cả module</option>
          {modules.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>

        {/* Date range */}
        <select
          value={daysFilter}
          onChange={(e) =>
            setDaysFilter(e.target.value ? Number(e.target.value) : "")
          }
          className="rounded-lg border bg-transparent px-2.5 py-1.5 text-sm"
          style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          <option value="">Toàn bộ thời gian</option>
          <option value="7">7 ngày qua</option>
          <option value="30">30 ngày qua</option>
        </select>

        {/* Reset */}
        {(typeFilter || moduleFilter || daysFilter) && (
          <button
            onClick={() => {
              setTypeFilter("");
              setModuleFilter("");
              setDaysFilter("");
            }}
            className="flex items-center gap-1 text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            <RotateCcw size={11} />
            Xóa bộ lọc
          </button>
        )}

        {/* Record count */}
        {data && (
          <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
            {data.total} kết quả
          </span>
        )}
      </div>

      {/* ── Table ─────────────────────────────────────────────────────── */}
      <div
        className="overflow-hidden rounded-2xl border"
        style={{ borderColor: "var(--border)" }}
      >
        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 border-b px-4 py-3 text-sm text-red-600" style={{ borderColor: "var(--border)" }}>
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead style={{ background: "var(--bg-secondary)" }}>
              <tr>
                <Th label="Thời gian" sortKey="started_at" current={sortKey} dir={sortDir} onSort={handleSort} className="pl-5" />
                <Th label="Loại" sortKey="session_type" current={sortKey} dir={sortDir} onSort={handleSort} />
                <Th label="Topic / Module" sortKey="subject" current={sortKey} dir={sortDir} onSort={handleSort} />
                <Th label="Điểm" sortKey="score_percent" current={sortKey} dir={sortDir} onSort={handleSort} />
                <Th label="Thời lượng" sortKey="duration_seconds" current={sortKey} dir={sortDir} onSort={handleSort} />
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                  Chi tiết
                </th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                /* Loading skeleton rows */
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-t" style={{ borderColor: "var(--border)" }}>
                    {Array.from({ length: 6 }).map((__, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" style={{ width: j === 0 ? 80 : j === 2 ? 120 : 60 }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : sortedItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                    Chưa có phiên học nào phù hợp với bộ lọc.
                  </td>
                </tr>
              ) : (
                sortedItems.map((item) => {
                  const isExpanded = expandedId === item.session_id;
                  return (
                    <>
                      <tr
                        key={item.session_id}
                        className="border-t transition-colors"
                        style={{
                          borderColor: "var(--border)",
                          background: isExpanded ? "var(--bg-secondary)" : "var(--bg-elevated)",
                        }}
                      >
                        {/* Date / time */}
                        <td className="pl-5 pr-4 py-3">
                          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                            {fmtDate(item.started_at)}
                          </p>
                          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
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
                          <p
                            className="max-w-[180px] truncate text-sm"
                            style={{ color: "var(--text-primary)" }}
                            title={item.subject}
                          >
                            {item.subject}
                          </p>
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
                              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                                {item.correct_count}/{item.total_questions}
                              </span>
                            </div>
                          ) : (
                            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                              {item.completed_at ? "—" : "Đang học"}
                            </span>
                          )}
                        </td>

                        {/* Duration */}
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1 text-sm" style={{ color: "var(--text-secondary)" }}>
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
                                  ? "bg-primary-100 text-primary-700"
                                  : "bg-slate-100 text-slate-600 hover:bg-primary-50 hover:text-primary-600 dark:bg-slate-800 dark:text-slate-400",
                              ].join(" ")}
                            >
                              {isExpanded ? (
                                <><ChevronUp size={12} /> Thu gọn</>
                              ) : (
                                <><ChevronDown size={12} /> Chi tiết</>
                              )}
                            </button>
                          ) : (
                            <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>
                          )}
                        </td>
                      </tr>

                      {/* Expanded detail row */}
                      {isExpanded && (
                        <tr
                          key={`${item.session_id}-detail`}
                          className="border-t"
                          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
                        >
                          <td colSpan={6} className="px-5 pb-4">
                            <ExpandedDetail
                              sessionId={item.session_id}
                              sessionType={item.session_type}
                            />
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination ──────────────────────────────────────────────── */}
        {data && totalPages > 1 && (
          <div
            className="flex items-center justify-between border-t px-5 py-3"
            style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
          >
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Trang {page} / {totalPages} — {data.total} kết quả
            </p>

            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex h-7 w-7 items-center justify-center rounded-lg border disabled:opacity-40"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
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
                    <span key={`ellipsis-${i}`} className="px-1 text-xs" style={{ color: "var(--text-muted)" }}>
                      …
                    </span>
                  ) : (
                    <button
                      key={p}
                      onClick={() => setPage(p as number)}
                      className="flex h-7 w-7 items-center justify-center rounded-lg border text-xs font-medium transition-colors"
                      style={{
                        borderColor: p === page ? "var(--color-primary-500, #6366f1)" : "var(--border)",
                        background: p === page ? "var(--color-primary-500, #6366f1)" : undefined,
                        color: p === page ? "white" : "var(--text-secondary)",
                      }}
                    >
                      {p}
                    </button>
                  )
                )}

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="flex h-7 w-7 items-center justify-center rounded-lg border disabled:opacity-40"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
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
