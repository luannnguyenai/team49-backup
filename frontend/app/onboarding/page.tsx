"use client";
// app/onboarding/page.tsx
// Multi-step onboarding flow (4 steps) for new users.
// Collects: known topics · desired modules · schedule · learning method
// On submit: PUT /api/users/me/onboarding → redirect to /assessment

import { useCallback, useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import {
  Brain,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";

import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import StepKnownTopics from "@/components/onboarding/StepKnownTopics";
import StepDesiredModules from "@/components/onboarding/StepDesiredModules";
import StepTimeSchedule from "@/components/onboarding/StepTimeSchedule";
import StepLearningMethod from "@/components/onboarding/StepLearningMethod";

import { contentApi } from "@/lib/api";
import { onboardingSchema, type OnboardingFormData } from "@/lib/onboarding-schema";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import type { ModuleDetail } from "@/types";

// ---------------------------------------------------------------------------
// Step metadata
// ---------------------------------------------------------------------------

const STEPS = [
  {
    title: "Bạn đã biết gì?",
    subtitle: "Tick những topics bạn đã nắm",
  },
  {
    title: "Bạn muốn học gì?",
    subtitle: "Chọn module bạn quan tâm",
  },
  {
    title: "Thời gian của bạn",
    subtitle: "Lên lịch học phù hợp",
  },
  {
    title: "Phương pháp học",
    subtitle: "Cách bạn học tốt nhất",
  },
] as const;

// Fields that must pass validation before advancing from each step
const STEP_VALIDATION_FIELDS: (keyof OnboardingFormData)[][] = [
  [],                                                // Step 0: optional
  ["desired_module_ids"],                            // Step 1: required
  ["available_hours_per_week", "target_deadline"],   // Step 2: required
  ["preferred_method"],                              // Step 3: required
];

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function OnboardingPage() {
  const router = useRouter();
  const { onboard, isLoading, error, clearError } = useAuthStore();

  // Current step (0-indexed) and transition direction
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const [animKey, setAnimKey] = useState(0);

  // Content data loaded from the API
  const [modules, setModules] = useState<ModuleDetail[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // ── React Hook Form ──────────────────────────────────────────────────────
  const {
    register,
    handleSubmit,
    watch,
    trigger,
    control,
    formState: { errors },
  } = useForm<OnboardingFormData>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: {
      known_topic_ids: [],
      desired_module_ids: [],
      available_hours_per_week: 5,
      target_deadline: "",
      preferred_method: undefined,
    },
  });

  // ── Load all modules + topics on mount ──────────────────────────────────
  useEffect(() => {
    async function loadData() {
      try {
        const list = await contentApi.modules();
        // Fetch each module's full detail (with topics) in parallel
        const details = await Promise.all(
          list.map((m) => contentApi.moduleDetail(m.id))
        );
        setModules(details);
      } catch {
        // On API failure: keep modules empty; user can still complete the form
      } finally {
        setLoadingData(false);
      }
    }
    loadData();
  }, []);

  // Derive the selected modules objects (needed for schedule estimate)
  const selectedModuleIds = watch("desired_module_ids");
  const selectedModules = modules.filter((m) =>
    selectedModuleIds.includes(m.id)
  );

  // ── Navigation ───────────────────────────────────────────────────────────
  const goNext = useCallback(async () => {
    const fields = STEP_VALIDATION_FIELDS[step];
    if (fields.length > 0) {
      const valid = await trigger(fields);
      if (!valid) return;
    }
    clearError();
    setDirection("forward");
    setAnimKey((k) => k + 1);
    setStep((s) => s + 1);
  }, [step, trigger, clearError]);

  const goBack = useCallback(() => {
    clearError();
    setDirection("backward");
    setAnimKey((k) => k + 1);
    setStep((s) => s - 1);
  }, [clearError]);

  // ── Submit ────────────────────────────────────────────────────────────────
  const onSubmit = async (data: OnboardingFormData) => {
    clearError();
    try {
      await onboard(data);

      // Persist selected module IDs (used by learning-path generation)
      sessionStorage.setItem("al_pending_module_ids", JSON.stringify(data.desired_module_ids));

      // Persist the specific topic IDs the user chose for mastery assessment.
      // The assessment page will test ONLY these topics (5 questions each).
      sessionStorage.setItem("al_pending_topic_ids", JSON.stringify(data.known_topic_ids));

      // Build a topic-name lookup so the assessment page can display names
      // without extra API calls.
      const topicNameMap: Record<string, string> = {};
      for (const mod of modules) {
        for (const t of mod.topics) {
          if (data.known_topic_ids.includes(t.id)) {
            topicNameMap[t.id] = t.name;
          }
        }
      }
      sessionStorage.setItem("al_pending_topic_names", JSON.stringify(topicNameMap));

      if (data.known_topic_ids.length > 0) {
        router.push("/assessment");
      } else {
        // No topics selected → nothing to assess → go straight to dashboard
        router.push("/dashboard");
      }
    } catch {
      /* error message is shown from the store */
    }
  };

  // ── Derived values ────────────────────────────────────────────────────────
  const isFirstStep = step === 0;
  const isLastStep = step === STEPS.length - 1;
  const progressPercent = Math.round(((step + 1) / STEPS.length) * 100);
  const { title, subtitle } = STEPS[step];

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen py-10 px-4"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      {/* Decorative blobs */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-primary-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-primary-400/10 blur-3xl" />
      </div>

      <div className="relative mx-auto w-full max-w-2xl">

        {/* ── Header ── */}
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/30">
            <Brain className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1
              className="text-xl font-bold"
              style={{ color: "var(--text-primary)" }}
            >
              Thiết lập lộ trình học
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Chỉ mất 2 phút để AI tạo lộ trình cá nhân hóa cho bạn.
            </p>
          </div>
        </div>

        {/* ── Progress bar ── */}
        <div className="mb-6">
          {/* Step label row */}
          <div className="mb-2 flex items-center justify-between">
            <div>
              <span
                className="text-sm font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                {title}
              </span>
              <span
                className="ml-2 text-xs"
                style={{ color: "var(--text-muted)" }}
              >
                · {subtitle}
              </span>
            </div>
            <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              {step + 1} / {STEPS.length}
            </span>
          </div>

          {/* Animated progress track */}
          <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div
              className="h-full rounded-full bg-primary-600 transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Step dots row */}
          <div className="mt-3 flex items-center justify-between">
            {STEPS.map((s, i) => (
              <div key={s.title} className="flex flex-1 items-center">
                {/* Dot */}
                <div
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                    "text-xs font-bold transition-all duration-300",
                    i < step
                      ? "bg-primary-600 text-white"
                      : i === step
                      ? "bg-primary-600 text-white ring-4 ring-primary-600/20"
                      : "bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500"
                  )}
                >
                  {i < step ? (
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                {/* Connector line (except after last dot) */}
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "mx-1 h-0.5 flex-1 rounded-full transition-all duration-500",
                      i < step
                        ? "bg-primary-600"
                        : "bg-slate-200 dark:bg-slate-700"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Card ── */}
        <div className="card">
          {/* Error banner */}
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Loading state */}
          {loadingData ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <LoadingSpinner size="lg" />
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Đang tải nội dung...
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)}>
              {/* ── Animated step content ── */}
              <div
                key={animKey}
                className={
                  direction === "forward"
                    ? "animate-slide-in-right"
                    : "animate-slide-in"
                }
              >
                {/* Step 0 — Known topics */}
                {step === 0 && (
                  <Controller
                    control={control}
                    name="known_topic_ids"
                    render={({ field }) => (
                      <StepKnownTopics
                        modules={modules}
                        selectedIds={field.value}
                        onToggle={(id) =>
                          field.onChange(
                            field.value.includes(id)
                              ? field.value.filter((x) => x !== id)
                              : [...field.value, id]
                          )
                        }
                      />
                    )}
                  />
                )}

                {/* Step 1 — Desired modules */}
                {step === 1 && (
                  <Controller
                    control={control}
                    name="desired_module_ids"
                    render={({ field }) => (
                      <StepDesiredModules
                        modules={modules}
                        selectedIds={field.value}
                        onToggle={(id) =>
                          field.onChange(
                            field.value.includes(id)
                              ? field.value.filter((x) => x !== id)
                              : [...field.value, id]
                          )
                        }
                        error={errors.desired_module_ids?.message}
                      />
                    )}
                  />
                )}

                {/* Step 2 — Schedule */}
                {step === 2 && (
                  <StepTimeSchedule
                    register={register}
                    errors={errors}
                    watch={watch}
                    selectedModules={selectedModules}
                  />
                )}

                {/* Step 3 — Learning method */}
                {step === 3 && (
                  <StepLearningMethod
                    register={register}
                    watch={watch}
                    errors={errors}
                  />
                )}
              </div>

              {/* ── Navigation buttons ── */}
              <div
                className={cn(
                  "mt-7 flex gap-3",
                  isFirstStep ? "justify-end" : "justify-between"
                )}
              >
                {!isFirstStep && (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={goBack}
                    leftIcon={<ChevronLeft className="h-4 w-4" />}
                  >
                    Quay lại
                  </Button>
                )}

                {!isLastStep ? (
                  <Button
                    type="button"
                    onClick={goNext}
                    rightIcon={<ChevronRight className="h-4 w-4" />}
                  >
                    {isFirstStep ? "Tiếp theo" : "Tiếp tục"}
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    loading={isLoading}
                    size="lg"
                    leftIcon={
                      !isLoading ? (
                        <Sparkles className="h-4 w-4" />
                      ) : undefined
                    }
                  >
                    Bắt đầu đánh giá
                  </Button>
                )}
              </div>
            </form>
          )}
        </div>

        {/* Skip link */}
        <p className="mt-4 text-center text-xs" style={{ color: "var(--text-muted)" }}>
          Bạn có thể cập nhật thông tin này bất cứ lúc nào trong phần Cài đặt.
        </p>
      </div>
    </div>
  );
}
