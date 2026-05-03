"use client";
// components/onboarding/StepGoalSelection.tsx
// Step 1 — Goal selection (single-select, planner V1 supports CV or NLP).

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOnboardingStore } from "@/stores/onboardingStore";

// ---------------------------------------------------------------------------
// Static data — goal IDs stay intent-centric; prerequisite courses are mapped server-side.
// ---------------------------------------------------------------------------

const GOALS = [
  {
    id: "computer_vision",
    label: "Computer Vision (CV)",
  },
  {
    id: "nlp",
    label: "Natural Language Processing",
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

  function select(id: string) {
    setGoalIds([id]);
  }

  const noneSelected = goalIds.length === 0;

  return (
    <div className="space-y-5">
      <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        Which direction do you want to focus on?
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {GOALS.map((goal) => {
          const isSelected = goalIds.includes(goal.id);

          return (
            <button
              key={goal.id}
              type="button"
              onClick={() => select(goal.id)}
              className={cn(
                "relative flex items-center gap-3 rounded-xl border-2 p-4 text-left",
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
              <span
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2",
                  isSelected ? "border-primary-600 bg-primary-600" : "border-slate-300",
                )}
              >
                {isSelected && <Check className="h-3 w-3 text-white" />}
              </span>

              <span
                className={cn(
                  "text-sm font-semibold leading-snug",
                  isSelected ? "text-primary-700 dark:text-primary-300" : "",
                )}
                style={{ color: isSelected ? undefined : "var(--text-primary)" }}
              >
                {goal.label}
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
          Continue
        </button>
      </div>
    </div>
  );
}
