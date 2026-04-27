"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { AssessmentDepth } from "@/stores/onboardingStore";

interface Props {
  onBack: () => void;
  onNext: () => void;
}

const DEPTH_OPTIONS: Array<{
  value: AssessmentDepth;
  label: string;
  questionCopy: string;
  levelCopy: string;
}> = [
  {
    value: "quick",
    label: "Nhanh",
    questionCopy: "tối đa 15 câu",
    levelCopy: "easy/medium",
  },
  {
    value: "standard",
    label: "Vừa",
    questionCopy: "tối đa 30 câu",
    levelCopy: "easy/medium/hard",
  },
  {
    value: "deep",
    label: "Kỹ",
    questionCopy: "tối đa 50 câu",
    levelCopy: "easy/medium/hard/application",
  },
];

export default function StepAssessmentDepth({ onBack, onNext }: Props) {
  const assessmentDepth = useOnboardingStore((s) => s.assessmentDepth);
  const setAssessmentDepth = useOnboardingStore((s) => s.setAssessmentDepth);

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Mức kiểm tra
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Chọn độ sâu placement. Số câu sẽ scale theo số cụm bạn chọn, nhưng không vượt quá giới hạn của từng mức.
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
          className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          Quay lại
        </button>
        <button
          type="button"
          onClick={onNext}
          className="rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Tiếp tục
        </button>
      </div>
    </div>
  );
}
