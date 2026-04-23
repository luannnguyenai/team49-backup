"use client";

// app/quiz/[topicId]/results/page.tsx
// Quiz results: score, mastery before→after animated, bloom bar chart,
// wrong answers list, KC review suggestions, 3 CTA buttons.

import { Suspense, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  Brain,
  CheckCircle2,
  Home,
  Lightbulb,
  RotateCcw,
  TrendingUp,
} from "lucide-react";
import type { MasteryLevel, QuizCompleteResponse } from "@/types";
import { buildQuizRuntimeRef } from "@/lib/canonical-learning-runtime";
import { MASTERY_COLORS, BLOOM_COLORS } from "@/lib/ui/skillColors";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MASTERY_LABELS: Record<MasteryLevel, string> = {
  not_started: "Chưa bắt đầu",
  novice: "Mới bắt đầu",
  developing: "Đang phát triển",
  proficient: "Thành thạo",
  mastered: "Xuất sắc",
};

const MASTERY_BG: Record<MasteryLevel, string> = {
  not_started: "bg-slate-100 text-slate-600",
  novice: "bg-red-100 text-red-700",
  developing: "bg-orange-100 text-orange-700",
  proficient: "bg-blue-100 text-blue-700",
  mastered: "bg-emerald-100 text-emerald-700",
};

const BLOOM_LABELS: Record<string, string> = {
  remember: "Nhớ",
  understand: "Hiểu",
  apply: "Áp dụng",
  analyze: "Phân tích",
};


function fmtSeconds(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  if (m === 0) return `${sec}s`;
  return `${m}m ${sec}s`;
}

// ---------------------------------------------------------------------------
// Animated mastery bar
// ---------------------------------------------------------------------------

function MasteryBar({
  label,
  value,
  color,
  animate,
}: {
  label: string;
  value: number;
  color: string;
  animate: boolean;
}) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    if (animate) {
      const t = setTimeout(() => setWidth(value), 80);
      return () => clearTimeout(t);
    }
    setWidth(value);
  }, [animate, value]);

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs" style={{ color: "var(--text-muted)" }}>
        <span>{label}</span>
        <span className="tabular-nums font-medium" style={{ color: "var(--text-primary)" }}>
          {value.toFixed(1)}%
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${width}%`, background: color }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bloom bar chart row
// ---------------------------------------------------------------------------

function BloomRow({ label, value, color }: { label: string; value: string; color: string }) {
  const [correct, total] = value.split("/").map(Number);
  const pct = total > 0 ? (correct / total) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      <span className="w-24 shrink-0 text-right text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
        {label}
      </span>
      <div className="flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700 h-3">
        {total > 0 && (
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, background: color }}
          />
        )}
      </div>
      <span className="w-10 text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
        {total > 0 ? `${correct}/${total}` : "—"}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main inner component (uses client-only sessionStorage)
// ---------------------------------------------------------------------------

function QuizResultsInner() {
  const { topicId } = useParams<{ topicId: string }>();
  const router = useRouter();
  const runtimeRef = buildQuizRuntimeRef(topicId);

  const [result, setResult] = useState<QuizCompleteResponse | null>(null);
  const [animReady, setAnimReady] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem(runtimeRef.resultStorageKey);
    if (raw) {
      try {
        setResult(JSON.parse(raw));
      } catch {
        // ignore parse error
      }
    }
    // Trigger bar animations after a brief mount delay
    const t = setTimeout(() => setAnimReady(true), 150);
    return () => clearTimeout(t);
  }, [runtimeRef.resultStorageKey]);

  if (!result) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6" style={{ background: "var(--bg-primary)" }}>
        <div className="text-center">
          <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
            Không tìm thấy kết quả quiz.
          </p>
          <button
            onClick={() => router.push("/dashboard")}
            className="btn-secondary mt-4"
          >
            Về trang chủ
          </button>
        </div>
      </div>
    );
  }

  const masteryColor = MASTERY_COLORS[result.mastery_level];
  const [correctStr, totalStr] = result.score.split("/");
  const correctNum = Number(correctStr);
  const totalNum = Number(totalStr);

  const bloomEntries = Object.entries(result.bloom_breakdown).filter(
    ([, val]) => val !== "0/0"
  );

  return (
    <div
      className="min-h-screen pb-16"
      style={{ background: "var(--bg-primary)" }}
    >
      {/* Header */}
      <header
        className="sticky top-0 z-10 flex items-center gap-3 border-b px-4 py-3 md:px-6"
        style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
      >
        <button
          onClick={() => router.push(runtimeRef.learnHref)}
          className="rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800"
          style={{ color: "var(--text-secondary)" }}
          aria-label="Quay lại"
        >
          <ArrowLeft size={18} />
        </button>
        <h1 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
          Kết quả Quiz: {result.topic_name}
        </h1>
      </header>

      <div className="mx-auto max-w-xl space-y-5 px-4 pt-6 md:px-6">
        {/* Score card */}
        <div
          className="rounded-2xl border p-6 text-center"
          style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
        >
          <div
            className="mx-auto mb-3 flex h-20 w-20 items-center justify-center rounded-full text-3xl font-black"
            style={{ background: `${masteryColor}22`, color: masteryColor }}
          >
            {correctNum}/{totalNum}
          </div>

          <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            {result.percent.toFixed(1)}%
          </p>

          <span
            className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-semibold ${MASTERY_BG[result.mastery_level]}`}
          >
            {MASTERY_LABELS[result.mastery_level]}
          </span>

          <div
            className="mt-4 grid grid-cols-2 gap-3 text-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>Tổng thời gian</p>
              <p className="mt-0.5 font-semibold" style={{ color: "var(--text-primary)" }}>
                {fmtSeconds(result.time_total_seconds)}
              </p>
            </div>
            <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>TB / câu</p>
              <p className="mt-0.5 font-semibold" style={{ color: "var(--text-primary)" }}>
                {fmtSeconds(result.avg_time_per_question)}
              </p>
            </div>
          </div>

          {result.learning_path_updated && (
            <div className="mt-3 flex items-center justify-center gap-1.5 text-xs text-emerald-600 font-medium">
              <CheckCircle2 size={14} />
              Lộ trình học đã được cập nhật tự động
            </div>
          )}
        </div>

        {/* Mastery delta */}
        <div
          className="rounded-2xl border p-5 space-y-4"
          style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
        >
          <div className="flex items-center gap-2">
            <TrendingUp size={17} style={{ color: masteryColor }} />
            <h2 className="font-semibold" style={{ color: "var(--text-primary)" }}>
              Mức độ thành thạo
            </h2>
          </div>

          <MasteryBar
            label="Trước quiz"
            value={result.mastery_before}
            color="#94a3b8"
            animate={animReady}
          />
          <MasteryBar
            label="Sau quiz"
            value={result.mastery_after}
            color={masteryColor}
            animate={animReady}
          />

          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Thay đổi:{" "}
            <span
              className="font-semibold"
              style={{ color: result.mastery_after >= result.mastery_before ? MASTERY_COLORS.mastered : MASTERY_COLORS.novice }}
            >
              {result.mastery_after >= result.mastery_before ? "+" : ""}
              {(result.mastery_after - result.mastery_before).toFixed(1)}%
            </span>
          </p>
        </div>

        {/* Bloom breakdown */}
        {bloomEntries.length > 0 && (
          <div
            className="rounded-2xl border p-5 space-y-3"
            style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
          >
            <div className="flex items-center gap-2">
              <Brain size={17} style={{ color: "var(--color-primary-500)" }} />
              <h2 className="font-semibold" style={{ color: "var(--text-primary)" }}>
                Phân tích theo Bloom
              </h2>
            </div>

            <div className="space-y-2.5">
              {bloomEntries.map(([level, val]) => (
                <BloomRow
                  key={level}
                  label={BLOOM_LABELS[level] ?? level}
                  value={val}
                  color={BLOOM_COLORS[level] ?? "#94a3b8"}
                />
              ))}
            </div>
          </div>
        )}

        {/* KC Review suggestions */}
        {result.weak_kcs.length > 0 && (
          <div
            className="rounded-2xl border p-5"
            style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
          >
            <div className="mb-3 flex items-center gap-2">
              <BookOpen size={17} className="text-amber-500" />
              <h2 className="font-semibold" style={{ color: "var(--text-primary)" }}>
                Kiến thức cần ôn lại
              </h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.weak_kcs.map((kc) => (
                <span
                  key={kc}
                  className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800"
                >
                  {kc}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Misconceptions */}
        {result.misconceptions.length > 0 && (
          <div
            className="rounded-2xl border p-5"
            style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}
          >
            <div className="mb-3 flex items-center gap-2">
              <Lightbulb size={17} className="text-yellow-500" />
              <h2 className="font-semibold" style={{ color: "var(--text-primary)" }}>
                Hiểu nhầm được phát hiện
              </h2>
            </div>
            <ul className="space-y-1.5">
              {result.misconceptions.map((m) => (
                <li
                  key={m}
                  className="flex items-start gap-2 text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-400" />
                  {m}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* CTA buttons */}
        <div className="grid grid-cols-1 gap-3 pt-2 sm:grid-cols-3">
          <button
            onClick={() => router.push(runtimeRef.restartHref)}
            className="btn-secondary flex items-center justify-center gap-2"
          >
            <RotateCcw size={15} />
            Làm lại
          </button>

          <button
            onClick={() => router.push(runtimeRef.learnHref)}
            className="btn-secondary flex items-center justify-center gap-2"
          >
            <BookOpen size={15} />
            Ôn lại bài
          </button>

          <button
            onClick={() => router.push("/dashboard")}
            className="btn-primary flex items-center justify-center gap-2"
          >
            <Home size={15} />
            Trang chủ
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export with Suspense boundary (required for useParams in App Router)
// ---------------------------------------------------------------------------

export default function QuizResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--bg-primary)" }}>
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        </div>
      }
    >
      <QuizResultsInner />
    </Suspense>
  );
}
