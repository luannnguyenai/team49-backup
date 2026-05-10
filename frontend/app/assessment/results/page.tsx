"use client";
// app/assessment/results/page.tsx
// Assessment results: compact summary · priority units · CTA

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Lightbulb,
  Trophy,
} from "lucide-react";

import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { buildAssessmentNextHref } from "@/components/onboarding/onboardingNavigation";
import { assessmentApi } from "@/lib/api";
import {
  buildAssessmentResultViewModel,
  type AssessmentPriorityItem,
} from "@/lib/assessment-results-view-model";
import { cn } from "@/lib/utils";
import type {
  AssessmentAISummaryResponse,
  AssessmentResultResponse,
  MasteryLevel,
} from "@/types";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const MASTERY_CONFIG: Record<
  MasteryLevel,
  { label: string; color: string; bg: string }
> = {
  not_started: { label: "Not started", color: "text-slate-500 dark:text-slate-400",      bg: "bg-slate-100 dark:bg-slate-800"        },
  novice:      { label: "Novice",  color: "text-red-600 dark:text-red-400",           bg: "bg-red-50 dark:bg-red-900/20"          },
  developing:  { label: "Developing", color: "text-orange-600 dark:text-orange-400",  bg: "bg-orange-50 dark:bg-orange-900/20"    },
  proficient:  { label: "Proficient",   color: "text-blue-600 dark:text-blue-400",          bg: "bg-blue-50 dark:bg-blue-900/20"        },
  mastered:    { label: "Mastered",   color: "text-emerald-600 dark:text-emerald-400",    bg: "bg-emerald-50 dark:bg-emerald-900/20"  },
};

const DECISION_OPTIONS: { value: string; label: string }[] = [
  { value: "skip",    label: "Skip"  },
  { value: "review",  label: "Review"  },
  { value: "relearn", label: "Relearn" },
];

const DECISION_LABEL: Record<string, string> = {
  skip:    "Skip",
  review:  "Review",
  relearn: "Relearn",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreMessage(pct: number): { emoji: string; text: string } {
  if (pct >= 80) return { emoji: "🏆", text: "Excellent work. You have a strong grasp of the material." };
  if (pct >= 60) return { emoji: "👍", text: "Good progress. You are building momentum." };
  if (pct >= 40) return { emoji: "📚", text: "You need more review, and the learning path will help." };
  return { emoji: "🌱", text: "Start from the fundamentals and you can improve quickly." };
}

function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700", className)} />
  );
}

// ---------------------------------------------------------------------------
// Toast (inline, no library)
// ---------------------------------------------------------------------------

interface ToastItem { id: number; message: string; type: "success" | "error" }

function Toast({ items }: { items: ToastItem[] }) {
  if (items.length === 0) return null;
  return (
    <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 flex flex-col gap-2 items-center">
      {items.map((t) => (
        <div
          key={t.id}
          className={cn(
            "rounded-xl px-5 py-2.5 text-sm font-medium shadow-lg",
            t.type === "success"
              ? "bg-emerald-600 text-white"
              : "bg-red-600 text-white"
          )}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compact decision row
// ---------------------------------------------------------------------------

interface DecisionRowProps {
  item: AssessmentPriorityItem;
  currentDecision: string;
  onDecisionChange: (unitId: string, newDecision: string, oldDecision: string) => void;
}

function DecisionRow({ item, currentDecision, onDecisionChange }: DecisionRowProps) {
  const cfg = MASTERY_CONFIG[item.masteryLevel as MasteryLevel] ?? MASTERY_CONFIG.not_started;

  return (
    <div
      className="grid gap-3 rounded-xl border p-3 sm:grid-cols-[1fr_auto_auto] sm:items-center"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
    >
      <div className="min-w-0">
        <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text-primary)" }}>
          {item.title}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", cfg.bg, cfg.color)}>
            {cfg.label}
          </span>
          <span className="text-xs font-medium text-primary-600">
            {item.scorePercent.toFixed(0)}%
            {typeof item.questionsCorrect === "number" && typeof item.questionsTotal === "number"
              ? ` (${item.questionsCorrect}/${item.questionsTotal})`
              : null}
          </span>
        </div>
      </div>

      <span
        className={cn(
          "w-fit rounded-full px-3 py-1 text-xs font-semibold",
          currentDecision === "relearn"
            ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
            : currentDecision === "review"
              ? "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
              : "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300",
        )}
      >
        {DECISION_LABEL[currentDecision] ?? currentDecision}
      </span>

      <select
        aria-label={`Adjust ${item.title}`}
        value={currentDecision}
        onChange={(event) => onDecisionChange(item.id, event.target.value, currentDecision)}
        className="rounded-lg border bg-white px-3 py-2 text-xs font-medium dark:bg-slate-900"
        style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
      >
        {DECISION_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main inner component
// ---------------------------------------------------------------------------

function AssessmentResultsInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const next = searchParams.get("next");

  const [result, setResult] = useState<AssessmentResultResponse | null>(null);
  const [aiSummary, setAiSummary] = useState<AssessmentAISummaryResponse | null>(null);
  const [aiSummaryLoading, setAiSummaryLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [navigating, setNavigating] = useState(false);

  // Decision override state: unitId → decision string
  const [decisions, setDecisions] = useState<Record<string, string>>({});

  // Toast
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastCounter = useRef(0);

  function showToast(message: string, type: "success" | "error" = "success") {
    const id = ++toastCounter.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 1500);
  }

  // ── Fetch results ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) {
      setError("No session was found. Please retake the assessment.");
      setLoading(false);
      return;
    }

    assessmentApi
      .results(sessionId)
      .then((data) => {
        setResult(data);
        // Seed decision state from server-computed decisions
        if (data.topic_decisions) {
          const initial: Record<string, string> = {};
          for (const td of data.topic_decisions) {
            initial[td.topic_unit_id] = td.decision;
          }
          setDecisions(initial);
        }
        setLoading(false);
        setAiSummaryLoading(true);
        assessmentApi
          .summary(sessionId)
          .then((summary) => {
            setAiSummary(summary);
          })
          .catch(() => {
            setAiSummary(null);
          })
          .finally(() => {
            setAiSummaryLoading(false);
          });
      })
      .catch(() => {
        setError("Unable to load the results. Please try again.");
        setLoading(false);
      });
  }, [sessionId]);

  // ── Decision change handler ───────────────────────────────────────────────
  async function handleDecisionChange(unitId: string, newDecision: string, oldDecision: string) {
    if (!sessionId || newDecision === oldDecision) return;

    // Optimistic update
    setDecisions((prev) => ({ ...prev, [unitId]: newDecision }));

    try {
      await assessmentApi.updateTopicDecision(sessionId, unitId, newDecision);
      showToast("Updated", "success");
    } catch {
      // Rollback
      setDecisions((prev) => ({ ...prev, [unitId]: oldDecision }));
      showToast("Update failed", "error");
    }
  }

  // ── Go to dashboard ───────────────────────────────────────────────────────
  const goToNextStep = () => {
    setNavigating(true);
    router.push(buildAssessmentNextHref(next));
  };

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen py-10 px-4" style={{ backgroundColor: "var(--bg-page)" }}>
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
            {error ?? "Results not found"}
          </p>
          <Button onClick={() => router.push("/assessment")} variant="secondary">
            Retake assessment
          </Button>
        </div>
      </div>
    );
  }

  // ── Derived values ────────────────────────────────────────────────────────
  const { overall_score_percent: overall } = result;
  const { emoji, text: msg } = scoreMessage(overall);
  const viewModel = buildAssessmentResultViewModel(result);
  const allMisconceptions = viewModel.misconceptions;
  const displayedMisconceptions = allMisconceptions.slice(0, 3);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen py-10 px-4" style={{ backgroundColor: "var(--bg-page)" }}>
      {/* Background blobs */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-emerald-400/10 blur-3xl" />
      </div>

      <Toast items={toasts} />

      <div className="relative mx-auto w-full max-w-2xl space-y-6 animate-fade-in">

        {/* ── Header ── */}
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/30">
            <Brain className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
            Assessment Results
          </h1>
        </div>

        {/* ── Overall score card ── */}
        <div className="card overflow-hidden p-0">
          <div className="bg-gradient-to-br from-primary-600 to-blue-700 p-5 text-white sm:p-6">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
                  Quick assessment
                </p>
                <h2 className="text-xl font-bold leading-tight">Results summary</h2>
                <p className="max-w-xl text-sm leading-relaxed text-white/80">
                  {msg}
                </p>
              </div>
              <div className="shrink-0 rounded-3xl bg-white/15 px-5 py-4 text-center ring-1 ring-white/20">
                <span className="text-3xl">{emoji}</span>
                <p className="text-4xl font-extrabold">{overall.toFixed(1)}%</p>
                <p className="mt-1 text-xs font-medium text-white/70">overall score</p>
              </div>
            </div>
          </div>

          <div className="space-y-4 p-5 sm:p-6">
            {aiSummaryLoading && (
              <div className="rounded-2xl border border-primary-100 bg-primary-50 p-4 text-sm text-primary-800 dark:border-primary-900/40 dark:bg-primary-900/20 dark:text-primary-200">
                AI is summarizing your results...
              </div>
            )}

            {aiSummary?.summary && (
              <div className="space-y-3 rounded-2xl border border-primary-100 bg-primary-50 p-4 dark:border-primary-900/40 dark:bg-primary-900/20">
                <div className="flex items-center gap-2 text-primary-800 dark:text-primary-200">
                  <Brain className="h-4 w-4" />
                  <p className="text-sm font-semibold">AI summary</p>
                </div>
                <p className="text-sm leading-relaxed text-primary-900 dark:text-primary-100">
                  {aiSummary.summary}
                </p>
                {aiSummary.highlights.length > 0 && (
                  <ul className="space-y-1.5">
                    {aiSummary.highlights.map((highlight) => (
                      <li key={highlight} className="text-sm text-primary-800 dark:text-primary-200">
                        - {highlight}
                      </li>
                    ))}
                  </ul>
                )}
                {aiSummary.next_step && (
                  <p className="text-sm font-medium text-primary-900 dark:text-primary-100">
                    {aiSummary.next_step}
                  </p>
                )}
              </div>
            )}

            {aiSummary && !aiSummary.available && !aiSummaryLoading && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100">
                AI feedback is temporarily unavailable. Your scored placement results below are still saved.
              </div>
            )}

            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-2xl bg-red-50 p-3 dark:bg-red-900/20">
                <p className="text-2xl font-bold text-red-600 dark:text-red-300">
                  {viewModel.counts.relearn}
                </p>
                <p className="text-xs font-medium text-red-700 dark:text-red-300">relearn</p>
              </div>
              <div className="rounded-2xl bg-amber-50 p-3 dark:bg-amber-900/20">
                <p className="text-2xl font-bold text-amber-600 dark:text-amber-300">
                  {viewModel.counts.review}
                </p>
                <p className="text-xs font-medium text-amber-700 dark:text-amber-300">review</p>
              </div>
              <div className="rounded-2xl bg-emerald-50 p-3 dark:bg-emerald-900/20">
                <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-300">
                  {viewModel.counts.skip}
                </p>
                <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300">skip</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Compact priority list ── */}
        <div className="card space-y-4">
          <div>
            <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Learning path priorities
            </h2>
            <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
              This view shows up to 5 sections that need action, without repeating the full assessment list.
            </p>
          </div>

          {viewModel.priorityItems.length > 0 ? (
            <div className="space-y-2">
              {viewModel.priorityItems.map((item) => (
                <DecisionRow
                  key={item.id}
                  item={item}
                  currentDecision={decisions[item.id] ?? item.decision}
                  onDecisionChange={handleDecisionChange}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300">
              No sections need relearning. The path will skip the areas you already know well.
            </div>
          )}
        </div>

        {/* ── Skipped/mastered summary ── */}
        {viewModel.counts.skip > 0 && (
          <div className="card flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {viewModel.counts.skip} sections will be skipped
              </h2>
              <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                These are the areas you already handled well on the assessment. The planner will use this automatically when building your path.
              </p>
              <div className="mt-3 space-y-2">
                {viewModel.masteredPreview.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-lg border border-emerald-100 bg-emerald-50/70 px-3 py-2 dark:border-emerald-900/40 dark:bg-emerald-900/20"
                  >
                    <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-100">
                      {item.title}
                    </p>
                    <p className="mt-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                      {item.scorePercent.toFixed(0)}%
                      {typeof item.questionsCorrect === "number" && typeof item.questionsTotal === "number"
                        ? ` (${item.questionsCorrect}/${item.questionsTotal})`
                        : null}{" "}
                      correct
                    </p>
                  </div>
                ))}
                {viewModel.counts.skip > viewModel.masteredPreview.length && (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    And {viewModel.counts.skip - viewModel.masteredPreview.length} more sections.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Misconceptions ── */}
        {allMisconceptions.length > 0 && (
          <div className="card space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Misconceptions detected ({allMisconceptions.length})
              </h2>
            </div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              These misconceptions were inferred from your incorrect answers. Your learning path will prioritize fixing them.
            </p>
            <div className="space-y-2">
              {displayedMisconceptions.map((m, i) => (
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
              {allMisconceptions.length > displayedMisconceptions.length && (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  And {allMisconceptions.length - displayedMisconceptions.length} more misconceptions will be addressed in the path.
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── No misconceptions ── */}
        {allMisconceptions.length === 0 && overall >= 60 && (
          <div className="card flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              No misconceptions were detected. Your understanding looks solid.
            </p>
          </div>
        )}

        {/* ── CTA ── */}
        <div className="card flex flex-col items-center gap-4 text-center">
          <Trophy className="h-8 w-8 text-primary-600" />
          <div>
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
              Assessment complete
            </p>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              AI has recorded your level and is ready to build your personalized learning path.
            </p>
          </div>
          <Button
            onClick={goToNextStep}
            loading={navigating}
            size="lg"
          >
            {navigating ? "Redirecting..." : "Confirm and start learning"}
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
