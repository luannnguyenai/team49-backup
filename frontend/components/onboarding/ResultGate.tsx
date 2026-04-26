"use client";
// components/onboarding/ResultGate.tsx
// Step 6 — Shows placement results and lets user decide on "review" topics.

import { useState } from "react";
import { setTopicDecision } from "@/lib/placement-assessment-api";
import type { TopicDecision } from "@/lib/placement-assessment-api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  results: TopicDecision[];
  onConfirm: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type UserChoice = "skip" | "review";

interface DecisionState {
  [topic_unit_id: string]: UserChoice;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ResultGate({ results, onConfirm }: Props) {
  const [decisions, setDecisions] = useState<DecisionState>({});
  const [pending, setPending] = useState<Set<string>>(new Set());

  const reviewTopics = results.filter((r) => r.decision === "review");
  const allReviewsDecided = reviewTopics.every((r) => decisions[r.topic_unit_id] !== undefined);

  async function handleChoice(topicUnitId: string, choice: UserChoice) {
    if (pending.has(topicUnitId)) return;

    setPending((prev) => new Set(prev).add(topicUnitId));
    try {
      await setTopicDecision({ topic_unit_id: topicUnitId, user_choice: choice });
      setDecisions((prev) => ({ ...prev, [topicUnitId]: choice }));
    } finally {
      setPending((prev) => {
        const next = new Set(prev);
        next.delete(topicUnitId);
        return next;
      });
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
          Kết quả đánh giá kiến thức
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Xem lại kết quả từng topic và quyết định cách tiến hành.
        </p>
      </div>

      <div className="space-y-3">
        {results.map((r) => {
          if (r.decision === "skip") {
            return (
              <div
                key={r.topic_unit_id}
                className="flex items-center justify-between rounded-xl border p-3"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
              >
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {r.topic_unit_id}
                </span>
                <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-400">
                  Mastered — đã miễn ✓
                </span>
              </div>
            );
          }

          if (r.decision === "relearn") {
            return (
              <div
                key={r.topic_unit_id}
                className="flex items-center justify-between rounded-xl border p-3"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
              >
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {r.topic_unit_id}
                </span>
                <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700 dark:bg-red-900/30 dark:text-red-400">
                  Cần học lại ✗
                </span>
              </div>
            );
          }

          // decision === "review"
          const userChoice = decisions[r.topic_unit_id];
          const isLoading = pending.has(r.topic_unit_id);

          return (
            <div
              key={r.topic_unit_id}
              className="rounded-xl border border-yellow-300 bg-yellow-50 p-3 dark:border-yellow-700 dark:bg-yellow-900/20"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-yellow-900 dark:text-yellow-200">
                  {r.topic_unit_id}
                </span>
                <span className="text-xs text-yellow-700 dark:text-yellow-400">
                  {Math.round(r.score_pct)}% đúng
                </span>
              </div>

              {userChoice ? (
                <div className="text-xs font-semibold text-yellow-800 dark:text-yellow-300">
                  {userChoice === "review" ? "→ Review (đã chọn)" : "→ Bỏ qua (đã chọn)"}
                </div>
              ) : (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={isLoading}
                    onClick={() => handleChoice(r.topic_unit_id, "review")}
                    className="rounded-lg bg-yellow-600 px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    Review (recommend)
                  </button>
                  <button
                    type="button"
                    disabled={isLoading}
                    onClick={() => handleChoice(r.topic_unit_id, "skip")}
                    className="rounded-lg border border-yellow-600 px-3 py-1.5 text-xs font-semibold text-yellow-700 transition-opacity hover:opacity-90 disabled:opacity-50 dark:text-yellow-400"
                  >
                    Bỏ qua
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button
        type="button"
        disabled={!allReviewsDecided}
        onClick={onConfirm}
        className="w-full rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
      >
        Xác nhận và tiếp tục
      </button>
    </div>
  );
}
