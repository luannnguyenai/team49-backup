"use client";
// app/onboarding/page.tsx
// Multi-step onboarding flow (5 steps) for new users.
// Step 1: Goal selection · Step 2: Known topics (filtered) · Step 3: Schedule · Step 4: Learning method · Step 5: Placement assessment
// On submit: PUT /api/users/me/onboarding → redirect to /assessment

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
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
import StepPlacementTest from "@/components/onboarding/StepPlacementTest";
import ResultGate from "@/components/onboarding/ResultGate";

import { bootstrapDataApi, canonicalSectionApi } from "@/lib/api";
import {
  buildBootstrapTopicsFromCanonicalSections,
  buildBootstrapTopicGroups,
  estimateSelectedCourseHours,
  normalizeBootstrapCourses,
} from "@/lib/bootstrap-onboarding";
import {
  buildCanonicalAssessmentContext,
  writePendingCanonicalAssessment,
} from "@/lib/canonical-assessment-session";
import { onboardingSchema, type OnboardingFormData } from "@/lib/onboarding-schema";
import type { TopicDecision } from "@/lib/placement-assessment-api";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import type {
  BootstrapCourseOption,
  BootstrapTopicOption,
  CourseSectionDetail,
} from "@/types";

// ---------------------------------------------------------------------------
// Step metadata — two flows share internal indices 0-6
// ---------------------------------------------------------------------------

const STEPS = [
  {
    title: "Mục tiêu học tập",
    subtitle: "Bạn muốn học gì?",
  },
  {
    title: "Kiến thức hiện tại",
    subtitle: "Tick những units bạn đã nắm",
  },
  {
    title: "Bạn muốn học gì?",
    subtitle: "Chọn khóa học bạn quan tâm",
  },
  {
    title: "Thời gian của bạn",
    subtitle: "Lên lịch học phù hợp",
  },
  {
    title: "Phương pháp học",
    subtitle: "Cách bạn học tốt nhất",
  },
  {
    title: "Đánh giá kiến thức",
    subtitle: "Kiểm tra những gì bạn đã biết",
  },
  {
    title: "Kết quả đánh giá",
    subtitle: "Xác nhận lộ trình của bạn",
  },
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
  // 2, 5, 6 are skipped for beginners
};

// Steps that use the page-level nav buttons (index 3 = TimeSchedule)
const STEPS_WITH_PAGE_NAV = new Set([3]);

// Form fields validated before advancing from each internal step
const STEP_VALIDATION_FIELDS: (keyof OnboardingFormData)[][] = [
  [],                                                // Step 0: optional
  ["selected_course_ids"],                           // Step 1: required
  ["available_hours_per_week", "target_deadline"],   // Step 2: required
  ["preferred_method"],                              // Step 3: required
];

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

function OnboardingPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { onboard, isLoading, error, clearError } = useAuthStore();
  const { goalIds, knownUnitIds, experienceLevel, skipPlacementAssessment } =
    useOnboardingStore();

  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const [animKey, setAnimKey] = useState(0);

  // UUID for the placement assessment session — generated once when Step 5 is entered
  const [placementSessionId, setPlacementSessionId] = useState<string | null>(null);
  const enteredStep5 = useRef(false);

  // Results from placement assessment — used by Step 6 (ResultGate)
  const [placementResults, setPlacementResults] = useState<TopicDecision[]>([]);

  // Content data loaded from the API
  const [canonicalSections, setCanonicalSections] = useState<CourseSectionDetail[]>([]);
  const [bootstrapCourses, setBootstrapCourses] = useState<BootstrapCourseOption[]>([]);
  const [bootstrapTopics, setBootstrapTopics] = useState<BootstrapTopicOption[]>([]);
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
      known_topic_slugs: [],
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
        const [courses, list] = await Promise.all([
          bootstrapDataApi.courses(),
          canonicalSectionApi.list(),
        ]);
        const details = await Promise.all(
          list.map((s) => canonicalSectionApi.detail(s.id))
        );
        const normalizedCourses = normalizeBootstrapCourses(courses);
        setBootstrapCourses(normalizedCourses);
        setBootstrapTopics(
          buildBootstrapTopicsFromCanonicalSections(details, normalizedCourses),
        );
        setCanonicalSections(details);
      } catch {
        // Keep bootstrap/canonical lists empty; user can still complete the form
      } finally {
        setLoadingData(false);
      }
    }
    loadData();
  }, []);

  // Generate placement session UUID once when entering step 5
  useEffect(() => {
    if (step === 5 && !enteredStep5.current) {
      enteredStep5.current = true;
      setPlacementSessionId(crypto.randomUUID());
    }
  }, [step]);

  // Derive the selected sections objects (needed for schedule estimate)
  const selectedCourseIds = watch("selected_course_ids");
  const selectedCourses = bootstrapCourses.filter((course) =>
    selectedCourseIds.includes(course.canonical_course_id)
  );
  const topicGroups = buildBootstrapTopicGroups(bootstrapTopics, bootstrapCourses);
  const topicCountsByCourseId = bootstrapTopics.reduce<Record<string, number>>((acc, topic) => {
    if (topic.canonical_course_id) {
      acc[topic.canonical_course_id] = (acc[topic.canonical_course_id] ?? 0) + 1;
    }
    return acc;
  }, {});
  const totalSelectedCourseHours = estimateSelectedCourseHours(
    bootstrapTopics,
    selectedCourseIds,
  );

  // ── Core submit (shared by placement complete/skip and direct submit) ────
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
        const selectedCourseIds = Array.from(
          new Set(
            selectedSections.map((section) => section.canonical_course_id ?? section.course_id)
          )
        );
        // Merge goal_ids and known_unit_ids from store (Steps 1 & 2 write to store, not form)
        await onboard({
          ...data,
          goal_ids: goalIds,
          known_unit_ids: knownUnitIds,
          selected_course_ids: selectedCourseIds,
        });
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
    [clearError, searchParams, sections, selectedSections, goalIds, knownUnitIds, onboard, router]
  );

  // ── Submit handler (used by Steps 2–4 form submit button) ────────────────
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
      const next = searchParams.get("next");
      const canonicalContext = buildCanonicalAssessmentContext({
        sections: canonicalSections,
        knownUnitIds: [],
        desiredSectionIds: [],
        selectedCourseIds: data.selected_course_ids,
      });
      await onboard({
        known_unit_ids: [],
        desired_section_ids: [],
        selected_course_ids: data.selected_course_ids,
        available_hours_per_week: data.available_hours_per_week,
        target_deadline: data.target_deadline,
        preferred_method: data.preferred_method,
      });
      writePendingCanonicalAssessment(canonicalContext);

      if (canonicalContext.canonicalUnitIds.length > 0) {
        const assessmentTarget = next
          ? `/assessment?next=${encodeURIComponent(next)}`
          : "/assessment";
        router.push(assessmentTarget);
      } else {
        // No units selected → nothing to assess → go straight to dashboard
        router.push(next ?? "/dashboard");
      }
    } catch {
      /* error message is shown from the store */
    }
  };

  // ── Placement callbacks (Step 5) ─────────────────────────────────────────
  const handlePlacementComplete = useCallback(
    (decisions: TopicDecision[]) => {
      // Store results and transition to Step 6 (ResultGate)
      setPlacementResults(decisions);
      navigate(6);
    },
    [navigate]
  );

  const handlePlacementSkip = useCallback(() => {
    handleSubmit(submitOnboarding)();
  }, [handleSubmit, submitOnboarding]);

  // ── ResultGate confirm (Step 6) ──────────────────────────────────────────
  const handleResultGateConfirm = useCallback(() => {
    handleSubmit(submitOnboarding)();
  }, [handleSubmit, submitOnboarding]);

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
  // Step 4 (Learning Method) is the last form step before placement/submit
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
                  <Controller
                    control={control}
                    name="known_topic_slugs"
                    render={({ field }) => (
                      <StepKnownUnits
                        topicGroups={topicGroups}
                        selectedSlugs={field.value}
                        onToggle={(slug) =>
                          field.onChange(
                            field.value.includes(slug)
                              ? field.value.filter((x) => x !== slug)
                              : [...field.value, slug]
                          )
                        }
                      />
                    )}
                  />
                )}

                {/* Step 2 — Schedule */}
                {step === 2 && (
                  <Controller
                    control={control}
                    name="selected_course_ids"
                    render={({ field }) => (
                      <StepDesiredSections
                        courses={bootstrapCourses}
                        topicCountsByCourseId={topicCountsByCourseId}
                        selectedIds={field.value}
                        onToggle={(id) =>
                          field.onChange(
                            field.value.includes(id)
                              ? field.value.filter((x) => x !== id)
                              : [...field.value, id]
                          )
                        }
                        error={errors.selected_course_ids?.message}
                      />
                    )}
                  />
                )}

                {/* Step 3 — Schedule */}
                {step === 3 && (
                  <StepTimeSchedule
                    register={register}
                    errors={errors}
                    watch={watch}
                    selectedCourseCount={selectedCourses.length}
                    totalHours={totalSelectedCourseHours}
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

                {/* Step 5 — Placement assessment (experienced flow only) */}
                {step === 5 && placementSessionId && (
                  <StepPlacementTest
                    sessionId={placementSessionId}
                    unitIds={knownUnitIds}
                    onComplete={handlePlacementComplete}
                    onSkip={handlePlacementSkip}
                  />
                )}

                {/* Step 6 — Result gate */}
                {step === 6 && (
                  <ResultGate
                    results={placementResults}
                    onConfirm={handleResultGateConfirm}
                  />
                )}
              </div>

              {/* ── Navigation buttons (only for Steps 2 and 3) ── */}
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

              {/* ── Step 4 (Learning method) nav: Back + Submit to trigger placement ── */}
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
                    onClick={async () => {
                      const fields = STEP_VALIDATION_FIELDS[step];
                      if (fields.length > 0) {
                        const valid = await trigger(fields);
                        if (!valid) return;
                      }
                      if (skipPlacementAssessment) {
                        handleSubmit(submitOnboarding)();
                      } else {
                        navigate(5);
                      }
                    }}
                    rightIcon={<Sparkles className="h-4 w-4" />}
                  >
                    Tiếp tục
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
