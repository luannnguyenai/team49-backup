"use client";
// app/assessment/page.tsx
// Full-screen assessment flow:
//   load → start session → question-by-question → submit → /assessment/results

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Brain, ChevronRight, Clock, SkipForward } from "lucide-react";

import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import MarkdownRenderer from "@/components/assessment/MarkdownRenderer";
import { assessmentApi, contentApi } from "@/lib/api";
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
  remember:   { label: "Nhớ",     color: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300" },
  understand: { label: "Hiểu",    color: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300" },
  apply:      { label: "Áp dụng", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" },
  analyze:    { label: "Phân tích",color: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300" },
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

export default function AssessmentPage() {
  const router = useRouter();

  // ── Core state ─────────────────────────────────────────────────────────────
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuestionForAssessment[]>([]);
  const [topicNames, setTopicNames] = useState<Record<string, string>>({});
  const [currentIdx, setCurrentIdx] = useState(0);

  // questionId → chosen option  (undefined = not yet answered, null = skipped)
  const [answers, setAnswers] = useState<Record<string, SelectedAnswer | null>>({});
  // questionId → response time in ms (recorded on first selection)
  const responseTimes = useRef<Record<string, number>>({});
  // per-question start timestamp
  const questionStart = useRef<number>(Date.now());

  // Transition animation key — incremented on each question change
  const [animKey, setAnimKey] = useState(0);

  const elapsed = useElapsedTimer(phase === "active");

  // ── Load session on mount ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        // Resolve topic IDs from module IDs stored by onboarding page
        const moduleIdsRaw = sessionStorage.getItem("al_pending_module_ids");
        let topicIds: string[] = [];
        const nameMap: Record<string, string> = {};

        if (moduleIdsRaw) {
          const moduleIds = JSON.parse(moduleIdsRaw) as string[];
          const modules = await Promise.all(
            moduleIds.map((id) => contentApi.moduleDetail(id))
          );
          modules.forEach((m) =>
            m.topics.forEach((t) => {
              topicIds.push(t.id);
              nameMap[t.id] = t.title;
            })
          );
        }

        // Fallback: use ALL modules if nothing in sessionStorage
        if (topicIds.length === 0) {
          const allModules = await contentApi.modules();
          const details = await Promise.all(
            allModules.map((m) => contentApi.moduleDetail(m.id))
          );
          details.forEach((m) =>
            m.topics.forEach((t) => {
              topicIds.push(t.id);
              nameMap[t.id] = t.title;
            })
          );
        }

        const resp = await assessmentApi.start(topicIds);
        if (cancelled) return;

        setTopicNames(nameMap);
        setSessionId(resp.session_id);
        setQuestions(resp.questions);
        questionStart.current = Date.now();
        setPhase("active");
      } catch (e: unknown) {
        if (!cancelled) {
          const detail = (e as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail;
          setErrorMsg(
            typeof detail === "string"
              ? detail
              : "Không thể bắt đầu assessment. Vui lòng thử lại."
          );
          setPhase("error");
        }
      }
    }

    bootstrap();
    return () => { cancelled = true; };
  }, []);

  // ── Current question ───────────────────────────────────────────────────────
  const question = questions[currentIdx] ?? null;
  const selectedOption = question ? (answers[question.id] ?? undefined) : undefined;
  const isAnswered = selectedOption != null; // true if picked an option
  const isLastQuestion = currentIdx === questions.length - 1;

  // ── Select an option ───────────────────────────────────────────────────────
  const selectOption = useCallback(
    (opt: SelectedAnswer) => {
      if (!question) return;
      // Record response time only on first selection
      if (answers[question.id] === undefined) {
        responseTimes.current[question.id] = Date.now() - questionStart.current;
      }
      setAnswers((prev) => ({ ...prev, [question.id]: opt }));
    },
    [question, answers]
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
    if (!question) return;
    // Mark as explicitly skipped (null) so it's excluded from submission
    setAnswers((prev) => ({ ...prev, [question.id]: null }));
    if (isLastQuestion) {
      submitAssessment();
    } else {
      setAnimKey((k) => k + 1);
      setCurrentIdx((i) => i + 1);
      questionStart.current = Date.now();
    }
  }, [question, isLastQuestion, currentIdx]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Submit all answered questions ─────────────────────────────────────────
  async function submitAssessment() {
    if (!sessionId) return;
    setPhase("submitting");

    const answerList: AnswerInput[] = questions
      .filter((q) => answers[q.id] != null && answers[q.id] !== null)
      .map((q) => ({
        question_id: q.id,
        selected_answer: answers[q.id] as SelectedAnswer,
        response_time_ms: responseTimes.current[q.id] ?? null,
      }));

    if (answerList.length === 0) {
      setErrorMsg("Bạn chưa trả lời câu nào. Vui lòng trả lời ít nhất 1 câu.");
      setPhase("active");
      return;
    }

    try {
      await assessmentApi.submit(sessionId, answerList);
      sessionStorage.removeItem("al_pending_module_ids");
      router.push(`/assessment/results?session_id=${sessionId}`);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setErrorMsg(
        typeof detail === "string" ? detail : "Nộp bài thất bại. Vui lòng thử lại."
      );
      setPhase("active");
    }
  }

  // ── Keyboard navigation ────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "active") return;

    function handleKey(e: KeyboardEvent) {
      // Ignore when typing in inputs
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
      <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: "var(--bg-page)" }}>
        <div className="flex flex-col items-center gap-4">
          <LoadingSpinner size="lg" />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Đang chuẩn bị câu hỏi…
          </p>
        </div>
      </div>
    );
  }

  if (phase === "error" && !question) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4" style={{ backgroundColor: "var(--bg-page)" }}>
        <div className="card max-w-md w-full text-center space-y-4">
          <p className="text-4xl">😕</p>
          <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
            {errorMsg ?? "Đã xảy ra lỗi"}
          </p>
          <Button onClick={() => router.push("/dashboard")} variant="secondary">
            Về Dashboard
          </Button>
        </div>
      </div>
    );
  }

  if (!question) return null;

  const bloom = BLOOM_BADGE[question.bloom_level];
  const topicName = topicNames[question.topic_id] ?? "Assessment";
  const progress = Math.round(((currentIdx + 1) / questions.length) * 100);

  // ── Main assessment UI ────────────────────────────────────────────────────

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      {/* ── Top bar ── */}
      <header
        className="sticky top-0 z-10 border-b px-4 py-3 backdrop-blur-sm"
        style={{
          backgroundColor: "color-mix(in srgb, var(--bg-card) 95%, transparent)",
          borderColor: "var(--border)",
        }}
      >
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          {/* Logo */}
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-600">
            <Brain className="h-4 w-4 text-white" />
          </div>

          {/* Progress info */}
          <div className="flex-1 min-w-0">
            <div className="mb-1.5 flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
              <span className="truncate font-medium" style={{ color: "var(--text-secondary)" }}>
                {topicName}
              </span>
              <span className="shrink-0 ml-2">
                Câu {currentIdx + 1} / {questions.length}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className="h-full rounded-full bg-primary-600 transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Timer */}
          <div
            className="flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-mono font-medium"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
          >
            <Clock className="h-3.5 w-3.5" />
            {elapsed}
          </div>
        </div>
      </header>

      {/* ── Question area ── */}
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-6">

        {/* Error banner */}
        {errorMsg && phase === "active" && (
          <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400">
            {errorMsg}
          </div>
        )}

        {/* Question card */}
        <div key={animKey} className="animate-fade-in space-y-5">
          <div className="card">
            {/* Meta row */}
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
                <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
                  ~{question.time_expected_seconds}s
                </span>
              )}
            </div>

            {/* Stem text with markdown */}
            <MarkdownRenderer
              text={question.stem_text}
              className="text-base leading-relaxed"
            />
          </div>

          {/* Options */}
          <div className="space-y-2.5" role="radiogroup" aria-label="Lựa chọn">
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
                      ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                      : "hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-sm"
                  )}
                  style={{
                    borderColor: isSelected ? undefined : "var(--border)",
                    backgroundColor: isSelected ? undefined : "var(--bg-card)",
                  }}
                >
                  {/* Option letter */}
                  <span
                    className={cn(
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-sm font-bold",
                      "transition-all duration-150",
                      isSelected
                        ? "bg-primary-600 text-white"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                    )}
                  >
                    {opt}
                  </span>
                  {/* Option text */}
                  <span
                    className={cn(
                      "mt-0.5 text-sm leading-relaxed",
                      isSelected ? "font-medium text-primary-700 dark:text-primary-200" : ""
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

        {/* ── Navigation ── */}
        <div className="flex items-center justify-between gap-3 pb-6">
          {/* Skip */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={skip}
            leftIcon={<SkipForward className="h-3.5 w-3.5" />}
          >
            Bỏ qua
          </Button>

          {/* Keyboard hint */}
          <p className="hidden text-xs sm:block" style={{ color: "var(--text-muted)" }}>
            Nhấn{" "}
            <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "var(--border)" }}>
              A
            </kbd>
            {" – "}
            <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "var(--border)" }}>
              D
            </kbd>{" "}
            để chọn ·{" "}
            <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "var(--border)" }}>
              Enter
            </kbd>{" "}
            để tiếp
          </p>

          {/* Next / Submit */}
          <Button
            type="button"
            onClick={advance}
            disabled={!isAnswered}
            loading={phase === "submitting"}
            rightIcon={
              phase !== "submitting" ? <ChevronRight className="h-4 w-4" /> : undefined
            }
          >
            {isLastQuestion ? "Nộp bài" : "Câu tiếp"}
          </Button>
        </div>
      </main>
    </div>
  );
}
