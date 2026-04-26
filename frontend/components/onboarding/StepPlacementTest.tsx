"use client";
// components/onboarding/StepPlacementTest.tsx
// Step 5 — Placement assessment: fetch questions, collect answers, show results.

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import {
  startPlacementAssessment,
  submitPlacementAssessment,
} from "@/lib/placement-assessment-api";
import type { PlacementQuestion, PlacementAnswerInput, TopicDecision } from "@/lib/placement-assessment-api";
import { useOnboardingStore } from "@/stores/onboardingStore";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  sessionId: string;
  unitIds: string[];
  onComplete: (decisions: TopicDecision[]) => void;
  onSkip: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupByUnit(questions: PlacementQuestion[]): Map<string, PlacementQuestion[]> {
  const map = new Map<string, PlacementQuestion[]>();
  for (const q of questions) {
    const group = map.get(q.topic_unit_id) ?? [];
    group.push(q);
    map.set(q.topic_unit_id, group);
  }
  return map;
}

function decisionLabel(decision: TopicDecision["decision"]): string {
  if (decision === "skip") return "✓ Skip";
  if (decision === "review") return "⚠ Review";
  return "✗ Relearn";
}

function decisionClass(decision: TopicDecision["decision"]): string {
  if (decision === "skip") return "text-green-600";
  if (decision === "review") return "text-yellow-600";
  return "text-red-600";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function StepPlacementTest({ sessionId, unitIds, onComplete, onSkip }: Props) {
  const [questions, setQuestions] = useState<PlacementQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // answers: item_id → selected_option
  const [answers, setAnswers] = useState<Record<string, string>>({});

  // results after submit
  const [topicDecisions, setTopicDecisions] = useState<TopicDecision[] | null>(null);

  // Unmount guard shared by both async paths
  const aliveRef = useRef(true);
  useEffect(() => () => { aliveRef.current = false; }, []);

  // ── Fetch questions on mount ───────────────────────────────────────────────
  useEffect(() => {
    async function load() {
      try {
        const res = await startPlacementAssessment({ session_id: sessionId, unit_ids: unitIds });
        if (aliveRef.current) setQuestions(res.questions);
      } catch {
        if (aliveRef.current) setError("Không thể tải câu hỏi. Vui lòng thử lại.");
      } finally {
        if (aliveRef.current) setLoading(false);
      }
    }
    load();
  }, [sessionId, unitIds]);

  // ── Submit ─────────────────────────────────────────────────────────────────
  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const answerList: PlacementAnswerInput[] = Object.entries(answers).map(
        ([item_id, selected_option]) => ({ item_id, selected_option }),
      );
      const res = await submitPlacementAssessment({ session_id: sessionId, answers: answerList });

      if (!aliveRef.current) return;

      // Persist to store
      useOnboardingStore.getState().setPlacementSessionId(sessionId);
      useOnboardingStore.getState().setPlacementResults(res.topic_decisions);

      setTopicDecisions(res.topic_decisions);
    } catch {
      if (aliveRef.current) setError("Gửi bài thất bại. Vui lòng thử lại.");
    } finally {
      if (aliveRef.current) setSubmitting(false);
    }
  }

  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.item_id] !== undefined);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
        Đang tải câu hỏi...
      </div>
    );
  }

  // ── Results state ──────────────────────────────────────────────────────────
  if (topicDecisions) {
    return (
      <div className="space-y-4">
        <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Kết quả đánh giá
        </p>

        <div className="space-y-3">
          {topicDecisions.map((d) => (
            <div
              key={d.topic_unit_id}
              className="flex items-center justify-between rounded-xl border-2 p-4"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
            >
              <span className="text-sm font-medium font-mono text-xs" style={{ color: "var(--text-primary)" }}>
                {d.topic_unit_id}
              </span>
              <div className="flex items-center gap-3">
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {Math.round(d.score_pct)}%
                </span>
                <span className={cn("text-sm font-semibold", decisionClass(d.decision))}>
                  {decisionLabel(d.decision)}
                </span>
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => onComplete(topicDecisions)}
          className="w-full rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Hoàn thành
        </button>
      </div>
    );
  }

  // ── Question UI ────────────────────────────────────────────────────────────
  const groups = groupByUnit(questions);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Trả lời tất cả câu hỏi để hệ thống đánh giá kiến thức của bạn.
        </p>
        <button
          type="button"
          onClick={onSkip}
          className="text-xs underline"
          style={{ color: "var(--text-muted)" }}
        >
          Bỏ qua
        </button>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {Array.from(groups.entries()).map(([unitId, unitQuestions]) => (
        <div key={unitId} className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Unit: {unitId}
          </p>

          {unitQuestions.map((q, qIdx) => {
            const selected = answers[q.item_id];
            const optionKeys = Object.keys(q.options).sort();

            return (
              <div
                key={q.item_id}
                className="rounded-xl border-2 p-4 space-y-3"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
              >
                <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {qIdx + 1}. {q.question_text}
                </p>

                <div className="space-y-2">
                  {optionKeys.map((key) => {
                    const isSelected = selected === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setAnswers((prev) => ({ ...prev, [q.item_id]: key }))}
                        className={cn(
                          "w-full rounded-lg border-2 px-4 py-2 text-left text-sm transition-all duration-150",
                          "hover:shadow-sm active:scale-[0.99]",
                          isSelected
                            ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                            : "hover:border-slate-300 dark:hover:border-slate-600",
                        )}
                        style={{
                          borderColor: isSelected ? undefined : "var(--border)",
                          backgroundColor: isSelected ? undefined : "var(--bg-card)",
                          color: isSelected ? undefined : "var(--text-primary)",
                        }}
                      >
                        <span className="font-semibold mr-2">{key}.</span>
                        {q.options[key]}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ))}

      <div className="pt-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!allAnswered || submitting}
          className={cn(
            "w-full rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-150",
            !allAnswered || submitting
              ? "cursor-not-allowed bg-slate-200 text-slate-400 dark:bg-slate-700 dark:text-slate-500"
              : "bg-primary-600 text-white hover:bg-primary-700 active:scale-[0.99]",
          )}
        >
          {submitting ? "Đang gửi..." : "Nộp bài"}
        </button>
      </div>
    </div>
  );
}
