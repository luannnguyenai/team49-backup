"use client";
// app/assessment/page.tsx
// Full-screen assessment flow:
//   load → start session → question-by-question → submit → /assessment/results

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Bookmark,
  BookmarkCheck,
  Brain,
  ChevronRight,
  Clock,
  SkipForward,
} from "lucide-react";

import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import MarkdownRenderer from "@/components/assessment/MarkdownRenderer";
import { assessmentApi, canonicalAssessmentApi } from "@/lib/api";
import {
  buildAssessmentAnswerInput,
  clearPendingAssessmentContext,
  getAssessmentQuestionKey,
  readPendingCanonicalAssessment,
  readStartedCanonicalAssessment,
} from "@/lib/canonical-assessment-session";
import { cn } from "@/lib/utils";
import type {
  AnswerInput,
  QuestionForAssessment,
  SelectedAnswer,
} from "@/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type Phase = "loading" | "active" | "submitting" | "error";

const OPTIONS: SelectedAnswer[] = ["A", "B", "C", "D"];

const BLOOM_BADGE: Record<string, { label: string; color: string }> = {
  remember: { label: "Remember", color: "bg-bloom-remember-soft text-bloom-remember" },
  understand: { label: "Understand", color: "bg-bloom-understand-soft text-bloom-understand" },
  apply: { label: "Apply", color: "bg-bloom-apply-soft text-bloom-apply" },
  analyze: { label: "Analyze", color: "bg-bloom-analyze-soft text-bloom-analyze" },
};

// ---------------------------------------------------------------------------
// Timer hook — counts up every second while `active` is true
// ---------------------------------------------------------------------------

function useElapsedTimer(active: boolean) {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [active]);
  const mm = String(Math.floor(secs / 60)).padStart(2, "0");
  const ss = String(secs % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function AssessmentPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // ── Core state ─────────────────────────────────────────────────────────────
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuestionForAssessment[]>([]);
  const [learningUnitNames, setLearningUnitNames] = useState<Record<string, string>>({});
  const [currentIdx, setCurrentIdx] = useState(0);

  // questionId → chosen option  (undefined = not yet answered, null = skipped)
  const [answers, setAnswers] = useState<Record<string, SelectedAnswer | null>>({});
  // questionId → response time in ms (recorded on first selection)
  const responseTimes = useRef<Record<string, number>>({});
  // per-question start timestamp
  const questionStart = useRef<number>(Date.now());

  // Flagged questions for review
  const [flagged, setFlagged] = useState<Set<string>>(new Set());

  // Transition animation key — incremented on each question change
  const [animKey, setAnimKey] = useState(0);

  const elapsed = useElapsedTimer(phase === "active");

  // ── Load session on mount ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const startedAssessment = readStartedCanonicalAssessment();
        if (startedAssessment) {
          if (!cancelled) {
            setLearningUnitNames(startedAssessment.unitNameMap);
            setSessionId(startedAssessment.sessionId);
            setQuestions(startedAssessment.questions);
            questionStart.current = Date.now();
            setPhase("active");
          }
          return;
        }

        const { canonicalUnitIds, unitNameMap, assessmentDepth } = readPendingCanonicalAssessment();
        if (canonicalUnitIds.length === 0) {
          if (!cancelled) {
            setErrorMsg("No learning units were found for this assessment. Please return to onboarding.");
            setPhase("error");
          }
          return;
        }

        const resp = await canonicalAssessmentApi.start({
          canonical_unit_ids: canonicalUnitIds,
          assessment_depth: assessmentDepth,
        });
        if (cancelled) return;

        setLearningUnitNames(unitNameMap);
        setSessionId(resp.session_id);
        setQuestions(resp.questions);
        questionStart.current = Date.now();
        setPhase("active");
      } catch (e: unknown) {
        if (!cancelled) {
          const data = (e as { response?: { data?: unknown } })?.response?.data;
          const detail = (data as { detail?: unknown })?.detail;
          const msg =
            typeof detail === "string"
              ? detail
              : Array.isArray(detail)
              ? (detail as { msg?: string }[])[0]?.msg ?? "Invalid data."
              : "Unable to start the assessment. Please try again.";
          setErrorMsg(msg);
          setPhase("error");
        }
      }
    }

    bootstrap();
    return () => { cancelled = true; };
  }, []);

  // ── Current question ───────────────────────────────────────────────────────
  const question = questions[currentIdx] ?? null;
  const questionKey = question ? getAssessmentQuestionKey(question) : null;
  const selectedOption = questionKey ? (answers[questionKey] ?? undefined) : undefined;
  const isAnswered = selectedOption != null;
  const isLastQuestion = currentIdx === questions.length - 1;

  // ── Select an option ───────────────────────────────────────────────────────
  const selectOption = useCallback(
    (opt: SelectedAnswer) => {
      if (!question || !questionKey) return;
      if (answers[questionKey] === undefined) {
        responseTimes.current[questionKey] = Date.now() - questionStart.current;
      }
      setAnswers((prev) => ({ ...prev, [questionKey]: opt }));
    },
    [question, questionKey, answers]
  );

  // ── Navigate to next question ──────────────────────────────────────────────
  const advance = useCallback(() => {
    if (isLastQuestion) {
      submitAssessment();
    } else {
      setAnimKey((k) => k + 1);
      setCurrentIdx((i) => i + 1);
      questionStart.current = Date.now();
    }
  }, [isLastQuestion, currentIdx]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Skip current question ──────────────────────────────────────────────────
  const skip = useCallback(() => {
    if (!question || !questionKey) return;
    setAnswers((prev) => ({ ...prev, [questionKey]: null }));
    if (isLastQuestion) {
      submitAssessment();
    } else {
      setAnimKey((k) => k + 1);
      setCurrentIdx((i) => i + 1);
      questionStart.current = Date.now();
    }
  }, [question, questionKey, isLastQuestion, currentIdx]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Jump to any question ───────────────────────────────────────────────────
  const jumpTo = useCallback((idx: number) => {
    setAnimKey((k) => k + 1);
    setCurrentIdx(idx);
    questionStart.current = Date.now();
  }, []);

  // ── Toggle bookmark / flag for review ─────────────────────────────────────
  const toggleFlag = useCallback((id: string) => {
    setFlagged((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // ── Submit all answered questions ─────────────────────────────────────────
  async function submitAssessment() {
    if (!sessionId) return;
    setPhase("submitting");

    const answerList: AnswerInput[] = questions
      .map((q) => ({
        question: q,
        key: getAssessmentQuestionKey(q),
      }))
      .filter(({ key }) => answers[key] != null && answers[key] !== null)
      .map(({ question: q, key }) =>
        buildAssessmentAnswerInput(
          q,
          answers[key] as SelectedAnswer,
          responseTimes.current[key] ?? null,
        ),
      );

    if (answerList.length === 0) {
      setErrorMsg("You have not answered any questions yet. Please answer at least one.");
      setPhase("active");
      return;
    }

    try {
      await assessmentApi.submit(sessionId, answerList);
      const next = searchParams.get("next");
      clearPendingAssessmentContext();
      const resultsParams = new URLSearchParams({ session_id: sessionId });
      if (next) {
        resultsParams.set("next", next);
      }
      router.push(`/assessment/results?${resultsParams.toString()}`);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setErrorMsg(
        typeof detail === "string" ? detail : "Submission failed. Please try again."
      );
      setPhase("active");
    }
  }

  // ── Keyboard navigation ────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "active") return;

    function handleKey(e: KeyboardEvent) {
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) return;

      const map: Record<string, SelectedAnswer> = { a: "A", b: "B", c: "C", d: "D" };
      const opt = map[e.key.toLowerCase()];
      if (opt) {
        selectOption(opt);
        return;
      }
      if (e.key === "Enter" && isAnswered) {
        advance();
      }
    }

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [phase, selectOption, advance, isAnswered]);

  // ── Render helpers ────────────────────────────────────────────────────────

  const getOptionText = (q: QuestionForAssessment, opt: SelectedAnswer) => {
    const map: Record<SelectedAnswer, string> = {
      A: q.option_a,
      B: q.option_b,
      C: q.option_c,
      D: q.option_d,
    };
    return map[opt];
  };

  // ── Skeletons ─────────────────────────────────────────────────────────────

  if (phase === "loading") {
    return (
      <div className="min-h-screen px-4 py-10" style={{ backgroundColor: "var(--bg-page)" }}>
        <div className="mx-auto flex w-full max-w-2xl flex-col items-center justify-center gap-4 rounded-3xl border px-6 py-16 text-center" style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}>
          <LoadingSpinner size="lg" />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Preparing your questions...
          </p>
        </div>
      </div>
    );
  }

  if (phase === "error" && !question) {
    return (
      <div className="min-h-screen px-4 py-10" style={{ backgroundColor: "var(--bg-page)" }}>
        <div className="mx-auto w-full max-w-2xl">
          <div className="card mx-auto max-w-md space-y-4 text-center">
            <p className="text-4xl">😕</p>
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
              {errorMsg ?? "Something went wrong"}
            </p>
            <Button onClick={() => router.push("/dashboard")} variant="secondary">
              Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!question) return null;

  const bloom = question.bloom_level ? BLOOM_BADGE[question.bloom_level] : undefined;
  const learningUnitName = question.canonical_unit_id
    ? learningUnitNames[question.canonical_unit_id] ?? "Assessment"
    : question.topic_id
    ? learningUnitNames[question.topic_id] ?? "Assessment"
    : "Assessment";
  const progress = Math.round(((currentIdx + 1) / questions.length) * 100);
  const isFlagged = questionKey ? flagged.has(questionKey) : false;

  // ── Main assessment UI ────────────────────────────────────────────────────

  return (
    <div className="min-h-screen px-4 py-10" style={{ backgroundColor: "var(--bg-page)" }}>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header
          className="rounded-3xl border px-5 py-5 shadow-sm backdrop-blur-sm"
          style={{
            backgroundColor: "color-mix(in srgb, var(--bg-card) 95%, transparent)",
            borderColor: "var(--border)",
          }}
        >
          <div className="flex items-start gap-3 sm:items-center">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/20">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="mb-1.5 flex items-center justify-between gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
                <span className="truncate font-medium" style={{ color: "var(--text-secondary)" }}>
                  {learningUnitName}
                </span>
                <span className="shrink-0">
                  Question {currentIdx + 1} / {questions.length}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-primary-600 transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
            <div
              className="flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-mono font-medium"
              style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
            >
              <Clock className="h-3.5 w-3.5" />
              {elapsed}
            </div>
          </div>
        </header>

        <div className="flex flex-1 flex-col gap-6 lg:flex-row lg:items-start">
          <aside className="card lg:sticky lg:top-6 lg:w-72 lg:shrink-0">
            <div className="mb-4 flex items-center gap-2">
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Questions
              </span>
              <span
                className="ml-auto text-xs font-medium tabular-nums"
                style={{ color: "var(--text-muted)" }}
              >
                {currentIdx + 1}/{questions.length}
              </span>
            </div>

            <div className="grid grid-cols-4 gap-1.5">
              {questions.map((q, idx) => {
                const qKey = getAssessmentQuestionKey(q);
                const isAns = answers[qKey] != null;
                const isSkipped = answers[qKey] === null;
                const isCur = idx === currentIdx;
                const isQFlagged = flagged.has(qKey);

                return (
                  <button
                    key={qKey}
                    onClick={() => jumpTo(idx)}
                    title={`Question ${idx + 1}${isQFlagged ? " · Marked for review" : ""}`}
                    className={cn(
                      "relative flex h-10 w-full items-center justify-center rounded-lg text-xs font-bold transition-all duration-150",
                      isCur
                        ? "scale-105 bg-primary-600 text-white shadow-sm"
                        : isSkipped
                        ? "bg-state-warning-bg text-state-warning-fg hover:brightness-95"
                        : isAns
                        ? "bg-state-success-bg text-state-success-fg hover:brightness-95"
                        : "hover:bg-slate-100"
                    )}
                    style={
                      !isCur && !isAns && !isSkipped
                        ? { color: "var(--text-secondary)", backgroundColor: "var(--bg-page)" }
                        : undefined
                    }
                  >
                    {idx + 1}
                    {isQFlagged && (
                      <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-state-warning-fg ring-1 ring-white" />
                    )}
                  </button>
                );
              })}
            </div>

            <div
              className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 shrink-0 rounded bg-primary-600" />
                <span>Current</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 shrink-0 rounded border border-state-success-border bg-state-success-bg" />
                <span>Answered</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 shrink-0 rounded border border-state-warning-border bg-state-warning-bg" />
                <span>Skipped</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="ml-0.5 h-2 w-2 shrink-0 rounded-full bg-state-warning-fg" />
                <span>Marked for review</span>
              </div>
            </div>
          </aside>

          <main className="min-w-0 flex flex-1 flex-col gap-6">
          {errorMsg && phase === "active" && (
            <div className="state-error rounded-lg border px-4 py-3 text-sm">
              {errorMsg}
            </div>
          )}

          <div key={animKey} className="animate-fade-in space-y-5">
            <div className="card">
              <div className="mb-4 flex flex-wrap items-center gap-2">
                {bloom && (
                  <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", bloom.color)}>
                    {bloom.label}
                  </span>
                )}
                <span
                  className="rounded-full px-2.5 py-1 text-xs font-medium capitalize"
                  style={{
                    backgroundColor: "var(--bg-page)",
                    color: "var(--text-muted)",
                  }}
                >
                  {question.difficulty_bucket}
                </span>
                {question.time_expected_seconds && (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    ~{question.time_expected_seconds}s
                  </span>
                )}

                <button
                  onClick={() => questionKey && toggleFlag(questionKey)}
                  title={isFlagged ? "Remove review mark" : "Mark for review"}
                  className={cn(
                    "ml-auto flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all duration-150",
                    isFlagged
                      ? "bg-state-warning-bg text-state-warning-fg"
                      : "hover:bg-slate-100"
                  )}
                  style={!isFlagged ? { color: "var(--text-muted)" } : undefined}
                >
                  {isFlagged ? (
                    <BookmarkCheck className="h-3.5 w-3.5" />
                  ) : (
                    <Bookmark className="h-3.5 w-3.5" />
                  )}
                  <span className="hidden sm:inline">
                    {isFlagged ? "Marked" : "Mark"}
                  </span>
                </button>
              </div>

              <MarkdownRenderer
                text={question.stem_text}
                className="text-base leading-relaxed"
              />
            </div>

            <div className="space-y-2.5" role="radiogroup" aria-label="Answer choices">
              {OPTIONS.map((opt) => {
                const isSelected = selectedOption === opt;
                return (
                  <button
                    key={opt}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => selectOption(opt)}
                    className={cn(
                      "flex w-full items-start gap-3 rounded-xl border-2 px-4 py-3.5 text-left",
                      "transition-all duration-150 active:scale-[0.99]",
                      isSelected
                        ? "border-primary-500 bg-primary-50"
                        : "hover:border-slate-300 hover:shadow-sm"
                    )}
                    style={{
                      borderColor: isSelected ? undefined : "var(--border)",
                      backgroundColor: isSelected ? undefined : "var(--bg-card)",
                    }}
                  >
                    <span
                      className={cn(
                        "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-sm font-bold",
                        "transition-all duration-150",
                        isSelected
                          ? "bg-primary-600 text-white"
                          : "bg-slate-100 text-slate-500"
                      )}
                    >
                      {opt}
                    </span>
                    <span
                      className={cn(
                        "mt-0.5 text-sm leading-relaxed",
                        isSelected ? "font-medium text-primary-700" : ""
                      )}
                      style={{ color: isSelected ? undefined : "var(--text-primary)" }}
                    >
                      {getOptionText(question, opt)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 pb-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={skip}
              leftIcon={<SkipForward className="h-3.5 w-3.5" />}
            >
              Skip
            </Button>

            <p className="hidden text-xs sm:block" style={{ color: "var(--text-muted)" }}>
              Press{" "}
              <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "var(--border)" }}>
                A
              </kbd>
              {" - "}
              <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "var(--border)" }}>
                D
              </kbd>{" "}
              to choose ·{" "}
              <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "var(--border)" }}>
                Enter
              </kbd>{" "}
              to continue
            </p>

            <Button
              type="button"
              onClick={advance}
              disabled={!isAnswered}
              loading={phase === "submitting"}
              rightIcon={
                phase !== "submitting" ? <ChevronRight className="h-4 w-4" /> : undefined
              }
            >
              {isLastQuestion ? "Submit assessment" : "Next question"}
            </Button>
          </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export default function AssessmentPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: "var(--bg-page)" }}>
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <AssessmentPageInner />
    </Suspense>
  );
}
