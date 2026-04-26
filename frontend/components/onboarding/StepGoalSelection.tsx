"use client";
// components/onboarding/StepGoalSelection.tsx
// Step 1 — Goal selection (multi-select)
// Lets the user choose one or more learning goals before the main onboarding flow.

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOnboardingStore } from "@/stores/onboardingStore";

// ---------------------------------------------------------------------------
// Static data
// ---------------------------------------------------------------------------

const GOALS = [
  { id: "computer_vision", label: "Computer Vision (CS231n)" },
  { id: "nlp", label: "Natural Language Processing (CS224n)" },
  { id: "deep_learning", label: "Deep Learning (CS230)" },
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
    <div className="space-y-4">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Chọn mục tiêu học tập của bạn. Bạn có thể chọn nhiều mục tiêu.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {GOALS.map((goal) => {
          const isSelected = goalIds.includes(goal.id);

          return (
            <button
              key={goal.id}
              type="button"
              onClick={() => toggle(goal.id)}
              className={cn(
                "relative flex cursor-pointer items-center gap-3 rounded-xl border-2 p-4 text-left",
                "transition-all duration-150 hover:shadow-md active:scale-[0.98]",
                isSelected
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                  : "hover:border-slate-300 dark:hover:border-slate-600",
              )}
              style={{
                borderColor: isSelected ? undefined : "var(--border)",
                backgroundColor: isSelected ? undefined : "var(--bg-card)",
              }}
            >
              {/* Check badge */}
              {isSelected && (
                <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-blue-600">
                  <Check className="h-3 w-3 text-white" />
                </span>
              )}

              <span
                className={cn(
                  "pr-6 text-sm font-medium leading-snug",
                  isSelected
                    ? "text-blue-700 dark:text-blue-300"
                    : "",
                )}
                style={{ color: isSelected ? undefined : "var(--text-primary)" }}
              >
                {goal.label}
              </span>
            </button>
          );
        })}
      </div>

      <div className="pt-2">
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
