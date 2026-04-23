"use client";
// app/assessment/page.tsx
// Full-screen assessment flow:
//   load → start session → question-by-question → submit → /assessment/results

import { useCallback, useEffect, useRef, useState } from "react";
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
import { assessmentApi, canonicalAssessmentApi, legacyContentApi } from "@/lib/api";
import {
  ASSESSMENT_STORAGE_KEYS,
  buildAssessmentAnswerInput,
  clearPendingAssessmentContext,
  getAssessmentQuestionKey,
  readPendingCanonicalAssessment,
} from "@/lib/canonical-assessment-session";
import { cn } from "@/lib/utils";
import type {
  AnswerInput,
  ModuleDetail,
  QuestionForAssessment,
  SelectedAnswer,
} from "@/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type Phase = "loading" | "active" | "submitting" | "error";

const OPTIONS: SelectedAnswer[] = ["A", "B", "C", "D"];

const BLOOM_BADGE: Record<string, { label: string; color: string }> = {
  remember: { label: "Nhớ", color: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300" },
  understand: { label: "Hiểu", color: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300" },
  apply: { label: "Áp dụng", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" },
  analyze: { label: "Phân tích", color: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300" },
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
  const searchParams = useSearchParams();

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
        const { canonicalUnitIds, unitNameMap } = readPendingCanonicalAssessment();
        const topicIdsRaw = sessionStorage.getItem(ASSESSMENT_STORAGE_KEYS.topicIds);
        const topicNamesRaw = sessionStorage.getItem(ASSESSMENT_STORAGE_KEYS.topicNames);

        let topicIds: string[] = topicIdsRaw ? JSON.parse(topicIdsRaw) as string[] : [];
        let nameMap: Record<string, string> = topicNamesRaw
          ? JSON.parse(topicNamesRaw) as Record<string, string>
          : {};

        if (canonicalUnitIds.length === 0 && topicIds.length === 0) {
          const moduleIdsRaw = sessionStorage.getItem(ASSESSMENT_STORAGE_KEYS.moduleIds);
          if (moduleIdsRaw) {
            const moduleIds = JSON.parse(moduleIdsRaw) as string[];
            const mods: ModuleDetail[] = await Promise.all(
              moduleIds.map((id) => legacyContentApi.moduleDetail(id))
            );
            mods.forEach((m) =>
              m.topics.forEach((t) => {
                topicIds.push(t.id);
                nameMap[t.id] = t.name;
              })
            );
          }
        }

        if (canonicalUnitIds.length === 0 && topicIds.length === 0) {
          const allModules = await legacyContentApi.modules();
          const details: ModuleDetail[] = await Promise.all(
            allModules.map((m) => legacyContentApi.moduleDetail(m.id))
          );
          details.forEach((m) =>
            m.topics.forEach((t) => {
              topicIds.push(t.id);
              nameMap[t.id] = t.name;
            })
          );
        }

        const resp = canonicalUnitIds.length > 0
          ? await canonicalAssessmentApi.start({ canonical_unit_ids: canonicalUnitIds })
          : await assessmentApi.start(topicIds);
        if (cancelled) return;

        setTopicNames(canonicalUnitIds.length > 0 ? unitNameMap : nameMap);
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
              ? (detail as { msg?: string }[])[0]?.msg ?? "Dữ liệu không hợp lệ."
              : "Không thể bắt đầu assessment. Vui lòng thử lại.";
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
      setErrorMsg("Bạn chưa trả lời câu nào. Vui lòng trả lời ít nhất 1 câu.");
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
        typeof detail === "string" ? detail : "Nộp bài thất bại. Vui lòng thử lại."
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

  const bloom = question.bloom_level ? BLOOM_BADGE[question.bloom_level] : undefined;
  const topicName = question.canonical_unit_id
    ? topicNames[question.canonical_unit_id] ?? "Assessment"
    : question.topic_id
    ? topicNames[question.topic_id] ?? "Assessment"
    : "Assessment";
  const progress = Math.round(((currentIdx + 1) / questions.length) * 100);
  const isFlagged = questionKey ? flagged.has(questionKey) : false;

  // ── Main assessment UI ────────────────────────────────────────────────────

  return (
    <div className="flex min-h-screen" style={{ backgroundColor: "var(--bg-page)" }}>

      {/* ── Left sidebar: question navigator ── */}
      <aside
        className="hidden md:flex flex-col w-56 xl:w-64 shrink-0 sticky top-0 h-screen overflow-y-auto border-r"
        style={{
          backgroundColor: "var(--bg-card)",
          borderColor: "var(--border)",
        }}
      >
        {/* Sidebar header */}
        <div
          className="flex items-center gap-2 border-b px-4 py-3.5"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary-600">
            <Brain className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Câu hỏi
          </span>
          <span
            className="ml-auto text-xs font-medium tabular-nums"
            style={{ color: "var(--text-muted)" }}
          >
            {currentIdx + 1}/{questions.length}
          </span>
        </div>

        {/* Question grid */}
        <div className="flex-1 overflow-y-auto p-3">
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
                  title={`Câu ${idx + 1}${isQFlagged ? " · Đánh dấu review" : ""}`}
                  className={cn(
                    "relative flex h-9 w-full items-center justify-center rounded-lg text-xs font-bold transition-all duration-150",
                    isCur
                      ? "bg-primary-600 text-white shadow-sm scale-105"
                      : isSkipped
                      ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 hover:brightness-95"
                      : isAns
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 hover:brightness-95"
                      : "hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                  style={
                    !isCur && !isAns && !isSkipped
                      ? { color: "var(--text-secondary)", backgroundColor: "var(--bg-page)" }
                      : undefined
                  }
                >
                  {idx + 1}
                  {/* Flag dot */}
                  {isQFlagged && (
                    <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-yellow-400 ring-1 ring-white dark:ring-slate-900" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Legend */}
        <div
          className="border-t p-3 space-y-1.5 text-xs"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
        >
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded bg-primary-600 shrink-0" />
            <span>Đang làm</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded bg-emerald-100 border border-emerald-300 shrink-0" />
            <span>Đã trả lời</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded bg-amber-100 border border-amber-300 shrink-0" />
            <span>Đã bỏ qua</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-yellow-400 shrink-0 ml-0.5" />
            <span>Đánh dấu review</span>
          </div>
        </div>
      </aside>

      {/* ── Main content ── */}
      <div className="flex flex-1 flex-col min-w-0">

        {/* ── Top bar ── */}
        <header
          className="sticky top-0 z-10 border-b px-4 py-3 backdrop-blur-sm"
          style={{
            backgroundColor: "color-mix(in srgb, var(--bg-card) 95%, transparent)",
            borderColor: "var(--border)",
          }}
        >
          <div className="mx-auto flex max-w-2xl items-center gap-3">
            {/* Logo — hidden on md+ since sidebar has it */}
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-600 md:hidden">
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
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    ~{question.time_expected_seconds}s
                  </span>
                )}

                {/* Bookmark / flag button */}
                <button
                  onClick={() => questionKey && toggleFlag(questionKey)}
                  title={isFlagged ? "Bỏ đánh dấu review" : "Đánh dấu để review lại"}
                  className={cn(
                    "ml-auto flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all duration-150",
                    isFlagged
                      ? "bg-yellow-50 text-yellow-600 dark:bg-yellow-900/20 dark:text-yellow-400"
                      : "hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                  style={!isFlagged ? { color: "var(--text-muted)" } : undefined}
                >
                  {isFlagged ? (
                    <BookmarkCheck className="h-3.5 w-3.5" />
                  ) : (
                    <Bookmark className="h-3.5 w-3.5" />
                  )}
                  <span className="hidden sm:inline">
                    {isFlagged ? "Đã đánh dấu" : "Đánh dấu"}
                  </span>
                </button>
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
    </div>
  );
}
