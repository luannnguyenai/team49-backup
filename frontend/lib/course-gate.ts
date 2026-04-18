import type { CourseStatus, StartLearningDecisionResponse } from "@/types";

export interface CourseGateState {
  canStartLearning: boolean;
  isComingSoon: boolean;
  message: string | null;
}

export function getCourseGateState(
  courseStatus: CourseStatus,
  entry?: StartLearningDecisionResponse | null,
): CourseGateState {
  if (courseStatus === "coming_soon") {
    return {
      canStartLearning: false,
      isComingSoon: true,
      message: "This course is visible in the catalog but not open for learning yet.",
    };
  }

  if (entry?.reason === "course_unavailable") {
    return {
      canStartLearning: false,
      isComingSoon: false,
      message: "Learning is blocked until this course becomes available.",
    };
  }

  return {
    canStartLearning: true,
    isComingSoon: false,
    message: null,
  };
}

export function getEntryRedirectTarget(
  entry?: StartLearningDecisionResponse | null,
): string | null {
  return entry?.target ?? null;
}
