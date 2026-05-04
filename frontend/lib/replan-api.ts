/**
 * lib/replan-api.ts
 * -----------------
 * Typed API client for the replan production endpoints.
 *
 * POST /api/replan/analyze
 * POST /api/replan/assessment/start
 */

import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types matching backend ReplanAnalyzeResponse / ReplanAssessmentStartResponse
// ---------------------------------------------------------------------------

export type Difficulty = "easy" | "medium" | "hard" | "application";
export type DifficultyFilter = "easy" | "easy_medium" | "easy_medium_hard" | "all";

export interface ReplanAnalyzeUnit {
  canonicalUnitId: string;
  title: string;
  source: "matched_from_description" | "suggested_prerequisite";
  suggestedForTitle: string | null;
  knowledgePoints: string[];
  questionCounts: Record<Difficulty, number>;
}

export interface ReplanPrerequisiteSuggestion {
  canonicalUnitId: string;
  title: string;
  reason: string;
  depth: number;
  reviewUnit: ReplanAnalyzeUnit;
}

export interface ReplanAnalyzeResponse {
  units: ReplanAnalyzeUnit[];
  prerequisites: ReplanPrerequisiteSuggestion[];
  keywordPlanSpecificity: string;
  guardrailFlags: string[];
}

export interface ReplanAssessmentUnitPayload {
  canonicalUnitId: string;
  difficultyFilter: DifficultyFilter;
}

export interface ReplanAssessmentStartResponse {
  sessionId: string;
  totalQuestions: number;
  canonicalUnitIds: string[];
  unitNameMap: Record<string, string>;
  assessmentHref: string;
}

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

export const replanApi = {
  /**
   * Analyze a knowledge claim against the user's real current learning path.
   */
  analyze: (claim: string) =>
    api
      .post<ReplanAnalyzeResponse>("/api/replan/analyze", { claim })
      .then((r) => r.data),

  /**
   * Start a replan assessment with exact unit + difficulty filters.
   */
  startAssessment: (selectedUnits: ReplanAssessmentUnitPayload[]) =>
    api
      .post<ReplanAssessmentStartResponse>("/api/replan/assessment/start", {
        selectedUnits,
      })
      .then((r) => r.data),
};
