"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { AssessmentDepth } from "@/stores/onboardingStore";

interface Props {
  onBack: () => void;
  onNext: () => void;
  nextLabel?: string;
  nextLoading?: boolean;
}

const DEPTH_OPTIONS: Array<{
  value: AssessmentDepth;
  label: string;
  questionCopy: string;
  levelCopy: string;
}> = [
  {
    value: "quick",
    label: "Quick",
    questionCopy: "up to 15 questions",
    levelCopy: "easy/medium",
  },
  {
    value: "standard",
    label: "Standard",
    questionCopy: "up to 30 questions",
    levelCopy: "easy/medium/hard",
  },
  {
    value: "deep",
    label: "Deep",
    questionCopy: "up to 50 questions",
    levelCopy: "easy/medium/hard/application",
  },
];

export default function StepAssessmentDepth({
  onBack,
  onNext,
  nextLabel = "Continue",
  nextLoading = false,
}: Props) {
  const assessmentDepth = useOnboardingStore((s) => s.assessmentDepth);
  const setAssessmentDepth = useOnboardingStore((s) => s.setAssessmentDepth);

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Assessment depth
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Choose the placement depth. The number of questions scales with the clusters you selected, but it will not exceed the limit for each level.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {DEPTH_OPTIONS.map((option) => {
          const isSelected = assessmentDepth === option.value;
          return (
            <button
              key={option.value}
              type="button"
              aria-label={`${option.label}: ${option.questionCopy}, level ${option.levelCopy}`}
              onClick={() => setAssessmentDepth(option.value)}
              className={cn(
                "relative rounded-xl border px-3 py-4 text-left transition-all",
                isSelected
                  ? "border-primary-600 bg-primary-50 shadow-sm dark:bg-primary-900/20"
                  : "hover:border-slate-300",
              )}
              style={{ borderColor: isSelected ? undefined : "var(--border)" }}
            >
              {isSelected && (
                <span className="absolute right-3 top-3 rounded-full bg-primary-600 p-1 text-white">
                  <Check className="h-3 w-3" />
                </span>
              )}
              <span className="block text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {option.label}
              </span>
              <span className="mt-2 block text-xs" style={{ color: "var(--text-muted)" }}>
                {option.questionCopy}
              </span>
              <span className="mt-2 block text-xs font-medium text-primary-600">
                {option.levelCopy}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-3 pt-2">
        <button
          type="button"
          onClick={onBack}
          disabled={nextLoading}
          className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          Back
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={nextLoading}
          className="rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-70"
        >
          {nextLoading ? "Saving..." : nextLabel}
        </button>
      </div>
    </div>
  );
}
