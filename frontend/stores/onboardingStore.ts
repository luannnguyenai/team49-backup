// stores/onboardingStore.ts
// Zustand store for the 5-step onboarding flow with placement assessment.

import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OnboardingStep = 1 | 2 | 3 | 4 | 5 | 6;

export interface PlacementTopicResult {
  topic_unit_id: string;
  decision: "skip" | "review" | "relearn";
  score_pct: number;
}

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

export type ExperienceLevel = "beginner" | "experienced";
export type AssessmentDepth = "quick" | "standard" | "deep";

interface OnboardingState {
  currentStep: OnboardingStep;
  goalIds: string[];                    // selected goals from Step 1
  experienceLevel: ExperienceLevel | null; // selected at Step 2
  knownUnitIds: string[];               // selected known topics from Step 3 (experienced only)
  assessmentDepth: AssessmentDepth;      // placement verification length selected after prior analysis
  desiredSectionIds: string[];          // from Step 4
  weeklyHours: number | null;           // from Step 4
  learningMethod: string | null;        // from Step 5
  placementSessionId: string | null;    // UUID returned by POST /placement/start
  placementResults: PlacementTopicResult[] | null;
  skipPlacementAssessment: boolean;     // true when experienceLevel='beginner'

  // Actions
  setStep: (step: OnboardingStep) => void;
  setGoalIds: (ids: string[]) => void;
  setExperienceLevel: (level: ExperienceLevel) => void;
  setKnownUnitIds: (ids: string[]) => void;
  setAssessmentDepth: (depth: AssessmentDepth) => void;
  setDesiredSectionIds: (ids: string[]) => void;
  setWeeklyHours: (hours: number) => void;
  setLearningMethod: (method: string) => void;
  setPlacementSessionId: (id: string) => void;
  setPlacementResults: (results: PlacementTopicResult[]) => void;
  setSkipPlacementAssessment: (skip: boolean) => void;
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

const initialState = {
  currentStep: 1 as OnboardingStep,
  goalIds: [],
  experienceLevel: null as ExperienceLevel | null,
  knownUnitIds: [],
  assessmentDepth: "standard" as AssessmentDepth,
  desiredSectionIds: [],
  weeklyHours: null,
  learningMethod: null,
  placementSessionId: null,
  placementResults: null,
  skipPlacementAssessment: false,
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useOnboardingStore = create<OnboardingState>()((set) => ({
  ...initialState,

  setStep: (step) => set({ currentStep: step }),
  setGoalIds: (ids) => set({ goalIds: ids }),
  setExperienceLevel: (level) => set({ experienceLevel: level }),
  setKnownUnitIds: (ids) => set({ knownUnitIds: ids }),
  setAssessmentDepth: (depth) => set({ assessmentDepth: depth }),
  setDesiredSectionIds: (ids) => set({ desiredSectionIds: ids }),
  setWeeklyHours: (hours) => set({ weeklyHours: hours }),
  setLearningMethod: (method) => set({ learningMethod: method }),
  setPlacementSessionId: (id) => set({ placementSessionId: id }),
  setPlacementResults: (results) => set({ placementResults: results }),
  setSkipPlacementAssessment: (skip) => set({ skipPlacementAssessment: skip }),
  reset: () => set(initialState),
}));
