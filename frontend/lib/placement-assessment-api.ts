// lib/placement-assessment-api.ts
// API client for placement assessment endpoints.
// Follows the same pattern as other API objects in lib/api.ts.

import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Request / Response types (match backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface PlacementStartRequest {
  session_id: string;        // UUID of planner session
  unit_ids: string[];        // canonical topic unit IDs to assess
}

export interface PlacementQuestion {
  item_id: string;
  question_text: string;
  options: Record<string, string>;   // {"A": "...", "B": "...", ...}
  topic_unit_id: string;
}

export interface PlacementStartResponse {
  session_id: string;
  questions: PlacementQuestion[];
  processed_unit_ids: string[];
}

export interface PlacementAnswerInput {
  item_id: string;
  selected_option: string;   // "A" | "B" | "C" | "D"
}

export interface PlacementSubmitRequest {
  session_id: string;
  answers: PlacementAnswerInput[];
}

export interface TopicDecision {
  topic_unit_id: string;
  decision: "skip" | "review" | "relearn";
  score_pct: number;
}

export interface PlacementSubmitResponse {
  topic_decisions: TopicDecision[];
  overall_score_pct: number;
}

export interface PlacementResultsResponse {
  results: TopicDecision[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function startPlacementAssessment(
  req: PlacementStartRequest
): Promise<PlacementStartResponse> {
  return api
    .post<PlacementStartResponse>("/api/placement-assessment/start", req)
    .then((r) => r.data);
}

export async function submitPlacementAssessment(
  req: PlacementSubmitRequest
): Promise<PlacementSubmitResponse> {
  return api
    .post<PlacementSubmitResponse>("/api/placement-assessment/submit", req)
    .then((r) => r.data);
}

export async function getPlacementResults(): Promise<PlacementResultsResponse> {
  return api
    .get<PlacementResultsResponse>("/api/placement-assessment/results")
    .then((r) => r.data);
}

export async function setTopicDecision(req: {
  topic_unit_id: string;
  user_choice: "skip" | "review";
}): Promise<void> {
  await api.patch("/api/placement-assessment/topic-decision", req);
}
