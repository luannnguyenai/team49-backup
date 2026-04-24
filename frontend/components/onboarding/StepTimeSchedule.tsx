"use client";
// components/onboarding/StepTimeSchedule.tsx
// Step 3 — "Thời gian của bạn"
// Range slider (hours/week) + date picker + weeks-estimate preview.

import { Calendar, Clock, TrendingUp } from "lucide-react";
import type { UseFormRegister, FieldErrors, UseFormWatch } from "react-hook-form";
import { cn } from "@/lib/utils";
import type { OnboardingFormData } from "@/lib/onboarding-schema";
import type { CourseSectionDetail } from "@/types";

interface Props {
  register: UseFormRegister<OnboardingFormData>;
  errors: FieldErrors<OnboardingFormData>;
  watch: UseFormWatch<OnboardingFormData>;
  selectedSections: CourseSectionDetail[];
}

// Minimum selectable date: tomorrow
function getMinDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split("T")[0];
}

export default function StepTimeSchedule({
  register,
  errors,
  watch,
  selectedSections,
}: Props) {
  const hours = watch("available_hours_per_week") ?? 5;

  // Compute total content hours from selected sections
  const totalHours = selectedSections.reduce(
    (sum, section) =>
      sum +
      section.learning_units.reduce(
        (sectionSum, unit) => sectionSum + (unit.estimated_hours_beginner ?? 0),
        0,
      ),
    0
  );
  const weeksNeeded = hours > 0 ? Math.ceil(totalHours / hours) : null;

  return (
    <div className="space-y-6">
      {/* ── Hours per week slider ── */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <label
            className="flex items-center gap-2 text-sm font-medium"
            style={{ color: "var(--text-primary)" }}
          >
            <Clock className="h-4 w-4" style={{ color: "var(--text-secondary)" }} />
            Bạn có thể dành bao nhiêu giờ/tuần?
          </label>
          <span className="rounded-lg bg-primary-50 dark:bg-primary-900/30 px-3 py-1 text-sm font-bold text-primary-600">
            {Number(hours) % 1 === 0 ? hours : Number(hours).toFixed(1)} giờ
          </span>
        </div>

        <input
          type="range"
          min="1"
          max="20"
          step="0.5"
          className={cn(
            "h-2 w-full cursor-pointer appearance-none rounded-full",
            "bg-slate-200 dark:bg-slate-700 accent-blue-600"
          )}
          {...register("available_hours_per_week", { valueAsNumber: true })}
        />

        {/* Tick labels */}
        <div
          className="mt-1.5 flex justify-between text-xs"
          style={{ color: "var(--text-muted)" }}
        >
          {["1", "5", "10", "15", "20"].map((v) => (
            <span key={v}>{v}</span>
          ))}
        </div>

        {errors.available_hours_per_week && (
          <p className="error-msg">{errors.available_hours_per_week.message}</p>
        )}
      </div>

      {/* ── Target deadline ── */}
      <div>
        <label
          className="mb-1.5 flex items-center gap-2 text-sm font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          <Calendar className="h-4 w-4" style={{ color: "var(--text-secondary)" }} />
          Bạn muốn hoàn thành trước ngày nào?
        </label>

        <input
          type="date"
          min={getMinDate()}
          className={cn("input-base", errors.target_deadline && "error")}
          {...register("target_deadline")}
        />

        {errors.target_deadline && (
          <p className="error-msg">{errors.target_deadline.message}</p>
        )}
      </div>

      {/* ── Estimate preview ── */}
      {selectedSections.length > 0 && weeksNeeded !== null && (
        <div className="rounded-xl border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20 p-4">
          <div className="flex items-start gap-3">
            <TrendingUp className="mt-0.5 h-5 w-5 shrink-0 text-primary-600" />
            <div>
              <p className="text-sm font-semibold text-primary-700 dark:text-primary-300">
                Dự kiến hoàn thành
              </p>
              <p
                className="mt-1 text-sm leading-relaxed"
                style={{ color: "var(--text-secondary)" }}
              >
                Với{" "}
                <strong className="text-primary-600">
                  {Number(hours) % 1 === 0 ? hours : Number(hours).toFixed(1)} giờ/tuần
                </strong>
                , bạn cần khoảng{" "}
                <strong className="text-primary-600">{weeksNeeded} tuần</strong> để
                hoàn thành {selectedSections.length} section được chọn (
                {totalHours.toFixed(1)} giờ nội dung).
              </p>
            </div>
          </div>
        </div>
      )}

      {selectedSections.length === 0 && (
        <div
          className="rounded-xl border border-dashed p-4 text-center text-sm"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
        >
          Quay lại bước 2 để chọn sections — dự kiến thời gian sẽ xuất hiện ở đây.
        </div>
      )}
    </div>
  );
}
