"use client";

// app/module-test/[sectionId]/page.tsx
// Full-screen module test exam:
//   - All questions visible via left navigation panel (click to jump)
//   - One question shown at a time
//   - Topic section headers
//   - Flag button per question
//   - No answer reveal until final submit
//   - Confirm dialog before submit
//   - Count-up timer

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  BookOpen,
  Brain,
  ChevronLeft,
  ChevronRight,
  Clock,
  Flag,
  Menu,
  Send,
  X,
} from "lucide-react";
import { canonicalModuleTestApi, moduleTestApi } from "@/lib/api";
import { buildModuleTestRuntimeRef } from "@/lib/canonical-learning-runtime";
import type {
  ModuleTestAnswerInput,
  ModuleTestStartResponse,
  QuestionForModuleTest,
  SelectedAnswer,
  TopicQuestionsGroup,
} from "@/types";
import MarkdownRenderer from "@/components/assessment/MarkdownRenderer";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const OPTIONS: SelectedAnswer[] = ["A", "B", "C", "D"];

const BLOOM_BADGE: Record<string, { label: string; cls: string }> = {
  remember:   { label: "Nhớ",       cls: "bg-sky-100 text-sky-700" },
  understand: { label: "Hiểu",      cls: "bg-violet-100 text-violet-700" },
  apply:      { label: "Áp dụng",   cls: "bg-amber-100 text-amber-700" },
  analyze:    { label: "Phân tích", cls: "bg-rose-100 text-rose-700" },
};

const DIFF_BADGE: Record<string, { label: string; cls: string }> = {
  easy:   { label: "Dễ",        cls: "bg-emerald-100 text-emerald-700" },
  medium: { label: "Trung bình",cls: "bg-orange-100 text-orange-700" },
  hard:   { label: "Khó",       cls: "bg-red-100 text-red-700" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtTime(secs: number) {
  const m = Math.floor(secs / 60).toString().padStart(2, "0");
  const s = (secs % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/** Flatten TopicQuestionsGroup[] → QuestionForModuleTest[] in order */
function flattenQuestions(topics: TopicQuestionsGroup[]): QuestionForModuleTest[] {
  return topics.flatMap((g) => g.questions);
}

/** Map questionId → topicName */
function buildTopicNameMap(topics: TopicQuestionsGroup[]): Record<string, string> {
  const m: Record<string, string> = {};
  for (const g of topics) {
    for (const q of g.questions) m[q.id] = g.learning_unit_title;
  }
  return m;
}

/** First questionId for each topic group (used to show section header) */
function buildTopicFirstQuestionIds(topics: TopicQuestionsGroup[]): Set<string> {
  const s = new Set<string>();
  for (const g of topics) {
    if (g.questions[0]) s.add(g.questions[0].id);
  }
  return s;
}

// ---------------------------------------------------------------------------
// Nav panel question button
// ---------------------------------------------------------------------------

function NavQBtn({
  num,
  answered,
  flagged,
  active,
  onClick,
}: {
  num: number;
  answered: boolean;
  flagged: boolean;
  active: boolean;
  onClick: () => void;
}) {
  let cls =
    "flex h-8 w-8 items-center justify-center rounded-lg text-xs font-semibold transition-all cursor-pointer border ";

  if (active) {
    cls += "border-primary-500 bg-primary-500 text-white shadow-sm";
  } else if (flagged) {
    cls += "border-yellow-400 bg-yellow-100 text-yellow-800";
  } else if (answered) {
    cls += "border-blue-400 bg-blue-100 text-blue-800";
  } else {
    cls += "border-slate-200 bg-white text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400";
  }

  return (
    <button type="button" className={cls} onClick={onClick}>
      {num}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Confirm submit dialog
// ---------------------------------------------------------------------------

function ConfirmDialog({
  unansweredCount,
  flaggedCount,
  onConfirm,
  onCancel,
  loading,
}: {
  unansweredCount: number;
  flaggedCount: number;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />
      {/* Dialog */}
      <div
        className="relative w-full max-w-sm rounded-2xl p-6 shadow-2xl"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
      >
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-100">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
          </div>
          <h2 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
            Xác nhận nộp bài
          </h2>
        </div>

        <div className="space-y-2 text-sm" style={{ color: "var(--text-secondary)" }}>
          {unansweredCount > 0 && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
              ⚠️ Còn <strong>{unansweredCount}</strong> câu chưa trả lời.
            </p>
          )}
          {flaggedCount > 0 && (
            <p className="rounded-lg bg-yellow-50 px-3 py-2 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400">
              🚩 Còn <strong>{flaggedCount}</strong> câu đã đánh dấu cần xem lại.
            </p>
          )}
          {unansweredCount === 0 && flaggedCount === 0 && (
            <p>Bạn đã trả lời tất cả câu hỏi. Xác nhận nộp bài?</p>
          )}
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn-secondary flex-1"
          >
            Xem lại
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="btn-primary flex flex-1 items-center justify-center gap-2"
          >
            {loading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Nộp bài
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type Phase = "loading" | "active" | "submitting" | "error";

export default function ModuleTestPage() {
  const { sectionId } = useParams<{ sectionId: string }>();
  const router = useRouter();
  const runtimeRef = buildModuleTestRuntimeRef(sectionId);

  // ── Core state ───────────────────────────────────────────────────────────
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [startData, setStartData] = useState<ModuleTestStartResponse | null>(null);
  const [allQuestions, setAllQuestions] = useState<QuestionForModuleTest[]>([]);
  const [topicNameMap, setTopicNameMap] = useState<Record<string, string>>({});
  const [firstQIds, setFirstQIds] = useState<Set<string>>(new Set());
  const [sessionId, setSessionId] = useState("");

  // ── Answer / flag state ───────────────────────────────────────────────────
  const [answers, setAnswers] = useState<Record<string, SelectedAnswer>>({});
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [currentIdx, setCurrentIdx] = useState(0);

  // ── UI state ──────────────────────────────────────────────────────────────
  const [navOpen, setNavOpen] = useState(false);       // mobile nav drawer
  const [showConfirm, setShowConfirm] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load session on mount ─────────────────────────────────────────────────
  useEffect(() => {
    if (!runtimeRef.sectionId) return;
    canonicalModuleTestApi
      .start(runtimeRef.sectionId)
      .then((data) => {
        const flat = flattenQuestions(data.learning_units);
        setStartData(data);
        setAllQuestions(flat);
        setTopicNameMap(buildTopicNameMap(data.learning_units));
        setFirstQIds(buildTopicFirstQuestionIds(data.learning_units));
        setSessionId(data.session_id);
        setPhase("active");
        timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
      })
      .catch((err) => {
        const d = err?.response?.data?.detail;
        setErrorMsg(typeof d === "string" ? d : "Không thể bắt đầu module test.");
        setPhase("error");
      });

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [runtimeRef.sectionId]);

  // ── Keyboard navigation ───────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "active") return;
    const handler = (e: KeyboardEvent) => {
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) return;
      const map: Record<string, SelectedAnswer> = { a: "A", b: "B", c: "C", d: "D" };
      const opt = map[e.key.toLowerCase()];
      const q = allQuestions[currentIdx];
      if (opt && q) {
        setAnswers((prev) => ({ ...prev, [q.id]: opt }));
        return;
      }
      if (e.key === "ArrowRight" || (e.key === "Enter" && answers[allQuestions[currentIdx]?.id])) {
        goNext();
      }
      if (e.key === "ArrowLeft") goPrev();
      if (e.key === "f" || e.key === "F") toggleFlag();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }); // intentionally no deps array — needs fresh closure each render

  // ── Navigation helpers ────────────────────────────────────────────────────
  const goNext = useCallback(() => {
    setCurrentIdx((i) => Math.min(i + 1, allQuestions.length - 1));
  }, [allQuestions.length]);

  const goPrev = useCallback(() => {
    setCurrentIdx((i) => Math.max(i - 1, 0));
  }, []);

  const toggleFlag = useCallback(() => {
    const q = allQuestions[currentIdx];
    if (!q) return;
    setFlagged((prev) => {
      const next = new Set(prev);
      next.has(q.id) ? next.delete(q.id) : next.add(q.id);
      return next;
    });
  }, [allQuestions, currentIdx]);

  // ── Submit ────────────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!sessionId) return;
    setShowConfirm(false);
    setPhase("submitting");
    if (timerRef.current) clearInterval(timerRef.current);

    const answerList: ModuleTestAnswerInput[] = allQuestions
      .filter((q) => answers[q.id] !== undefined)
      .map((q) => ({
        question_id: q.id,
        selected_answer: answers[q.id],
        response_time_ms: null,
      }));

    try {
      const result = await moduleTestApi.submit(sessionId, answerList);
      sessionStorage.setItem(
        runtimeRef.resultStorageKey,
        JSON.stringify(result)
      );
      router.push(runtimeRef.resultsHref);
    } catch (err: unknown) {
      const d = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setErrorMsg(typeof d === "string" ? d : "Nộp bài thất bại. Vui lòng thử lại.");
      setPhase("active");
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    }
  }

  // ── Derived ───────────────────────────────────────────────────────────────
  const question = allQuestions[currentIdx];
  const unansweredCount = allQuestions.filter((q) => !answers[q.id]).length;
  const flaggedCount = flagged.size;
  const isFirst = currentIdx === 0;
  const isLast = currentIdx === allQuestions.length - 1;

  // ── Loading / Error screens ────────────────────────────────────────────────
  if (phase === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Đang tải đề thi...</p>
        </div>
      </div>
    );
  }

  if (phase === "error" && !question) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6" style={{ background: "var(--bg-primary)" }}>
        <div className="max-w-sm text-center space-y-4">
          <AlertCircle className="mx-auto text-red-500" size={40} />
          <p className="font-semibold" style={{ color: "var(--text-primary)" }}>Không thể bắt đầu</p>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{errorMsg}</p>
          <button onClick={() => router.back()} className="btn-secondary">
            Quay lại
          </button>
        </div>
      </div>
    );
  }

  if (!question || !startData) return null;

  const bloom = BLOOM_BADGE[question.bloom_level];
  const diff = DIFF_BADGE[question.difficulty_bucket];
  const currentTopicName = topicNameMap[question.id] ?? "";
  const isFirstOfTopic = firstQIds.has(question.id);
  const isCurrentFlagged = flagged.has(question.id);
  const currentAnswer = answers[question.id];
  const questionNum = currentIdx + 1;
  const progressPct = Math.round(
    (Object.keys(answers).length / allQuestions.length) * 100
  );

  // Build per-learning-unit groups for the nav panel
  const navGroups = startData.learning_units.map((g, gi) => {
    // Find the global indices for questions in this group
    const groupStart = startData.learning_units
      .slice(0, gi)
      .reduce((acc, t) => acc + t.questions.length, 0);
    return {
      learning_unit_title: g.learning_unit_title,
      questions: g.questions.map((q, qi) => ({
        id: q.id,
        globalIdx: groupStart + qi,
        num: groupStart + qi + 1,
      })),
    };
  });

  // ── Nav Panel (shared between desktop sidebar + mobile drawer) ─────────────
  const NavPanel = (
    <div className="flex flex-col h-full">
      {/* Legend */}
      <div className="mb-3 flex flex-wrap gap-x-3 gap-y-1 text-xs" style={{ color: "var(--text-muted)" }}>
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded bg-blue-300" />Đã trả lời
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded bg-yellow-300" />Đánh dấu
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded border border-slate-300 bg-white dark:border-slate-600 dark:bg-slate-800" />Chưa trả lời
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {navGroups.map((group) => (
          <div key={group.learning_unit_title}>
            <p
              className="mb-2 text-xs font-semibold uppercase tracking-wide truncate"
              style={{ color: "var(--text-muted)" }}
            >
              {group.learning_unit_title}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {group.questions.map(({ id, globalIdx, num }) => (
                <NavQBtn
                  key={id}
                  num={num}
                  answered={!!answers[id]}
                  flagged={flagged.has(id)}
                  active={globalIdx === currentIdx}
                  onClick={() => {
                    setCurrentIdx(globalIdx);
                    setNavOpen(false);
                  }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Submit CTA in panel */}
      <div className="mt-4 pt-4 border-t" style={{ borderColor: "var(--border)" }}>
        <div className="mb-2 text-xs" style={{ color: "var(--text-muted)" }}>
          Đã trả lời:{" "}
          <strong style={{ color: "var(--text-primary)" }}>
            {allQuestions.length - unansweredCount}/{allQuestions.length}
          </strong>
        </div>
        <button
          onClick={() => setShowConfirm(true)}
          className="btn-primary flex w-full items-center justify-center gap-2"
        >
          <Send className="h-4 w-4" />
          Nộp bài
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen flex-col" style={{ background: "var(--bg-primary)" }}>

      {/* ── Mobile nav drawer ─────────────────────────────────────────────── */}
      {navOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setNavOpen(false)}
          />
          <div
            className="absolute left-0 top-0 h-full w-72 p-5 shadow-2xl overflow-y-auto"
            style={{ background: "var(--bg-elevated)" }}
          >
            <button
              onClick={() => setNavOpen(false)}
              className="mb-4 flex items-center gap-2 text-sm"
              style={{ color: "var(--text-muted)" }}
            >
              <X size={16} /> Đóng
            </button>
            {NavPanel}
          </div>
        </div>
      )}

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 border-b px-4 py-2.5 backdrop-blur-sm"
        style={{
          background: "color-mix(in srgb, var(--bg-elevated) 95%, transparent)",
          borderColor: "var(--border)",
        }}
      >
        <div className="flex items-center gap-3 max-w-5xl mx-auto">
          {/* Mobile menu button */}
          <button
            className="rounded-lg p-1.5 lg:hidden"
            style={{ color: "var(--text-muted)" }}
            onClick={() => setNavOpen(true)}
          >
            <Menu size={18} />
          </button>

          {/* Module title */}
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <Brain className="h-5 w-5 shrink-0 text-primary-500" />
            <span className="truncate text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              {startData.section_title}
            </span>
          </div>

          {/* Progress bar */}
          <div className="hidden sm:flex items-center gap-2 flex-1 max-w-xs">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className="h-full rounded-full bg-primary-500 transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <span className="shrink-0 text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
              {allQuestions.length - unansweredCount}/{allQuestions.length}
            </span>
          </div>

          {/* Timer */}
          <div
            className="flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1 font-mono text-xs font-medium"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
          >
            <Clock size={13} />
            {fmtTime(elapsed)}
          </div>

          {/* Submit button (header) */}
          <button
            onClick={() => setShowConfirm(true)}
            disabled={phase === "submitting"}
            className="btn-primary hidden shrink-0 items-center gap-1.5 sm:flex"
          >
            <Send size={14} />
            Nộp bài
          </button>
        </div>
      </header>

      {/* ── Body: sidebar + question ──────────────────────────────────────── */}
      <div className="mx-auto flex w-full max-w-5xl flex-1 gap-6 px-4 py-5">

        {/* Desktop nav sidebar */}
        <aside
          className="hidden lg:flex w-52 shrink-0 flex-col rounded-2xl border p-4"
          style={{ borderColor: "var(--border)", background: "var(--bg-elevated)", height: "fit-content", position: "sticky", top: "72px" }}
        >
          {NavPanel}
        </aside>

        {/* Main question area */}
        <div className="min-w-0 flex-1 space-y-4">

          {/* Error banner */}
          {errorMsg && phase === "active" && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {errorMsg}
            </div>
          )}

          {/* Topic section header — shown when first question of a topic */}
          {isFirstOfTopic && (
            <div
              className="flex items-center gap-2 rounded-xl border px-4 py-3"
              style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
            >
              <BookOpen size={16} style={{ color: "var(--color-primary-500)" }} />
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {currentTopicName}
              </span>
            </div>
          )}

          {/* Question card */}
          <div
            key={currentIdx}
            className="animate-fade-in rounded-2xl border p-5"
            style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
          >
            {/* Meta row */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                Câu {questionNum}
              </span>
              {bloom && (
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${bloom.cls}`}>
                  {bloom.label}
                </span>
              )}
              {diff && (
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${diff.cls}`}>
                  {diff.label}
                </span>
              )}

              {/* Flag button */}
              <button
                onClick={toggleFlag}
                className={[
                  "ml-auto flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors",
                  isCurrentFlagged
                    ? "bg-yellow-100 text-yellow-700"
                    : "bg-slate-100 text-slate-500 hover:bg-yellow-50 hover:text-yellow-600 dark:bg-slate-800 dark:text-slate-400",
                ].join(" ")}
              >
                <Flag size={12} />
                {isCurrentFlagged ? "Đã đánh dấu" : "Đánh dấu"}
              </button>
            </div>

            {/* Stem */}
            <div className="text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
              <MarkdownRenderer text={question.stem_text} />
            </div>
          </div>

          {/* Options */}
          <div className="space-y-2.5">
            {OPTIONS.map((opt) => {
              const isSelected = currentAnswer === opt;
              return (
                <button
                  key={opt}
                  type="button"
                  onClick={() =>
                    setAnswers((prev) => ({ ...prev, [question.id]: opt }))
                  }
                  className={[
                    "flex w-full items-start gap-3 rounded-xl border-2 px-4 py-3.5 text-left",
                    "transition-all duration-150 active:scale-[0.99]",
                    isSelected
                      ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                      : "hover:border-slate-300 dark:hover:border-slate-600",
                  ].join(" ")}
                  style={{
                    borderColor: isSelected ? undefined : "var(--border)",
                    background: isSelected ? undefined : "var(--bg-elevated)",
                  }}
                >
                  <span
                    className={[
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-sm font-bold transition-colors",
                      isSelected
                        ? "bg-primary-600 text-white"
                        : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
                    ].join(" ")}
                  >
                    {opt}
                  </span>
                  <span
                    className={[
                      "mt-0.5 text-sm leading-relaxed",
                      isSelected
                        ? "font-medium text-primary-700 dark:text-primary-200"
                        : "",
                    ].join(" ")}
                    style={{ color: isSelected ? undefined : "var(--text-primary)" }}
                  >
                    {opt === "A" ? question.option_a
                      : opt === "B" ? question.option_b
                      : opt === "C" ? question.option_c
                      : question.option_d}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Prev / Next navigation */}
          <div className="flex items-center justify-between pt-2 pb-6">
            <button
              onClick={goPrev}
              disabled={isFirst}
              className="btn-secondary flex items-center gap-1.5 disabled:opacity-40"
            >
              <ChevronLeft size={15} />
              Câu trước
            </button>

            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {questionNum} / {allQuestions.length}
            </span>

            {isLast ? (
              <button
                onClick={() => setShowConfirm(true)}
                className="btn-primary flex items-center gap-1.5"
              >
                <Send size={15} />
                Nộp bài
              </button>
            ) : (
              <button
                onClick={goNext}
                className="btn-primary flex items-center gap-1.5"
              >
                Câu sau
                <ChevronRight size={15} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Confirm dialog ──────────────────────────────────────────────────── */}
      {showConfirm && (
        <ConfirmDialog
          unansweredCount={unansweredCount}
          flaggedCount={flaggedCount}
          onConfirm={handleSubmit}
          onCancel={() => setShowConfirm(false)}
          loading={phase === "submitting"}
        />
      )}
    </div>
  );
}
