import type { CourseStatus, StartLearningDecisionResponse, StartLearningReason } from "@/types";

export interface CourseGateState {
  canStartLearning: boolean;
  isComingSoon: boolean;
  requiresAuth: boolean;
  requiresSkillTest: boolean;
  message: string | null;
  redirectTarget: string | null;
}

/**
 * Evaluate the course gate state from course status and entry decision.
 *
 * US2: Now handles auth_required and skill_test_required reasons,
 * providing specific messages and redirect targets for each gate.
 */
export function getCourseGateState(
  courseStatus: CourseStatus,
  entry?: StartLearningDecisionResponse | null,
): CourseGateState {
  if (courseStatus === "coming_soon") {
    return {
      canStartLearning: false,
      isComingSoon: true,
      requiresAuth: false,
      requiresSkillTest: false,
      message: "This course is visible in the catalog but not open for learning yet.",
      redirectTarget: null,
    };
  }

  if (entry?.reason === "course_unavailable") {
    return {
      canStartLearning: false,
      isComingSoon: false,
      requiresAuth: false,
      requiresSkillTest: false,
      message: "Learning is blocked until this course becomes available.",
      redirectTarget: null,
    };
  }

  if (entry?.reason === "auth_required") {
    return {
      canStartLearning: false,
      isComingSoon: false,
      requiresAuth: true,
      requiresSkillTest: false,
      message: "Sign in to start learning this course.",
      redirectTarget: entry.target,
    };
  }

  if (entry?.reason === "skill_test_required") {
    return {
      canStartLearning: false,
      isComingSoon: false,
      requiresAuth: false,
      requiresSkillTest: true,
      message: "Complete the skill assessment to unlock this course.",
      redirectTarget: entry.target,
    };
  }

  return {
    canStartLearning: true,
    isComingSoon: false,
    requiresAuth: false,
    requiresSkillTest: false,
    message: null,
    redirectTarget: entry?.target ?? null,
  };
}

/**
 * Extract the redirect target from an entry decision.
 */
export function getEntryRedirectTarget(
  entry?: StartLearningDecisionResponse | null,
): string | null {
  return entry?.target ?? null;
}

/**
 * Determine if a start-learning reason indicates a gate that blocks learning.
 */
export function isBlockedReason(reason: StartLearningReason): boolean {
  return reason !== "learning_ready";
}
