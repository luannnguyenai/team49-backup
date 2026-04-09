"use client";
// app/onboarding/page.tsx
// Multi-step onboarding flow after first registration

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { Brain, Clock, Calendar, BookOpen, ChevronRight, Check } from "lucide-react";

import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { useAuthStore } from "@/stores/authStore";

const schema = z.object({
  available_hours_per_week: z.coerce
    .number({ invalid_type_error: "Phải là số" })
    .min(0.5, "Ít nhất 0.5 giờ/tuần")
    .max(168, "Không thể vượt quá 168 giờ/tuần"),
  target_deadline: z
    .string()
    .min(1, "Vui lòng chọn ngày")
    .refine(
      (d) => new Date(d) > new Date(),
      "Deadline phải sau ngày hôm nay"
    ),
  preferred_method: z.enum(["reading", "video"], {
    required_error: "Vui lòng chọn phương pháp",
  }),
});

type FormData = z.infer<typeof schema>;

const STEPS = ["Thông tin cá nhân", "Xác nhận"];

export default function OnboardingPage() {
  const router = useRouter();
  const { user, onboard, isLoading, error, clearError } = useAuthStore();
  const [step, setStep] = useState(0);

  const {
    register,
    handleSubmit,
    watch,
    trigger,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      available_hours_per_week: user?.available_hours_per_week ?? 5,
      target_deadline: user?.target_deadline ?? "",
      preferred_method: user?.preferred_method ?? undefined,
    },
  });

  const values = watch();

  const goNext = async () => {
    const valid = await trigger();
    if (valid) setStep(1);
  };

  const onSubmit = async (data: FormData) => {
    clearError();
    try {
      await onboard({
        known_topic_ids: [],
        desired_module_ids: [],
        available_hours_per_week: data.available_hours_per_week,
        target_deadline: data.target_deadline,
        preferred_method: data.preferred_method,
      });
      router.push("/dashboard");
    } catch {
      /* error shown below */
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      {/* Blobs */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-primary-400/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-lg">
        {/* Header */}
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/30">
            <Brain className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
              Thiết lập lộ trình học
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Chỉ mất 1 phút để AI tạo lộ trình phù hợp với bạn.
            </p>
          </div>
        </div>

        {/* Step indicator */}
        <div className="mb-6 flex items-center gap-2">
          {STEPS.map((label, i) => (
            <div key={label} className="flex flex-1 items-center gap-2">
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all ${
                  i < step
                    ? "bg-green-500 text-white"
                    : i === step
                    ? "bg-primary-600 text-white"
                    : "bg-slate-200 dark:bg-slate-700 text-slate-400"
                }`}
              >
                {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </div>
              <span
                className={`text-xs font-medium ${
                  i === step ? "text-primary-600" : ""
                }`}
                style={{ color: i === step ? undefined : "var(--text-muted)" }}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  className="h-px flex-1"
                  style={{ backgroundColor: "var(--border)" }}
                />
              )}
            </div>
          ))}
        </div>

        <div className="card animate-fade-in">
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Step 0 — form */}
          {step === 0 && (
            <div className="space-y-5">
              <Input
                label="Số giờ học mỗi tuần"
                type="number"
                step="0.5"
                min="0.5"
                max="168"
                leftElement={<Clock className="h-4 w-4" />}
                hint="Hãy thực tế nhé — AI sẽ căn chỉnh lịch cho bạn."
                error={errors.available_hours_per_week?.message}
                {...register("available_hours_per_week")}
              />
              <Input
                label="Deadline hoàn thành khoá học"
                type="date"
                leftElement={<Calendar className="h-4 w-4" />}
                error={errors.target_deadline?.message}
                {...register("target_deadline")}
              />

              <div>
                <label className="label">Phương pháp học yêu thích</label>
                <div className="grid grid-cols-2 gap-3">
                  {(["reading", "video"] as const).map((method) => {
                    const selected = values.preferred_method === method;
                    return (
                      <label
                        key={method}
                        className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 p-4 transition-all ${
                          selected
                            ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                            : "hover:border-slate-300 dark:hover:border-slate-600"
                        }`}
                        style={{ borderColor: selected ? undefined : "var(--border)" }}
                      >
                        <input
                          type="radio"
                          value={method}
                          className="sr-only"
                          {...register("preferred_method")}
                        />
                        <span className="text-2xl">
                          {method === "reading" ? "📖" : "🎥"}
                        </span>
                        <span
                          className={`text-sm font-medium ${
                            selected ? "text-primary-600" : ""
                          }`}
                          style={{ color: selected ? undefined : "var(--text-secondary)" }}
                        >
                          {method === "reading" ? "Đọc tài liệu" : "Xem video"}
                        </span>
                      </label>
                    );
                  })}
                </div>
                {errors.preferred_method && (
                  <p className="error-msg mt-2">
                    {errors.preferred_method.message}
                  </p>
                )}
              </div>

              <Button
                type="button"
                onClick={goNext}
                className="w-full"
                rightIcon={<ChevronRight className="h-4 w-4" />}
              >
                Tiếp tục
              </Button>
            </div>
          )}

          {/* Step 1 — confirm */}
          {step === 1 && (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
                Xác nhận thông tin
              </p>
              <div
                className="divide-y rounded-xl border text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                {[
                  {
                    label: "Giờ học / tuần",
                    value: `${values.available_hours_per_week} giờ`,
                  },
                  { label: "Deadline", value: values.target_deadline },
                  {
                    label: "Phương pháp",
                    value:
                      values.preferred_method === "reading"
                        ? "📖 Đọc tài liệu"
                        : "🎥 Xem video",
                  },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                    <span className="font-medium" style={{ color: "var(--text-primary)" }}>
                      {value}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setStep(0)}
                  className="flex-1"
                >
                  Quay lại
                </Button>
                <Button
                  type="submit"
                  loading={isLoading}
                  className="flex-1"
                  leftIcon={<Brain className="h-4 w-4" />}
                >
                  Tạo lộ trình
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
