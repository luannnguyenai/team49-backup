"use client";
// components/onboarding/StepGoalSelection.tsx
// Step 1 — Goal selection (multi-select, 3 cards).
// Titles are friendly goal names; course codes appear as small badges only.

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOnboardingStore } from "@/stores/onboardingStore";

// ---------------------------------------------------------------------------
// Static data — order: Computer Vision → NLP → Deep Learning
// ---------------------------------------------------------------------------

const GOALS = [
  {
    id: "computer_vision",
    emoji: "🖼️",
    label: "Computer Vision",
    description: "Học cách máy tính 'nhìn' và hiểu ảnh",
    badge: "CS231n",
  },
  {
    id: "nlp",
    emoji: "💬",
    label: "Natural Language Processing",
    description: "Dạy máy hiểu và sinh ngôn ngữ",
    badge: "CS224n",
  },
  {
    id: "deep_learning",
    emoji: "🧠",
    label: "Deep Learning",
    description: "Nền tảng deep learning, neural networks, optimization",
    badge: "CS230",
  },
] as const;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  onNext: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function StepGoalSelection({ onNext }: Props) {
  const goalIds = useOnboardingStore((s) => s.goalIds);
  const setGoalIds = useOnboardingStore((s) => s.setGoalIds);

  function toggle(id: string) {
    if (goalIds.includes(id)) {
      setGoalIds(goalIds.filter((g) => g !== id));
    } else {
      setGoalIds([...goalIds, id]);
    }
  }

  const noneSelected = goalIds.length === 0;

  return (
    <div className="space-y-5">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Chọn mục tiêu học tập của bạn. Bạn có thể chọn nhiều mục tiêu.
      </p>

      {/* 1-col on mobile, 3-col on sm+ */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {GOALS.map((goal) => {
          const isSelected = goalIds.includes(goal.id);

          return (
            <button
              key={goal.id}
              type="button"
              onClick={() => toggle(goal.id)}
              className={cn(
                "relative flex flex-col gap-2 rounded-xl border-2 p-4 text-left",
                "transition-all duration-150 hover:shadow-md active:scale-[0.98]",
                isSelected
                  ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                  : "hover:border-slate-300 dark:hover:border-slate-600",
              )}
              style={{
                borderColor: isSelected ? undefined : "var(--border)",
                backgroundColor: isSelected ? undefined : "var(--bg-card)",
              }}
            >
              {/* Check badge */}
              {isSelected && (
                <span className="absolute right-2.5 top-2.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary-600">
                  <Check className="h-3 w-3 text-white" />
                </span>
              )}

              {/* Emoji icon */}
              <span className="text-2xl leading-none" aria-hidden>
                {goal.emoji}
              </span>

              {/* Friendly title — NO course code here */}
              <span
                className={cn(
                  "pr-6 text-sm font-semibold leading-snug",
                  isSelected ? "text-primary-700 dark:text-primary-300" : "",
                )}
                style={{ color: isSelected ? undefined : "var(--text-primary)" }}
              >
                {goal.label}
              </span>

              {/* Short description */}
              <span
                className="text-xs leading-relaxed"
                style={{ color: "var(--text-muted)" }}
              >
                {goal.description}
              </span>

              {/* Course code badge */}
              <span
                className={cn(
                  "mt-1 inline-flex w-fit items-center rounded-md px-2 py-0.5 text-xs font-medium",
                  isSelected
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-800/40 dark:text-primary-300"
                    : "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
                )}
              >
                {goal.badge}
              </span>
            </button>
          );
        })}
      </div>

      <div className="pt-1">
        <button
          type="button"
          onClick={onNext}
          disabled={noneSelected}
          className={cn(
            "w-full rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-150",
            noneSelected
              ? "cursor-not-allowed bg-slate-200 text-slate-400 dark:bg-slate-700 dark:text-slate-500"
              : "bg-primary-600 text-white hover:bg-primary-700 active:scale-[0.99]",
          )}
        >
          Tiếp tục
        </button>
      </div>
    </div>
  );
}
