export type PlannerPathKey = "computer_vision" | "nlp";

export interface LearningProfile {
  pathKey: PlannerPathKey;
  label: string;
  startCourse: string | null;
  selectedCourseIds: string[];
  weeklyHours: number | null;
  source: "onboarding" | "manual";
  topologyHash: string;
  pacingHash: string;
  generatedFromProfileHash: string;
}

export interface OnboardingLearningProfileInput {
  selected_path_key: unknown;
  available_hours_per_week: number | null;
  preferred_method?: "reading" | "video" | null;
}

function normalizeCourseId(courseId: string): string {
  const trimmed = courseId.trim();
  const lower = trimmed.toLowerCase();
  if (lower === "cs230") return "CS230";
  if (lower === "cs231n") return "CS231n";
  if (lower === "cs224n") return "CS224n";
  return trimmed;
}

function normalizeCourseIdsPreserveOrder(courseIds: string[]): string[] {
  return [...new Set(courseIds.map(normalizeCourseId).filter(Boolean))];
}

function normalizeCourseIdsForHash(courseIds: string[]): string[] {
  return normalizeCourseIdsPreserveOrder(courseIds).sort();
}

export function isPlannerPathKey(value: unknown): value is PlannerPathKey {
  return value === "computer_vision" || value === "nlp";
}

export type ProfileHashInput = Pick<
  LearningProfile,
  "source" | "pathKey" | "startCourse" | "selectedCourseIds" | "weeklyHours"
>;

export function topologyHash(profile: ProfileHashInput): string {
  return [
    profile.source,
    profile.pathKey,
    profile.startCourse ?? "none",
    normalizeCourseIdsForHash(profile.selectedCourseIds).join(","),
  ].join(":");
}

export function pacingHash(profile: ProfileHashInput): string {
  return ["weekly", profile.weeklyHours ?? "flex"].join(":");
}

export function profileHash(profile: ProfileHashInput): string {
  return topologyHash(profile);
}

function withHashes(base: ProfileHashInput & { label: string }): LearningProfile {
  const normalizedBase = {
    ...base,
    selectedCourseIds: normalizeCourseIdsPreserveOrder(base.selectedCourseIds),
    startCourse: base.startCourse ? normalizeCourseId(base.startCourse) : null,
  };
  const nextTopologyHash = topologyHash(normalizedBase);

  return {
    ...normalizedBase,
    topologyHash: nextTopologyHash,
    pacingHash: pacingHash(normalizedBase),
    generatedFromProfileHash: nextTopologyHash,
  };
}

export const SUPPORTED_LEARNING_PATHS = {
  computer_vision: {
    pathKey: "computer_vision",
    label: "Computer Vision",
    startCourse: "CS230",
    selectedCourseIds: ["CS230", "CS231n"],
  },
  nlp: {
    pathKey: "nlp",
    label: "Natural Language Processing",
    startCourse: "CS230",
    selectedCourseIds: ["CS230", "CS224n"],
  },
} as const satisfies Record<
  PlannerPathKey,
  {
    pathKey: PlannerPathKey;
    label: string;
    startCourse: string;
    selectedCourseIds: string[];
  }
>;

export function createLearningProfileForPath(
  pathKey: PlannerPathKey,
  options: {
    weeklyHours: number | null;
    source: LearningProfile["source"];
  },
): LearningProfile {
  const path = SUPPORTED_LEARNING_PATHS[pathKey];
  return withHashes({
    pathKey,
    label: path.label,
    startCourse: path.startCourse,
    selectedCourseIds: [...path.selectedCourseIds],
    weeklyHours: options.weeklyHours,
    source: options.source,
  });
}

export function onboardingToLearningProfile(input: OnboardingLearningProfileInput): LearningProfile {
  if (!isPlannerPathKey(input.selected_path_key)) {
    throw new Error("Planner V1 requires exactly one path: computer_vision or nlp");
  }

  return createLearningProfileForPath(input.selected_path_key, {
    weeklyHours: input.available_hours_per_week,
    source: "onboarding",
  });
}

export function isProfilePathStale(
  generatedTopologyHash: string | null | undefined,
  currentProfile: LearningProfile,
): boolean {
  if (!generatedTopologyHash) return false;
  return generatedTopologyHash !== currentProfile.topologyHash;
}

export function describeProfileChange(
  previousProfile: LearningProfile,
  currentProfile: LearningProfile,
): string {
  if (previousProfile.pathKey === "computer_vision" && currentProfile.pathKey === "nlp") {
    return "You are switching your learning path from Computer Vision to NLP.";
  }
  if (previousProfile.pathKey === "nlp" && currentProfile.pathKey === "computer_vision") {
    return "You are switching your learning path from NLP to Computer Vision.";
  }
  return `You are switching your learning path from ${previousProfile.label} to ${currentProfile.label}.`;
}
