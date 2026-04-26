"use client";
// components/onboarding/StepExperienceLevel.tsx
// Step 2 — Experience level selection (single-select, required).
// Beginner → auto-skips Known Topics + Placement Assessment.
// Experienced → continues to Known Topics as normal.

import { cn } from "@/lib/utils";
import { useOnboardingStore, type ExperienceLevel } from "@/stores/onboardingStore";

// ---------------------------------------------------------------------------
// Static data
// ---------------------------------------------------------------------------

const OPTIONS: {
  level: ExperienceLevel;
  emoji: string;
  label: string;
  description: string;
}[] = [
  {
    level: "beginner",
    emoji: "🌱",
    label: "Bạn là người mới học AI",
    description:
      "Hệ thống sẽ sinh lộ trình từ đầu, không cần làm test đầu vào.",
  },
  {
    level: "experienced",
    emoji: "🎓",
    label: "Bạn đã có kiến thức về AI",
    description:
      "Hệ thống sẽ cho bạn chọn topic đã biết và làm test ngắn để cá nhân hóa lộ trình.",
  },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  onNext: (level: ExperienceLevel) => void;
  onBack: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function StepExperienceLevel({ onNext, onBack }: Props) {
  const experienceLevel = useOnboardingStore((s) => s.experienceLevel);
  const setExperienceLevel = useOnboardingStore((s) => s.setExperienceLevel);

  function select(level: ExperienceLevel) {
    setExperienceLevel(level);
  }

  return (
    <div className="space-y-5">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Bạn đã từng học AI/ML chưa? Chọn mức phù hợp để hệ thống cá nhân hóa lộ trình.
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {OPTIONS.map((opt) => {
          const isSelected = experienceLevel === opt.level;
          return (
            <button
              key={opt.level}
              type="button"
              onClick={() => select(opt.level)}
              className={cn(
                "flex flex-col gap-3 rounded-xl border-2 p-5 text-left",
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
              <span className="text-3xl leading-none" aria-hidden>
                {opt.emoji}
              </span>

              <span
                className={cn(
                  "text-sm font-semibold leading-snug",
                  isSelected ? "text-primary-700 dark:text-primary-300" : "",
                )}
                style={{ color: isSelected ? undefined : "var(--text-primary)" }}
              >
                {opt.label}
              </span>

              <span
                className="text-xs leading-relaxed"
                style={{ color: "var(--text-muted)" }}
              >
                {opt.description}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-3 pt-1">
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
          onClick={() => experienceLevel && onNext(experienceLevel)}
          disabled={experienceLevel === null}
          className={cn(
            "ml-auto rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-150",
            experienceLevel === null
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
