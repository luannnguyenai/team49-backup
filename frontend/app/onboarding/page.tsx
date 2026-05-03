"use client";
// app/onboarding/page.tsx
// Multi-step onboarding wizard.
//
// Internal step indices:
//   0  Goal selection
//   1  Experience level
//   2  Prior profile input       (experienced flow only)
//   3  AI topic confirmation     (experienced flow only)
//   4  Assessment depth          (experienced flow only)
//
// Beginner flow:    0 → 1 → submit
// Experienced flow: 0 → 1 → 2 → 3 → 4 → submit

import { Suspense, useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { Brain } from "lucide-react";

import LoadingSpinner from "@/components/ui/LoadingSpinner";
import StepGoalSelection from "@/components/onboarding/StepGoalSelection";
import StepExperienceLevel from "@/components/onboarding/StepExperienceLevel";
import StepPriorKnowledgeInput from "@/components/onboarding/StepPriorKnowledgeInput";
import StepKnownTopicsFiltered from "@/components/onboarding/StepKnownTopicsFiltered";
import StepAssessmentDepth from "@/components/onboarding/StepAssessmentDepth";
import { buildPostOnboardingHref } from "@/components/onboarding/onboardingNavigation";

import { canonicalSectionApi } from "@/lib/api";
import {
  analyzePriorProfile,
  saveGoals,
  saveKnownTopics,
  saveExperienceLevel,
} from "@/lib/onboarding-api";
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
import {
  buildPriorCandidateTopics,
  buildPriorShortlistFallback,
  mergePriorAnalysisIntoCandidates,
  selectSuggestedKnownUnitIds,
  type PlannerGoalId,
  type PriorCandidateTopic,
} from "@/components/onboarding/priorCandidateBuilder";

// ---------------------------------------------------------------------------
// Step metadata — two flows share internal indices 0-4
// ---------------------------------------------------------------------------

// Experienced: 5 steps visible
const STEPS_EXPERIENCED = [
  { title: "Learning goal", subtitle: "What do you want to study?" },
  { title: "Experience", subtitle: "Have you studied AI/ML before?" },
  { title: "Current foundation", subtitle: "Enter details for AI analysis" },
  { title: "Knowledge confirmation", subtitle: "Choose groups for placement verification" },
  { title: "Assessment depth", subtitle: "Choose the placement depth" },
] as const;

// Beginner: 2 visible steps (internal indices 0, 1)
const STEPS_BEGINNER = [
  { title: "Learning goal", subtitle: "What do you want to study?" },
  { title: "Experience", subtitle: "Have you studied AI/ML before?" },
] as const;

// Maps internal step index → beginner display index (-1 = hidden/skipped)
const BEGINNER_DISPLAY_IDX: Record<number, number> = {
  0: 0,
  1: 1,
  // 2, 3 and 4 are skipped for beginners
};

function goalFromStore(goalIds: string[]): PlannerGoalId {
  return goalIds.includes("nlp") ? "nlp" : "computer_vision";
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

function OnboardingPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { onboard, isLoading, error, clearError } = useAuthStore();
  const { goalIds, knownUnitIds, experienceLevel, assessmentDepth } = useOnboardingStore();

  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const [animKey, setAnimKey] = useState(0);

  const [sections, setSections] = useState<CourseSectionDetail[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [priorKnowledgeText, setPriorKnowledgeText] = useState("");
  const [codingExperienceText, setCodingExperienceText] = useState("");
  const [priorTopics, setPriorTopics] = useState<PriorCandidateTopic[]>([]);
  const [priorAnalysisFallback, setPriorAnalysisFallback] = useState(false);
  const [priorAnalysisModel, setPriorAnalysisModel] = useState<string | null>(null);
  const [analyzingPrior, setAnalyzingPrior] = useState(false);

  // ── React Hook Form ───────────────────────────────────────────────────────
  const { handleSubmit } =
    useForm<OnboardingFormData>({
      resolver: zodResolver(onboardingSchema),
      defaultValues: {
        goal_ids: [],
        known_unit_ids: [],
        desired_section_ids: [],
        selected_course_ids: [],
        available_hours_per_week: 5,
        target_deadline: undefined,
        preferred_method: "video",
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
        canonicalContext.assessmentDepth = assessmentDepth;
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

        router.push(
          buildPostOnboardingHref({
            hasAssessmentUnits: canonicalContext.canonicalUnitIds.length > 0,
            requestedNext: next,
          }),
        );
      } catch {
        /* error shown from store */
      }
    },
    [assessmentDepth, clearError, searchParams, sections, goalIds, knownUnitIds, onboard, router]
  );

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

  const runPriorAnalysis = useCallback(async () => {
    const selectedGoal = goalFromStore(goalIds);
    const candidateTopics = buildPriorCandidateTopics({
      goalId: selectedGoal,
      sections,
    }).confirmEligible;
    const fallbackTopics = buildPriorShortlistFallback({
      topics: candidateTopics,
      priorKnowledgeText,
      codingExperienceText,
    });

    setAnalyzingPrior(true);
    try {
      const response = await analyzePriorProfile({
        goal_id: selectedGoal,
        prior_knowledge_text: priorKnowledgeText,
        coding_experience_text: codingExperienceText,
        candidates: candidateTopics.map((topic) => ({
          id: topic.id,
          display_label: topic.displayLabel,
          raw_title: topic.rawTitle,
          unit_titles: [],
        })),
      });
      const fallbackIds = fallbackTopics.map((topic) => topic.id);
      const shortlistedIds = response.fallback
        ? [...new Set([...(response.shortlisted_topic_ids ?? []), ...fallbackIds])]
        : response.shortlisted_topic_ids ?? [];
      const analyzedTopics = mergePriorAnalysisIntoCandidates(
        candidateTopics,
        response.topic_summaries ?? [],
        shortlistedIds,
        response.fallback ? fallbackTopics : [],
      );

      setPriorTopics(analyzedTopics.length > 0 ? analyzedTopics : fallbackTopics);
      useOnboardingStore.getState().setKnownUnitIds(selectSuggestedKnownUnitIds(analyzedTopics));
      setPriorAnalysisFallback(response.fallback);
      setPriorAnalysisModel(`${response.provider}/${response.model_used}`);
    } catch {
      const fallbackIds = fallbackTopics.map((topic) => topic.id);
      const analyzedTopics = mergePriorAnalysisIntoCandidates(candidateTopics, [], fallbackIds, fallbackTopics);
      setPriorTopics(analyzedTopics.length > 0 ? analyzedTopics : fallbackTopics);
      useOnboardingStore.getState().setKnownUnitIds(selectSuggestedKnownUnitIds(analyzedTopics));
      setPriorAnalysisFallback(true);
      setPriorAnalysisModel(null);
    } finally {
      setAnalyzingPrior(false);
    }
    navigate(3);
  }, [codingExperienceText, goalIds, navigate, priorKnowledgeText, sections]);

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
              Set up your learning path
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              It only takes 2 minutes for AI to create a personalized path for you.
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
                Loading content...
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit(submitOnboarding)}>
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
                        handleSubmit(submitOnboarding)();
                      } else {
                        navigate(2);
                      }
                    }}
                  />
                )}

                {/* Step 2 — Manual prior profile input (experienced flow only) */}
                {step === 2 && (
                  <StepPriorKnowledgeInput
                    goalId={goalFromStore(goalIds)}
                    priorKnowledgeText={priorKnowledgeText}
                    codingExperienceText={codingExperienceText}
                    isAnalyzing={analyzingPrior}
                    onPriorKnowledgeChange={setPriorKnowledgeText}
                    onCodingExperienceChange={setCodingExperienceText}
                    onBack={() => navigate(1)}
                    onNext={runPriorAnalysis}
                  />
                )}

                {/* Step 3 — AI topic confirmation (experienced flow only) */}
                {step === 3 && (
                  <StepKnownTopicsFiltered
                    topics={priorTopics}
                    analysisFallback={priorAnalysisFallback}
                    modelLabel={priorAnalysisModel}
                    onNext={() => {
                      saveKnownTopics(knownUnitIds).catch(() => {});
                      navigate(4);
                    }}
                    onBack={() => navigate(2)}
                    onSkipAll={() => {
                      saveKnownTopics([]).catch(() => {});
                      navigate(4);
                    }}
                  />
                )}

                {/* Step 4 — Assessment depth (experienced flow only) */}
                {step === 4 && (
                  <StepAssessmentDepth
                    onBack={() => navigate(3)}
                    onNext={() => {
                      handleSubmit(submitOnboarding)();
                    }}
                    nextLabel="Finish"
                  />
                )}
              </div>

            </form>
          )}
        </div>

        <p className="mt-4 text-center text-xs" style={{ color: "var(--text-muted)" }}>
          You can update this information at any time in Settings.
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
