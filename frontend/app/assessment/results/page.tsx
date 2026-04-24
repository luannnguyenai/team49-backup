"use client";
// app/assessment/results/page.tsx
// Assessment results: overall score · radar chart · per-learning-unit table · misconceptions · CTA

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Trophy,
} from "lucide-react";

import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import RadarChart from "@/components/assessment/RadarChart";
import { assessmentApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AssessmentResultResponse, MasteryLevel } from "@/types";

// ---------------------------------------------------------------------------
// Mastery level display config
// ---------------------------------------------------------------------------

const MASTERY_CONFIG: Record<
  MasteryLevel,
  { label: string; color: string; bg: string }
> = {
  not_started: { label: "Chưa bắt đầu", color: "text-slate-500 dark:text-slate-400",  bg: "bg-slate-100 dark:bg-slate-800"   },
  novice:     { label: "Mới bắt đầu",  color: "text-red-600 dark:text-red-400",    bg: "bg-red-50 dark:bg-red-900/20"    },
  developing: { label: "Đang phát triển", color: "text-orange-600 dark:text-orange-400", bg: "bg-orange-50 dark:bg-orange-900/20" },
  proficient: { label: "Thành thạo",   color: "text-blue-600 dark:text-blue-400",   bg: "bg-blue-50 dark:bg-blue-900/20"   },
  mastered:   { label: "Chuyên sâu",   color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-900/20" },
};

const BLOOM_VI: Record<string, string> = {
  remember:   "Nhớ",
  understand: "Hiểu",
  apply:      "Áp dụng",
  analyze:    "Phân tích",
};

// ---------------------------------------------------------------------------
// Overall score → message
// ---------------------------------------------------------------------------

function scoreMessage(pct: number): { emoji: string; text: string } {
  if (pct >= 80) return { emoji: "🏆", text: "Xuất sắc! Bạn nắm vững kiến thức rất tốt." };
  if (pct >= 60) return { emoji: "👍", text: "Tốt! Bạn đang trên đà phát triển." };
  if (pct >= 40) return { emoji: "📚", text: "Cần ôn tập thêm — lộ trình sẽ giúp bạn." };
  return { emoji: "🌱", text: "Hãy bắt đầu từ nền tảng — bạn sẽ tiến bộ nhanh thôi!" };
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700",
        className
      )}
    />
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function AssessmentResultsInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const next = searchParams.get("next");

  const [result, setResult] = useState<AssessmentResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedLearningUnit, setExpandedLearningUnit] = useState<string | null>(null);
  const [navigating, setNavigating] = useState(false);

  // ── Fetch results ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) {
      setError("Không tìm thấy session. Vui lòng làm lại assessment.");
      setLoading(false);
      return;
    }

    assessmentApi
      .results(sessionId)
      .then((data) => {
        setResult(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Không thể tải kết quả. Vui lòng thử lại.");
        setLoading(false);
      });
  }, [sessionId]);

  // ── Go to dashboard ───────────────────────────────────────────────────────
  const goToDashboard = () => {
    setNavigating(true);
    router.push(next ?? "/dashboard");
  };

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        className="min-h-screen py-10 px-4"
        style={{ backgroundColor: "var(--bg-page)" }}
      >
        <div className="mx-auto max-w-2xl space-y-6">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (error || !result) {
    return (
      <div
        className="flex min-h-screen items-center justify-center p-4"
        style={{ backgroundColor: "var(--bg-page)" }}
      >
        <div className="card max-w-md w-full text-center space-y-4">
          <AlertTriangle className="mx-auto h-10 w-10 text-red-500" />
          <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
            {error ?? "Không tìm thấy kết quả"}
          </p>
          <Button onClick={() => router.push("/assessment")} variant="secondary">
            Làm lại assessment
          </Button>
        </div>
      </div>
    );
  }

  // ── Derived values ────────────────────────────────────────────────────────
  const { overall_score_percent: overall, learning_unit_results } = result;
  const { emoji, text: msg } = scoreMessage(overall);

  const radarData = learning_unit_results.map((tr) => ({
    label: tr.learning_unit_title,
    value: tr.score_percent,
    level: tr.mastery_level,
  }));

  const allMisconceptions = learning_unit_results.flatMap((tr) =>
    tr.misconceptions_detected.map((m) => ({ learningUnit: tr.learning_unit_title, id: m }))
  );

  // ── Results UI ────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen py-10 px-4"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      {/* Background blobs */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-emerald-400/10 blur-3xl" />
      </div>

      <div className="relative mx-auto w-full max-w-2xl space-y-6 animate-fade-in">

        {/* ── Header ── */}
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/30">
            <Brain className="h-6 w-6 text-white" />
          </div>
          <h1
            className="text-xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Kết quả Assessment
          </h1>
        </div>

        {/* ── Overall score card ── */}
        <div className="card text-center space-y-3">
          <span className="text-5xl">{emoji}</span>
          <div>
            <p className="text-4xl font-extrabold text-primary-600">
              {overall.toFixed(1)}%
            </p>
            <p className="mt-1 text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              tổng thể
            </p>
          </div>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {msg}
          </p>

          {/* Quick mastery summary chips */}
          <div className="flex flex-wrap justify-center gap-2 pt-1">
            {learning_unit_results.map((tr) => {
              const cfg = MASTERY_CONFIG[tr.mastery_level];
              return (
                <span
                  key={tr.learning_unit_id}
                  className={cn("rounded-full px-3 py-1 text-xs font-semibold", cfg.bg, cfg.color)}
                >
                  {tr.learning_unit_title}: {cfg.label}
                </span>
              );
            })}
          </div>
        </div>

        {/* ── Radar chart ── */}
        {radarData.length > 1 && (
          <div className="card flex flex-col items-center gap-4">
            <h2
              className="self-start text-sm font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Mastery theo learning unit
            </h2>
            <div className="w-full max-w-xs">
              <RadarChart data={radarData} size={300} />
            </div>
            {/* Legend */}
            <div className="flex flex-wrap justify-center gap-3">
              {(["novice", "developing", "proficient", "mastered"] as MasteryLevel[]).map((lvl) => {
                const cfg = MASTERY_CONFIG[lvl];
                return (
                  <span key={lvl} className={cn("flex items-center gap-1.5 text-xs font-medium", cfg.color)}>
                    <span className={cn("h-2.5 w-2.5 rounded-full", cfg.bg.replace("bg-", "bg-").replace("/20", ""))} />
                    {cfg.label}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Per-learning-unit detail table ── */}
        <div className="card overflow-hidden p-0">
          <div
            className="border-b px-6 py-4"
            style={{ borderColor: "var(--border)" }}
          >
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Chi tiết theo learning unit
            </h2>
          </div>

          {/* Table header */}
          <div
            className="hidden grid-cols-4 gap-4 border-b px-6 py-2.5 text-xs font-medium sm:grid"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          >
            <span>Learning unit</span>
            <span className="text-center">Score</span>
            <span className="text-center">Level</span>
            <span className="text-center">Bloom Max</span>
          </div>

          {learning_unit_results.map((tr) => {
            const cfg = MASTERY_CONFIG[tr.mastery_level];
            const isExpanded = expandedLearningUnit === tr.learning_unit_id;

            // Highest bloom level achieved from breakdown
            const bloomMaxKey = Object.entries(tr.bloom_breakdown)
              .filter(([, val]) => {
                const [correct] = val.split("/").map(Number);
                return correct > 0;
              })
              .map(([k]) => k)
              .at(-1);

            return (
              <div key={tr.learning_unit_id} style={{ borderColor: "var(--border)" }} className="border-b last:border-0">
                {/* Main row */}
                <button
                  type="button"
                  className="flex w-full items-center px-6 py-4 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                  onClick={() => setExpandedLearningUnit(isExpanded ? null : tr.learning_unit_id)}
                >
                  <div className="flex flex-1 flex-col gap-1 sm:grid sm:grid-cols-4 sm:items-center sm:gap-4">
                    {/* Learning unit title */}
                    <span
                      className="text-sm font-medium"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {tr.learning_unit_title}
                    </span>

                    {/* Score bar */}
                    <div className="flex items-center gap-2 sm:justify-center">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                        <div
                          className="h-full rounded-full bg-primary-600 transition-all"
                          style={{ width: `${tr.score_percent}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-primary-600">
                        {tr.score_percent.toFixed(0)}%
                      </span>
                    </div>

                    {/* Level badge */}
                    <div className="sm:text-center">
                      <span
                        className={cn(
                          "inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold",
                          cfg.bg,
                          cfg.color
                        )}
                      >
                        {cfg.label}
                      </span>
                    </div>

                    {/* Bloom max */}
                    <span
                      className="text-xs sm:text-center"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {bloomMaxKey ? BLOOM_VI[bloomMaxKey] ?? bloomMaxKey : "—"}
                    </span>
                  </div>

                  {/* Expand icon */}
                  <span className="ml-3 shrink-0" style={{ color: "var(--text-muted)" }}>
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </span>
                </button>

                {/* Expanded detail */}
                {isExpanded && (
                  <div
                    className="animate-fade-in border-t px-6 py-4"
                    style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-page)" }}
                  >
                    {/* Bloom breakdown */}
                    <p className="mb-2 text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>
                      Bloom breakdown
                    </p>
                    <div className="mb-3 flex flex-wrap gap-2">
                      {Object.entries(tr.bloom_breakdown).map(([bloom, val]) => {
                        const [correct, total] = val.split("/").map(Number);
                        if (total === 0) return null;
                        return (
                          <span
                            key={bloom}
                            className="rounded-lg border px-2.5 py-1 text-xs"
                            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                          >
                            {BLOOM_VI[bloom] ?? bloom}:{" "}
                            <strong style={{ color: "var(--text-primary)" }}>
                              {correct}/{total}
                            </strong>
                          </span>
                        );
                      })}
                    </div>

                    {/* Weak KCs */}
                    {tr.weak_kcs.length > 0 && (
                      <div className="mb-2">
                        <p className="mb-1.5 text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>
                          Kiến thức cần ôn
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {tr.weak_kcs.map((kc) => (
                            <span
                              key={kc}
                              className="rounded-full bg-amber-50 dark:bg-amber-900/20 px-2.5 py-1 text-xs text-amber-700 dark:text-amber-300"
                            >
                              {kc}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Misconceptions ── */}
        {allMisconceptions.length > 0 && (
          <div className="card space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <h2
                className="text-sm font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                Hiểu nhầm phát hiện ({allMisconceptions.length})
              </h2>
            </div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Những misconception này được phát hiện dựa trên đáp án sai của bạn. Lộ trình học sẽ ưu tiên giải quyết chúng.
            </p>
            <div className="space-y-2">
              {allMisconceptions.map((m, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2.5 rounded-lg border px-3 py-2.5"
                  style={{ borderColor: "var(--border)" }}
                >
                  <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                  <div>
                    <p className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                      {m.learningUnit}
                    </p>
                    <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                      {m.id}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── No misconceptions ── */}
        {allMisconceptions.length === 0 && overall >= 60 && (
          <div className="card flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Không phát hiện misconception nào. Kiến thức của bạn khá vững!
            </p>
          </div>
        )}

        {/* ── CTA ── */}
        <div className="card flex flex-col items-center gap-4 text-center">
          <Trophy className="h-8 w-8 text-primary-600" />
          <div>
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
              Assessment hoàn thành!
            </p>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              AI đã ghi nhận trình độ của bạn và sẵn sàng tạo lộ trình học cá nhân hóa.
            </p>
          </div>
          <Button
            onClick={goToDashboard}
            loading={navigating}
            size="lg"
            rightIcon={!navigating ? <ArrowRight className="h-4 w-4" /> : undefined}
          >
            Xem lộ trình học
          </Button>
        </div>

        <p className="pb-4 text-center text-xs" style={{ color: "var(--text-muted)" }}>
          Session ID: {result.session_id}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Suspense boundary required by useSearchParams in Next.js 14 App Router
// ---------------------------------------------------------------------------

export default function AssessmentResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: "var(--bg-page)" }}>
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <AssessmentResultsInner />
    </Suspense>
  );
}
