"use client";

// app/module-test/[sectionId]/results/page.tsx
// Module test results:
//   PASS ✅ / FAIL ❌ hero section
//   Total score %
//   Per-topic breakdown table
//   FAIL path: weak topics + review hours + "Ôn lại" CTA
//   PASS path: confetti animation + next-module card
//   Wrong answers list with correct answer + explanation

import { Suspense, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clock,
  Home,
  Lightbulb,
  RotateCcw,
  Sparkles,
  Trophy,
  XCircle,
} from "lucide-react";
import type {
  ModuleTestResultResponse,
  SelectedAnswer,
  TopicTestResult,
  WrongAnswerDetail,
} from "@/types";
import { buildModuleTestRuntimeRef } from "@/lib/canonical-learning-runtime";
import MarkdownRenderer from "@/components/assessment/MarkdownRenderer";

// ---------------------------------------------------------------------------
// Helpers + constants
// ---------------------------------------------------------------------------

const BLOOM_VI: Record<string, string> = {
  remember:   "Nhớ",
  understand: "Hiểu",
  apply:      "Áp dụng",
  analyze:    "Phân tích",
};

const BLOOM_CLS: Record<string, string> = {
  remember:   "bg-sky-100 text-sky-700",
  understand: "bg-violet-100 text-violet-700",
  apply:      "bg-amber-100 text-amber-700",
  analyze:    "bg-rose-100 text-rose-700",
};

const VERDICT_CLS: Record<string, string> = {
  pass: "bg-emerald-100 text-emerald-700",
  fail: "bg-red-100 text-red-700",
};

const VERDICT_VI: Record<string, string> = {
  pass: "Đạt",
  fail: "Chưa đạt",
};

function optionText(w: WrongAnswerDetail, opt: SelectedAnswer): string {
  if (opt === "A") return w.option_a;
  if (opt === "B") return w.option_b;
  if (opt === "C") return w.option_c;
  return w.option_d;
}

// ---------------------------------------------------------------------------
// Confetti (pure CSS/JS — no library)
// ---------------------------------------------------------------------------

const CONFETTI_COLORS = [
  "#f97316", "#3b82f6", "#10b981", "#a855f7",
  "#ec4899", "#eab308", "#06b6d4", "#ef4444",
];

interface Piece {
  id: number;
  x: number;
  color: string;
  delay: number;
  duration: number;
  size: number;
}

function Confetti() {
  const pieces: Piece[] = Array.from({ length: 60 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
    delay: Math.random() * 2,
    duration: 2.5 + Math.random() * 2,
    size: 6 + Math.floor(Math.random() * 8),
  }));

  return (
    <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden">
      {pieces.map((p) => (
        <span
          key={p.id}
          className="absolute top-0 block rounded-sm opacity-0"
          style={{
            left: `${p.x}%`,
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
            animation: `confetti-fall ${p.duration}s ${p.delay}s ease-in forwards`,
          }}
        />
      ))}
      <style>{`
        @keyframes confetti-fall {
          0%   { transform: translateY(-20px) rotate(0deg);   opacity: 1; }
          100% { transform: translateY(110vh) rotate(720deg); opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Animated score counter
// ---------------------------------------------------------------------------

function AnimatedScore({ target }: { target: number }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const steps = 40;
    const inc = target / steps;
    let cur = 0;
    const id = setInterval(() => {
      cur = Math.min(cur + inc, target);
      setDisplay(Math.round(cur * 10) / 10);
      if (cur >= target) clearInterval(id);
    }, 30);
    return () => clearInterval(id);
  }, [target]);
  return <>{display.toFixed(1)}%</>;
}

// ---------------------------------------------------------------------------
// Per-topic table row
// ---------------------------------------------------------------------------

function TopicRow({ t }: { t: TopicTestResult }) {
  return (
    <tr className="border-t" style={{ borderColor: "var(--border)" }}>
      <td className="py-3 pr-4 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        {t.topic_name}
      </td>
      <td className="py-3 pr-4 text-sm tabular-nums" style={{ color: "var(--text-secondary)" }}>
        {t.score}
        <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>
          ({t.score_percent.toFixed(0)}%)
        </span>
      </td>
      <td className="py-3 pr-4">
        {t.bloom_max ? (
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${BLOOM_CLS[t.bloom_max] ?? "bg-slate-100 text-slate-600"}`}>
            {BLOOM_VI[t.bloom_max] ?? t.bloom_max}
          </span>
        ) : (
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>
        )}
      </td>
      <td className="py-3">
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${VERDICT_CLS[t.verdict]}`}>
          {VERDICT_VI[t.verdict]}
        </span>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Wrong answer card
// ---------------------------------------------------------------------------

function WrongAnswerCard({ item }: { item: WrongAnswerDetail }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="rounded-xl border"
      style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
    >
      {/* Stem (always visible) */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-3 p-4 text-left"
      >
        <XCircle className="mt-0.5 shrink-0 text-red-400" size={16} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
            {item.topic_name}
          </p>
          <div className="text-sm leading-relaxed line-clamp-2" style={{ color: "var(--text-primary)" }}>
            <MarkdownRenderer text={item.stem_text} />
          </div>
        </div>
        {open ? (
          <ChevronUp size={16} className="shrink-0 mt-0.5" style={{ color: "var(--text-muted)" }} />
        ) : (
          <ChevronDown size={16} className="shrink-0 mt-0.5" style={{ color: "var(--text-muted)" }} />
        )}
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t px-4 pb-4 pt-3 space-y-3" style={{ borderColor: "var(--border)" }}>
          {/* Options */}
          <div className="space-y-2">
            {(["A", "B", "C", "D"] as SelectedAnswer[]).map((opt) => {
              const isSelected = item.selected_answer === opt;
              const isCorrect = item.correct_answer === opt;
              return (
                <div
                  key={opt}
                  className={[
                    "flex items-start gap-2.5 rounded-lg px-3 py-2 text-sm",
                    isCorrect
                      ? "bg-emerald-50 border border-emerald-300 text-emerald-800"
                      : isSelected
                      ? "bg-red-50 border border-red-300 text-red-800"
                      : "border text-sm",
                  ].join(" ")}
                  style={!isCorrect && !isSelected ? { borderColor: "var(--border)", color: "var(--text-secondary)" } : {}}
                >
                  <span
                    className={[
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded text-xs font-bold",
                      isCorrect ? "bg-emerald-500 text-white"
                        : isSelected ? "bg-red-500 text-white"
                        : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
                    ].join(" ")}
                  >
                    {opt}
                  </span>
                  <span className="flex-1 leading-relaxed">
                    {optionText(item, opt)}
                  </span>
                  {isCorrect && <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-emerald-500" />}
                  {isSelected && !isCorrect && <XCircle size={14} className="shrink-0 mt-0.5 text-red-400" />}
                </div>
              );
            })}
          </div>

          {/* Explanation */}
          {item.explanation_text && (
            <div className="flex items-start gap-2 rounded-lg bg-blue-50 px-3 py-2.5 dark:bg-blue-900/20">
              <Lightbulb size={14} className="mt-0.5 shrink-0 text-blue-500" />
              <div className="text-sm leading-relaxed text-blue-800 dark:text-blue-200">
                <MarkdownRenderer text={item.explanation_text} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main inner component
// ---------------------------------------------------------------------------

function ModuleTestResultsInner() {
  const { sectionId } = useParams<{ sectionId: string }>();
  const router = useRouter();
  const runtimeRef = buildModuleTestRuntimeRef(sectionId);

  const [result, setResult] = useState<ModuleTestResultResponse | null>(null);
  const [animReady, setAnimReady] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const confettiStopRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem(runtimeRef.resultStorageKey);
    if (raw) {
      try {
        const parsed: ModuleTestResultResponse = JSON.parse(raw);
        setResult(parsed);
        if (parsed.passed) {
          setShowConfetti(true);
          confettiStopRef.current = setTimeout(() => setShowConfetti(false), 5000);
        }
      } catch {
        // ignore
      }
    }
    const t = setTimeout(() => setAnimReady(true), 100);
    return () => {
      clearTimeout(t);
      if (confettiStopRef.current) clearTimeout(confettiStopRef.current);
    };
  }, [runtimeRef.resultStorageKey]);

  if (!result) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--bg-primary)" }}
      >
        <div className="text-center space-y-4 p-6">
          <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
            Không tìm thấy kết quả.
          </p>
          <button onClick={() => router.push("/dashboard")} className="btn-secondary">
            Về trang chủ
          </button>
        </div>
      </div>
    );
  }

  const { passed, total_score_percent, per_topic, recommended_review_topics,
    estimated_review_hours, next_module, wrong_answers, module_name } = result;

  return (
    <div className="min-h-screen pb-20" style={{ background: "var(--bg-primary)" }}>
      {showConfetti && <Confetti />}

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-20 flex items-center gap-3 border-b px-4 py-3"
        style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
      >
        <button
          onClick={() => router.push("/dashboard")}
          className="rounded-lg p-1.5"
          style={{ color: "var(--text-muted)" }}
        >
          <Home size={18} />
        </button>
        <h1 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
          Kết quả: {module_name}
        </h1>
      </header>

      <div className="mx-auto max-w-2xl space-y-5 px-4 pt-6">

        {/* ── Hero: PASS / FAIL ──────────────────────────────────────────── */}
        <div
          className={[
            "rounded-2xl border p-6 text-center",
            passed
              ? "border-emerald-300 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20"
              : "border-red-300 bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20",
          ].join(" ")}
        >
          <div className="mb-3 text-5xl">
            {passed ? "✅" : "❌"}
          </div>

          <h2
            className={[
              "text-2xl font-black tracking-tight",
              passed ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400",
            ].join(" ")}
          >
            {passed ? "ĐẠT" : "CHƯA ĐẠT"}
          </h2>
          <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
            {passed ? "Chúc mừng! Bạn đã vượt qua module test." : "Bạn cần ôn thêm và thử lại."}
          </p>

          {/* Animated score */}
          <div
            className={[
              "mx-auto mt-4 flex h-24 w-24 items-center justify-center rounded-full text-2xl font-black",
              passed
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30"
                : "bg-red-100 text-red-700 dark:bg-red-900/30",
            ].join(" ")}
          >
            {animReady ? <AnimatedScore target={total_score_percent} /> : "0%"}
          </div>

          <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
            Yêu cầu: 70% • Đạt được: {total_score_percent.toFixed(1)}%
          </p>
        </div>

        {/* ── Per-topic breakdown table ───────────────────────────────────── */}
        <div
          className="rounded-2xl border overflow-hidden"
          style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
        >
          <div className="px-5 py-3 border-b" style={{ borderColor: "var(--border)" }}>
            <h3 className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
              Phân tích theo topic
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full px-5">
              <thead>
                <tr style={{ color: "var(--text-muted)" }}>
                  <th className="px-5 py-2.5 text-left text-xs font-medium">Topic</th>
                  <th className="px-0 py-2.5 text-left text-xs font-medium">Điểm</th>
                  <th className="px-0 py-2.5 text-left text-xs font-medium">Bloom max</th>
                  <th className="px-0 py-2.5 text-left text-xs font-medium">Kết quả</th>
                </tr>
              </thead>
              <tbody className="px-5">
                {per_topic.map((t) => (
                  <tr key={t.topic_id} className="border-t" style={{ borderColor: "var(--border)" }}>
                    <td className="px-5 py-3 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {t.topic_name}
                    </td>
                    <td className="py-3 pr-4 text-sm tabular-nums" style={{ color: "var(--text-secondary)" }}>
                      {t.score}
                      <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>
                        ({t.score_percent.toFixed(0)}%)
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      {t.bloom_max ? (
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${BLOOM_CLS[t.bloom_max] ?? "bg-slate-100 text-slate-600"}`}>
                          {BLOOM_VI[t.bloom_max] ?? t.bloom_max}
                        </span>
                      ) : (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>
                    <td className="py-3">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${VERDICT_CLS[t.verdict]}`}>
                        {VERDICT_VI[t.verdict]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── FAIL: weak topics + remediation ────────────────────────────── */}
        {!passed && recommended_review_topics.length > 0 && (
          <div
            className="rounded-2xl border p-5 space-y-4"
            style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
          >
            <div className="flex items-center justify-between">
              <h3 className="font-semibold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
                <BookOpen size={16} className="text-amber-500" />
                Các topic cần ôn lại
              </h3>
              <span className="flex items-center gap-1.5 text-xs rounded-full bg-amber-100 px-2.5 py-1 text-amber-700 font-medium">
                <Clock size={12} />
                Ước lượng: {estimated_review_hours}h thêm
              </span>
            </div>

            <div className="space-y-3">
              {recommended_review_topics.map((rt) => (
                <div
                  key={rt.topic_id}
                  className="flex items-start justify-between gap-3 rounded-xl border p-3"
                  style={{ borderColor: "var(--border)" }}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {rt.topic_name}
                    </p>
                    {rt.weak_kcs.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {rt.weak_kcs.map((kc) => (
                          <span
                            key={kc}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                          >
                            {kc}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                      ~{rt.estimated_review_hours}h ôn lại
                    </p>
                  </div>
                  <button
                    onClick={() => router.push(`/learn/${rt.topic_id}`)}
                    className="btn-secondary flex shrink-0 items-center gap-1.5 text-xs"
                  >
                    <BookOpen size={13} />
                    Ôn lại
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── PASS: next module card ──────────────────────────────────────── */}
        {passed && next_module && (
          <div
            className="rounded-2xl border p-5 bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20"
            style={{ borderColor: "var(--color-primary-300, #93c5fd)" }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={16} className="text-primary-500" />
              <span className="text-xs font-semibold uppercase tracking-wide text-primary-600">
                Module tiếp theo
              </span>
            </div>
            <p className="text-base font-bold mb-3" style={{ color: "var(--text-primary)" }}>
              {next_module.module_name}
            </p>
            <button
              onClick={() => router.push(`/module-test/${next_module.module_id}`)}
              className="btn-primary flex items-center gap-2"
            >
              Bắt đầu module
              <ArrowRight size={15} />
            </button>
          </div>
        )}

        {passed && !next_module && (
          <div
            className="rounded-2xl border p-5 text-center"
            style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
          >
            <Trophy className="mx-auto mb-2 text-yellow-500" size={32} />
            <p className="font-bold text-lg" style={{ color: "var(--text-primary)" }}>
              Bạn đã hoàn thành tất cả modules! 🎉
            </p>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Xuất sắc — không còn module nào tiếp theo.
            </p>
          </div>
        )}

        {/* ── Wrong answers section ───────────────────────────────────────── */}
        {wrong_answers.length > 0 && (
          <div>
            <h3
              className="mb-3 flex items-center gap-2 font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              <XCircle size={16} className="text-red-400" />
              Câu trả lời sai ({wrong_answers.length} câu)
            </h3>
            <div className="space-y-3">
              {wrong_answers.map((w) => (
                <WrongAnswerCard key={w.question_id} item={w} />
              ))}
            </div>
          </div>
        )}

        {/* ── CTA buttons ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-3 pt-2 sm:grid-cols-2">
          {!passed && (
            <button
              onClick={() => router.push(runtimeRef.restartHref)}
              className="btn-secondary flex items-center justify-center gap-2"
            >
              <RotateCcw size={15} />
              Thi lại
            </button>
          )}
          <button
            onClick={() => router.push("/dashboard")}
            className="btn-primary flex items-center justify-center gap-2"
          >
            <Home size={15} />
            Về trang chủ
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export with Suspense boundary (App Router requirement for useParams)
// ---------------------------------------------------------------------------

export default function ModuleTestResultsPage() {
  return (
    <Suspense
      fallback={
        <div
          className="flex min-h-screen items-center justify-center"
          style={{ background: "var(--bg-primary)" }}
        >
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        </div>
      }
    >
      <ModuleTestResultsInner />
    </Suspense>
  );
}
