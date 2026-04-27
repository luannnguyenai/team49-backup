"use client";
// app/onboarding/page.tsx
// Multi-step onboarding wizard.
//
// Internal step indices:
//   0  Goal selection
//   1  Experience level
//   2  Known topics      (experienced flow only)
//   3  Time / schedule
//   4  Learning method
//
// Beginner flow:    0 → 1 → 3 → 4 → submit
// Experienced flow: 0 → 1 → 2 → 3 → 4 → submit

import { Suspense, useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { Brain, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";

import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import StepGoalSelection from "@/components/onboarding/StepGoalSelection";
import StepExperienceLevel from "@/components/onboarding/StepExperienceLevel";
import StepKnownTopicsFiltered from "@/components/onboarding/StepKnownTopicsFiltered";
import StepTimeSchedule from "@/components/onboarding/StepTimeSchedule";
import StepLearningMethod from "@/components/onboarding/StepLearningMethod";

import { canonicalSectionApi } from "@/lib/api";
import { saveGoals, saveKnownTopics, saveExperienceLevel } from "@/lib/onboarding-api";
import {
  buildCanonicalAssessmentContext,
  writePendingCanonicalAssessment,
} from "@/lib/canonical-assessment-session";
import { onboardingSchema, type OnboardingFormData } from "@/lib/onboarding-schema";
import { cn } from "@/lib/utils";
import { onboardingToLearningProfile } from "@/features/learning-path/profile";
import { useLearningPathStore } from "@/features/learning-path/store";
import { useAuthStore } from "@/stores/authStore";
import { useOnboardingStore, type ExperienceLevel } from "@/stores/onboardingStore";
import type { CourseSectionDetail } from "@/types";

// ---------------------------------------------------------------------------
// Step metadata — two flows share internal indices 0-4
// ---------------------------------------------------------------------------

// Experienced: 5 steps visible
const STEPS_EXPERIENCED = [
  { title: "Mục tiêu học tập",   subtitle: "Bạn muốn học gì?" },
  { title: "Kinh nghiệm",        subtitle: "Bạn đã từng học AI/ML chưa?" },
  { title: "Kiến thức hiện tại", subtitle: "Tick những units bạn đã nắm" },
  { title: "Thời gian của bạn",  subtitle: "Lên lịch học phù hợp" },
  { title: "Phương pháp học",    subtitle: "Cách bạn học tốt nhất" },
] as const;

// Beginner: 5 visible steps (internal indices 0, 1, 3, 4 + done)
const STEPS_BEGINNER = [
  { title: "Mục tiêu học tập",  subtitle: "Bạn muốn học gì?" },
  { title: "Kinh nghiệm",       subtitle: "Bạn đã từng học AI/ML chưa?" },
  { title: "Thời gian của bạn", subtitle: "Lên lịch học phù hợp" },
  { title: "Phương pháp học",   subtitle: "Cách bạn học tốt nhất" },
  { title: "Sinh lộ trình",     subtitle: "Hoàn tất thiết lập" },
] as const;

// Maps internal step index → beginner display index (-1 = hidden/skipped)
const BEGINNER_DISPLAY_IDX: Record<number, number> = {
  0: 0,
  1: 1,
  3: 2,
  4: 3,
  // 2 is skipped for beginners
};

// Steps that use the page-level nav buttons (index 3 = TimeSchedule)
const STEPS_WITH_PAGE_NAV = new Set([3]);

// Form fields validated before advancing from each internal step
const STEP_VALIDATION_FIELDS: (keyof OnboardingFormData)[][] = [
  [],                                               // 0: GoalSelection
  [],                                               // 1: ExperienceLevel
  [],                                               // 2: KnownTopics (optional)
  ["available_hours_per_week", "target_deadline"],  // 3: required
  ["preferred_method"],                             // 4: required
];

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

function OnboardingPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { onboard, isLoading, error, clearError } = useAuthStore();
  const { goalIds, knownUnitIds, experienceLevel } = useOnboardingStore();

  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const [animKey, setAnimKey] = useState(0);

  const [sections, setSections] = useState<CourseSectionDetail[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // ── React Hook Form ───────────────────────────────────────────────────────
  const { register, handleSubmit, watch, trigger, formState: { errors } } =
    useForm<OnboardingFormData>({
      resolver: zodResolver(onboardingSchema),
      defaultValues: {
        goal_ids: [],
        known_unit_ids: [],
        desired_section_ids: [],
        selected_course_ids: [],
        available_hours_per_week: 5,
        target_deadline: "",
        preferred_method: undefined,
      },
    });

  // ── Load sections on mount ────────────────────────────────────────────────
  useEffect(() => {
    async function loadData() {
      try {
        const list = await canonicalSectionApi.list();
        const details = await Promise.all(
          list.map((s) => canonicalSectionApi.detail(s.id))
        );
        setSections(details);
      } catch {
        // keep sections empty; user can still complete the form
      } finally {
        setLoadingData(false);
      }
    }
    loadData();
  }, []);

  // ── Submit ────────────────────────────────────────────────────────────────
  const submitOnboarding = useCallback(
    async (data: OnboardingFormData) => {
      clearError();
      try {
        const next = searchParams.get("next");
        const canonicalContext = buildCanonicalAssessmentContext({
          sections,
          knownUnitIds: knownUnitIds,
          desiredSectionIds: data.desired_section_ids,
        });
        await onboard({
          ...data,
          goal_ids: goalIds,
          known_unit_ids: knownUnitIds,
          selected_course_ids: [],
        });
        if (goalIds[0]) {
          useLearningPathStore.getState().setProfile(
            onboardingToLearningProfile({
              selected_path_key: goalIds[0],
              available_hours_per_week: data.available_hours_per_week,
              preferred_method: data.preferred_method,
            }),
          );
        }
        writePendingCanonicalAssessment(canonicalContext);

        if (canonicalContext.canonicalUnitIds.length > 0) {
          router.push(
            next ? `/assessment?next=${encodeURIComponent(next)}` : "/assessment"
          );
        } else {
          router.push(next ?? "/dashboard");
        }
      } catch {
        /* error shown from store */
      }
    },
    [clearError, searchParams, sections, goalIds, knownUnitIds, onboard, router]
  );

  const onSubmit = async (data: OnboardingFormData) => {
    await submitOnboarding(data);
  };

  // ── Navigation ────────────────────────────────────────────────────────────
  const navigate = useCallback(
    (targetStep: number) => {
      clearError();
      setDirection(targetStep > step ? "forward" : "backward");
      setAnimKey((k) => k + 1);
      setStep(targetStep);
    },
    [step, clearError]
  );

  const goNext = useCallback(async () => {
    const fields = STEP_VALIDATION_FIELDS[step];
    if (fields.length > 0) {
      const valid = await trigger(fields);
      if (!valid) return;
    }
    navigate(step + 1);
  }, [step, trigger, navigate]);

  const goBack = useCallback(() => navigate(step - 1), [step, navigate]);

  // ── Derived display values ────────────────────────────────────────────────
  const isBeginner = experienceLevel === "beginner";
  const STEPS = isBeginner ? STEPS_BEGINNER : STEPS_EXPERIENCED;
  const totalSteps = STEPS.length;

  // Map internal step index to a display index for the progress bar
  const displayIdx = isBeginner
    ? (BEGINNER_DISPLAY_IDX[step] ?? 0)
    : step;

  const progressPercent = Math.round(((displayIdx + 1) / totalSteps) * 100);
  const { title, subtitle } = STEPS[displayIdx] ?? STEPS[STEPS.length - 1];

  const isFirstStep = step === 0;
  const showPageNav = STEPS_WITH_PAGE_NAV.has(step);
  const isLastFormStep = step === 4;

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
            <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
              Thiết lập lộ trình học
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Chỉ mất 2 phút để AI tạo lộ trình cá nhân hóa cho bạn.
            </p>
          </div>
        </div>

        {/* ── Progress bar ── */}
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {title}
              </span>
              <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>
                · {subtitle}
              </span>
            </div>
            <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              {displayIdx + 1} / {totalSteps}
            </span>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div
              className="h-full rounded-full bg-primary-600 transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Step dots */}
          <div className="mt-3 flex items-center justify-between">
            {STEPS.map((s, i) => (
              <div key={s.title} className="flex flex-1 items-center">
                <div
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                    "text-xs font-bold transition-all duration-300",
                    i < displayIdx
                      ? "bg-primary-600 text-white"
                      : i === displayIdx
                      ? "bg-primary-600 text-white ring-4 ring-primary-600/20"
                      : "bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500"
                  )}
                >
                  {i < displayIdx ? (
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "mx-1 h-0.5 flex-1 rounded-full transition-all duration-500",
                      i < displayIdx ? "bg-primary-600" : "bg-slate-200 dark:bg-slate-700"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Card ── */}
        <div className="card">
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {loadingData ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <LoadingSpinner size="lg" />
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Đang tải nội dung...
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)}>
              <div
                key={animKey}
                className={
                  direction === "forward" ? "animate-slide-in-right" : "animate-slide-in"
                }
              >
                {/* Step 0 — Goal selection */}
                {step === 0 && (
                  <StepGoalSelection
                    onNext={() => {
                      saveGoals(goalIds).catch(() => {});
                      navigate(1);
                    }}
                  />
                )}

                {/* Step 1 — Experience level */}
                {step === 1 && (
                  <StepExperienceLevel
                    onBack={() => navigate(0)}
                    onNext={(level: ExperienceLevel) => {
                      saveExperienceLevel(level).catch(() => {});
                      if (level === "beginner") {
                        const store = useOnboardingStore.getState();
                        store.setKnownUnitIds([]);
                        store.setSkipPlacementAssessment(true);
                        navigate(3); // skip Known Topics → go to Schedule
                      } else {
                        navigate(2);
                      }
                    }}
                  />
                )}

                {/* Step 2 — Known topics (experienced flow only) */}
                {step === 2 && (
                  <StepKnownTopicsFiltered
                    onNext={() => {
                      saveKnownTopics(knownUnitIds).catch(() => {});
                      navigate(3);
                    }}
                    onBack={() => navigate(1)}
                    onSkipAll={() => {
                      saveKnownTopics([]).catch(() => {});
                      navigate(3);
                    }}
                  />
                )}

                {/* Step 3 — Schedule */}
                {step === 3 && (
                  <StepTimeSchedule
                    register={register}
                    errors={errors}
                    watch={watch}
                    selectedCourseCount={goalIds.length}
                    totalHours={0}
                  />
                )}

                {/* Step 4 — Learning method */}
                {step === 4 && (
                  <StepLearningMethod
                    register={register}
                    watch={watch}
                    errors={errors}
                  />
                )}
              </div>

              {/* ── Page-level nav (Step 3: Schedule only) ── */}
              {showPageNav && (
                <div className={cn("mt-7 flex gap-3", isFirstStep ? "justify-end" : "justify-between")}>
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
                  <Button
                    type="button"
                    onClick={goNext}
                    rightIcon={<ChevronRight className="h-4 w-4" />}
                  >
                    Tiếp tục
                  </Button>
                </div>
              )}

              {/* ── Step 4 (Learning Method) nav ── */}
              {isLastFormStep && (
                <div className="mt-7 flex gap-3 justify-between">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={goBack}
                    leftIcon={<ChevronLeft className="h-4 w-4" />}
                  >
                    Quay lại
                  </Button>
                  <Button
                    type="button"
                    disabled={isLoading}
                    onClick={async () => {
                      const fields = STEP_VALIDATION_FIELDS[step];
                      if (fields.length > 0) {
                        const valid = await trigger(fields);
                        if (!valid) return;
                      }
                      handleSubmit(submitOnboarding)();
                    }}
                    rightIcon={<Sparkles className="h-4 w-4" />}
                  >
                    {isLoading ? "Đang xử lý..." : "Hoàn tất"}
                  </Button>
                </div>
              )}
            </form>
          )}
        </div>

        <p className="mt-4 text-center text-xs" style={{ color: "var(--text-muted)" }}>
          Bạn có thể cập nhật thông tin này bất cứ lúc nào trong phần Cài đặt.
        </p>
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <div
          className="flex min-h-screen items-center justify-center"
          style={{ backgroundColor: "var(--bg-page)" }}
        >
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <OnboardingPageInner />
    </Suspense>
  );
}
