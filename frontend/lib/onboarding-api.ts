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
): Promise<{ saved: boolean; count: number }> {
  return api
    .post<{ saved: boolean; count: number }>("/api/users/me/onboarding/known-topics", {
      topic_unit_ids: topicUnitIds,
    })
    .then((r) => r.data);
}
