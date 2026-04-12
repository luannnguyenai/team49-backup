"use client";
// components/onboarding/StepLearningMethod.tsx
// Step 4 — "Phương pháp học"
// Two large selectable cards: reading vs video.

import { BookOpen, Check, Play } from "lucide-react";
import type { UseFormRegister, UseFormWatch, FieldErrors } from "react-hook-form";
import { cn } from "@/lib/utils";
import type { OnboardingFormData } from "@/lib/onboarding-schema";

interface Props {
  register: UseFormRegister<OnboardingFormData>;
  watch: UseFormWatch<OnboardingFormData>;
  errors: FieldErrors<OnboardingFormData>;
}

const METHODS = [
  {
    value: "reading" as const,
    label: "Đọc tài liệu",
    tagline: "Markdown · Code examples · Tham chiếu nhanh",
    description:
      "Học qua văn bản có cấu trúc, code snippet thực tế và markdown được định dạng rõ ràng. Phù hợp để đọc lại nhiều lần hoặc tra cứu khi cần.",
    Icon: BookOpen,
    gradient: "from-blue-500 to-indigo-600",
    shadowColor: "shadow-blue-500/20",
  },
  {
    value: "video" as const,
    label: "Xem video",
    tagline: "Bài giảng · Minh hoạ trực quan · Demo live",
    description:
      "Học qua video bài giảng có hình ảnh minh hoạ và demo. Phù hợp nếu bạn tiếp thu tốt hơn khi nghe giải thích kết hợp với hình ảnh.",
    Icon: Play,
    gradient: "from-orange-500 to-rose-600",
    shadowColor: "shadow-orange-500/20",
  },
] as const;

export default function StepLearningMethod({ register, watch, errors }: Props) {
  const selected = watch("preferred_method");

  return (
    <div className="space-y-4">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        AI sẽ ưu tiên hiển thị loại nội dung này trong lộ trình của bạn.
      </p>

      <div className="grid grid-cols-1 gap-4">
        {METHODS.map((method) => {
          const isSelected = selected === method.value;
          const { Icon } = method;

          return (
            <label
              key={method.value}
              className={cn(
                "relative flex cursor-pointer rounded-2xl border-2 p-5",
                "transition-all duration-150 hover:shadow-lg active:scale-[0.99]",
                isSelected
                  ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                  : "hover:border-slate-300 dark:hover:border-slate-600"
              )}
              style={{
                borderColor: isSelected ? undefined : "var(--border)",
                backgroundColor: isSelected ? undefined : "var(--bg-card)",
              }}
            >
              <input
                type="radio"
                value={method.value}
                className="sr-only"
                {...register("preferred_method")}
              />

              <div className="flex w-full items-center gap-5">
                {/* Icon */}
                <div
                  className={cn(
                    "flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl",
                    "bg-gradient-to-br text-white shadow-lg",
                    method.gradient,
                    method.shadowColor
                  )}
                >
                  <Icon className="h-7 w-7" />
                </div>

                {/* Text */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p
                        className="font-semibold"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {method.label}
                      </p>
                      <p className="mt-0.5 text-xs font-medium text-primary-600 dark:text-primary-400">
                        {method.tagline}
                      </p>
                    </div>
                    {isSelected && (
                      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-600">
                        <Check className="h-3.5 w-3.5 text-white" />
                      </span>
                    )}
                  </div>
                  <p
                    className="mt-2 text-sm leading-relaxed"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {method.description}
                  </p>
                </div>
              </div>
            </label>
          );
        })}
      </div>

      {errors.preferred_method && (
        <p className="error-msg">{errors.preferred_method.message}</p>
      )}
    </div>
  );
}
