"use client";

// app/quiz/[topicId]/page.tsx
// Full-screen quiz: 10 MCQ one-at-a-time, real-time feedback after each answer,
// live correct/incorrect progress bar, running timer.

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react";
import { getOptionStyle } from "@/lib/ui/feedbackStyles";
import { quizApi } from "@/lib/api";
import type {
  QuestionForQuiz,
  QuizAnswerResponse,
  SelectedAnswer,
} from "@/types";
import MarkdownRenderer from "@/components/assessment/MarkdownRenderer";

// ---------------------------------------------------------------------------
// Constants + helpers
// ---------------------------------------------------------------------------

const BLOOM_LABELS: Record<string, string> = {
  remember: "Nhớ",
  understand: "Hiểu",
  apply: "Áp dụng",
  analyze: "Phân tích",
};

const BLOOM_COLORS: Record<string, string> = {
  remember: "bg-red-100 text-red-700",
  understand: "bg-orange-100 text-orange-700",
  apply: "bg-blue-100 text-blue-700",
  analyze: "bg-purple-100 text-purple-700",
};

const DIFF_LABELS: Record<string, string> = {
  easy: "Dễ",
  medium: "Trung bình",
  hard: "Khó",
};

const DIFF_COLORS: Record<string, string> = {
  easy: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  hard: "bg-red-100 text-red-700",
};

const OPTION_KEYS: SelectedAnswer[] = ["A", "B", "C", "D"];

function fmtTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Phase types
// ---------------------------------------------------------------------------

type Phase = "loading" | "quiz" | "feedback" | "completing" | "error";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function QuizPage() {
  const { topicId } = useParams<{ topicId: string }>();
  const router = useRouter();

  // Session
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [questions, setQuestions] = useState<QuestionForQuiz[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);

  // Per-question state
  const [selected, setSelected] = useState<SelectedAnswer | null>(null);
  const [feedback, setFeedback] = useState<QuizAnswerResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Timing
  const [elapsed, setElapsed] = useState(0); // total seconds
  const questionStartRef = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---------------------------------------------------------------------------
  // Start quiz on mount
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!topicId) return;

    quizApi
      .start(topicId)
      .then((data) => {
        setSessionId(data.session_id);
        setQuestions(data.questions);
        setPhase("quiz");
        questionStartRef.current = Date.now();
        // Start timer
        timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail;
        setErrorMsg(
          typeof detail === "string"
            ? detail
            : "Không thể bắt đầu quiz. Vui lòng thử lại."
        );
        setPhase("error");
      });

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [topicId]);

  // ---------------------------------------------------------------------------
  // Keyboard: A/B/C/D to select, Enter to confirm when selected
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (phase !== "quiz") return;

    const handler = (e: KeyboardEvent) => {
      const key = e.key.toUpperCase();
      if (OPTION_KEYS.includes(key as SelectedAnswer)) {
        setSelected(key as SelectedAnswer);
      }
      if (e.key === "Enter" && selected !== null && !submitting) {
        submitAnswer(selected);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  // ---------------------------------------------------------------------------
  // Submit answer
  // ---------------------------------------------------------------------------

  const submitAnswer = useCallback(
    async (answer: SelectedAnswer) => {
      if (submitting || phase !== "quiz") return;
      setSubmitting(true);

      const responseTimeMs = Math.round(Date.now() - questionStartRef.current);
      const q = questions[currentIdx];

      try {
        const fb = await quizApi.answer(sessionId, {
          question_id: q.id,
          selected_answer: answer,
          response_time_ms: responseTimeMs,
        });
        setFeedback(fb);
        setPhase("feedback");
      } catch {
        // On error just continue silently
      } finally {
        setSubmitting(false);
      }
    },
    [submitting, phase, questions, currentIdx, sessionId]
  );

  // ---------------------------------------------------------------------------
  // Advance to next question or complete
  // ---------------------------------------------------------------------------

  const advance = useCallback(async () => {
    const isLast = currentIdx >= questions.length - 1;

    if (isLast) {
      setPhase("completing");
      if (timerRef.current) clearInterval(timerRef.current);

      try {
        const result = await quizApi.complete(sessionId);
        sessionStorage.setItem(`quiz_result_${topicId}`, JSON.stringify(result));
        router.push(`/quiz/${topicId}/results`);
      } catch {
        setErrorMsg("Không thể hoàn thành quiz. Vui lòng thử lại.");
        setPhase("error");
      }
    } else {
      setCurrentIdx((i) => i + 1);
      setSelected(null);
      setFeedback(null);
      setPhase("quiz");
      questionStartRef.current = Date.now();
    }
  }, [currentIdx, questions.length, sessionId, topicId, router]);

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const question = questions[currentIdx];
  const correctCount = feedback?.questions_correct ?? 0;
  const answeredCount = feedback?.questions_answered ?? currentIdx;
  const progressPct = Math.round(((currentIdx + (phase === "feedback" ? 1 : 0)) / questions.length) * 100);

  // ---------------------------------------------------------------------------
  // Loading / Error
  // ---------------------------------------------------------------------------

  if (phase === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Đang chuẩn bị quiz...
          </p>
        </div>
      </div>
    );
  }

  if (phase === "completing") {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Đang tính kết quả...
          </p>
        </div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center p-6" style={{ background: "var(--bg-primary)" }}>
        <div className="max-w-sm text-center">
          <AlertCircle className="mx-auto mb-4 text-red-500" size={40} />
          <p className="font-semibold" style={{ color: "var(--text-primary)" }}>Đã xảy ra lỗi</p>
          <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>{errorMsg}</p>
          <button
            onClick={() => router.back()}
            className="btn-secondary mt-6"
          >
            Quay lại
          </button>
        </div>
      </div>
    );
  }

  if (!question) return null;

  // ---------------------------------------------------------------------------
  // Quiz + Feedback rendering
  // ---------------------------------------------------------------------------

  const optionTexts: Record<SelectedAnswer, string> = {
    A: question.option_a,
    B: question.option_b,
    C: question.option_c,
    D: question.option_d,
  };

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--bg-primary)" }}
    >
      {/* ------------------------------------------------------------------- */}
      {/* Top bar                                                              */}
      {/* ------------------------------------------------------------------- */}
      <header
        className="sticky top-0 z-20 border-b px-4 py-3 md:px-6"
        style={{
          background: "var(--bg-elevated)",
          borderColor: "var(--border)",
        }}
      >
        <div className="mx-auto flex max-w-2xl items-center gap-4">
          {/* Question counter */}
          <span className="shrink-0 text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
            {currentIdx + 1} / {questions.length}
          </span>

          {/* Progress bar */}
          <div className="flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700 h-2">
            <div
              className="h-full rounded-full bg-primary-500 transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Timer */}
          <span className="flex shrink-0 items-center gap-1 text-sm tabular-nums" style={{ color: "var(--text-muted)" }}>
            <Clock size={14} />
            {fmtTime(elapsed)}
          </span>
        </div>

        {/* Correct / Wrong tally bar */}
        {phase === "feedback" && answeredCount > 0 && (
          <div className="mx-auto mt-2 flex max-w-2xl items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-emerald-600">
              <CheckCircle2 size={13} />
              {correctCount} đúng
            </span>
            <div className="flex-1 overflow-hidden rounded-full bg-slate-200 h-1.5">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${(correctCount / answeredCount) * 100}%` }}
              />
            </div>
            <span className="flex items-center gap-1 text-red-500">
              <XCircle size={13} />
              {answeredCount - correctCount} sai
            </span>
          </div>
        )}
      </header>

      {/* ------------------------------------------------------------------- */}
      {/* Question card                                                        */}
      {/* ------------------------------------------------------------------- */}
      <main className="flex flex-1 flex-col items-center justify-start px-4 py-8 md:px-6">
        <div className="w-full max-w-2xl space-y-5">
          {/* Badges */}
          <div className="flex items-center gap-2 text-xs">
            <span className={`rounded-full px-2.5 py-0.5 font-medium ${BLOOM_COLORS[question.bloom_level]}`}>
              {BLOOM_LABELS[question.bloom_level] ?? question.bloom_level}
            </span>
            <span className={`rounded-full px-2.5 py-0.5 font-medium ${DIFF_COLORS[question.difficulty_bucket]}`}>
              {DIFF_LABELS[question.difficulty_bucket] ?? question.difficulty_bucket}
            </span>
          </div>

          {/* Stem */}
          <div
            className="rounded-2xl border p-5 text-base font-medium leading-relaxed"
            style={{
              borderColor: "var(--border)",
              background: "var(--bg-elevated)",
              color: "var(--text-primary)",
            }}
          >
            <MarkdownRenderer text={question.stem_text} />
          </div>

          {/* Options */}
          <div className="space-y-3">
            {OPTION_KEYS.map((key) => {
              const isSelected = selected === key;
              const isFeedback = phase === "feedback";
              const isCorrect = feedback?.correct_answer === key;
              const isWrong = isFeedback && isSelected && !feedback?.is_correct;

              const optStyle = getOptionStyle({ isFeedback, isCorrect, isWrong, isSelected });
              const ringClass = isFeedback ? "" : isSelected ? "ring-2 ring-primary-300" : "";

              return (
                <button
                  key={key}
                  disabled={isFeedback || submitting}
                  onClick={() => {
                    setSelected(key);
                    submitAnswer(key);
                  }}
                  className={[
                    "w-full flex items-start gap-3 rounded-xl border p-4 text-left transition-all duration-150",
                    !isFeedback && !submitting ? "hover:border-primary-400 cursor-pointer" : "cursor-default",
                    ringClass,
                  ].join(" ")}
                  style={{ borderColor: optStyle.borderColor, background: optStyle.background }}
                >
                  {/* Key badge */}
                  <span
                    className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                    style={{ background: optStyle.badgeBg, color: optStyle.badgeColor }}
                  >
                    {key}
                  </span>

                  <span className="flex-1 text-sm" style={{ color: optStyle.textColor }}>
                    <MarkdownRenderer text={optionTexts[key]} />
                  </span>

                  {/* Result icon */}
                  {isFeedback && isCorrect && (
                    <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-500" size={18} />
                  )}
                  {isFeedback && isWrong && (
                    <XCircle className="mt-0.5 shrink-0 text-red-500" size={18} />
                  )}
                </button>
              );
            })}
          </div>

          {/* Feedback panel */}
          {phase === "feedback" && feedback && (
            <div
              className={[
                "rounded-2xl border p-4 text-sm",
                feedback.is_correct
                  ? "border-emerald-300 bg-emerald-50"
                  : "border-red-300 bg-red-50",
              ].join(" ")}
            >
              <div className="flex items-center gap-2 font-semibold">
                {feedback.is_correct ? (
                  <>
                    <CheckCircle2 className="text-emerald-600" size={18} />
                    <span className="text-emerald-700">Chính xác!</span>
                  </>
                ) : (
                  <>
                    <XCircle className="text-red-600" size={18} />
                    <span className="text-red-700">
                      Chưa đúng — Đáp án đúng: <strong>{feedback.correct_answer}</strong>
                    </span>
                  </>
                )}
              </div>

              {feedback.explanation_text && (
                <div
                  className="mt-2 pl-6 leading-relaxed"
                  style={{ color: feedback.is_correct ? "#15803d" : "#b91c1c" }}
                >
                  <MarkdownRenderer text={feedback.explanation_text} />
                </div>
              )}
            </div>
          )}

          {/* Continue button */}
          {phase === "feedback" && (
            <button
              onClick={advance}
              className="btn-primary flex w-full items-center justify-center gap-2 py-3"
            >
              {currentIdx >= questions.length - 1 ? (
                "Xem kết quả"
              ) : (
                <>
                  Câu tiếp theo
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          )}

          {/* Keyboard hint */}
          {phase === "quiz" && (
            <p className="text-center text-xs" style={{ color: "var(--text-muted)" }}>
              Nhấn phím <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs dark:bg-slate-800">A</kbd>–
              <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs dark:bg-slate-800">D</kbd> để chọn
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
