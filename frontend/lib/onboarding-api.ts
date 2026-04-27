// lib/onboarding-api.ts
// API calls for onboarding goals, topics, and known-topics endpoints.

import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TopicsResponse {
  courses: Array<{
    course_id: string;
    goal_id: string | null;
    sections: Array<{
      section_id: string;
      title: string;
      units: Array<{
        unit_id: string;
        title: string;
        estimated_hours_beginner: number | null;
      }>;
    }>;
  }>;
}

export interface PriorAnalysisCandidatePayload {
  id: string;
  display_label: string;
  raw_title: string;
  unit_titles: string[];
}

export interface PriorAnalysisResponse {
  shortlisted_topic_ids: string[];
  topic_summaries?: Array<{
    id: string;
    summary: string;
    label?: string | null;
  }>;
  model_used: string;
  provider: string;
  fallback: boolean;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function saveGoals(
  goalIds: string[]
): Promise<{ goal_ids: string[]; course_ids: string[] }> {
  return api
    .post<{ goal_ids: string[]; course_ids: string[] }>("/api/users/me/onboarding/goals", {
      goal_ids: goalIds,
    })
    .then((r) => r.data);
}

export async function getTopics(goalIds: string[]): Promise<TopicsResponse> {
  const params = goalIds.map((g) => `goal=${g}`).join("&");
  return api.get<TopicsResponse>(`/api/onboarding/topics?${params}`).then((r) => r.data);
}

export async function saveKnownTopics(
  topicUnitIds: string[]
): Promise<{ saved: boolean; count: number; skip_placement: boolean }> {
  return api
    .post<{ saved: boolean; count: number; skip_placement: boolean }>(
      "/api/users/me/onboarding/known-topics",
      { topic_unit_ids: topicUnitIds },
    )
    .then((r) => r.data);
}

export async function saveExperienceLevel(
  level: "beginner" | "experienced"
): Promise<{ level: string; placement_status: string | null }> {
  return api
    .post<{ level: string; placement_status: string | null }>(
      "/api/users/me/onboarding/experience-level",
      { level },
    )
    .then((r) => r.data);
}

export async function analyzePriorProfile(payload: {
  goal_id: string;
  prior_knowledge_text: string;
  coding_experience_text: string;
  candidates: PriorAnalysisCandidatePayload[];
}): Promise<PriorAnalysisResponse> {
  return api
    .post<PriorAnalysisResponse>("/api/onboarding/prior-analysis", payload)
    .then((r) => r.data);
}
