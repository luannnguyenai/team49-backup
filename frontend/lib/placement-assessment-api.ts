// lib/placement-assessment-api.ts
// API client for placement assessment endpoints.
// Adapts backend Pydantic shapes to frontend-friendly types.

import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Frontend-facing types (what components consume)
// ---------------------------------------------------------------------------

export interface PlacementQuestion {
  item_id: string;
  question_text: string;                 // mapped from backend stem_text
  options: Record<"A" | "B" | "C" | "D", string>; // mapped from option_a/b/c/d
  topic_unit_id: string;
}

export interface PlacementStartResponse {
  session_id: string;
  total_questions: number;
  questions: PlacementQuestion[];
  processed_unit_ids: string[];          // mapped from topic_unit_ids
  skipped_topics: string[];              // units with no items
  should_skip_step: boolean;             // true when ALL units had no items
}

export interface PlacementAnswerInput {
  item_id: string;
  selected_answer: string;              // "A" | "B" | "C" | "D"
  topic_unit_id: string;
}

export interface TopicDecision {
  topic_unit_id: string;
  decision: "skip" | "review" | "relearn";
  score_pct: number;
}

export interface PlacementSubmitResponse {
  session_id: string;
  topic_decisions: TopicDecision[];
  skipped_count: number;
  review_count: number;
  relearn_count: number;
}

export interface PlacementResultsResponse {
  results: TopicDecision[];
}

// ---------------------------------------------------------------------------
// Backend raw types (internal — not exported)
// ---------------------------------------------------------------------------

interface BackendQuestion {
  item_id: string;
  canonical_unit_id: string;
  topic_unit_id: string;
  stem_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
}

interface BackendStartResponse {
  session_id: string;
  total_questions: number;
  questions: BackendQuestion[];
  topic_unit_ids: string[];
  skipped_topics: string[];
  should_skip_step: boolean;
}

// ---------------------------------------------------------------------------
// Transformers
// ---------------------------------------------------------------------------

function toFrontendQuestion(q: BackendQuestion): PlacementQuestion {
  return {
    item_id: q.item_id,
    question_text: q.stem_text,
    options: { A: q.option_a, B: q.option_b, C: q.option_c, D: q.option_d },
    topic_unit_id: String(q.topic_unit_id),
  };
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function startPlacementAssessment(
  topicUnitIds: string[]
): Promise<PlacementStartResponse> {
  const raw = await api
    .post<BackendStartResponse>("/api/placement-assessment/start", {
      topic_unit_ids: topicUnitIds,
    })
    .then((r) => r.data);

  return {
    session_id: String(raw.session_id),
    total_questions: raw.total_questions,
    questions: raw.questions.map(toFrontendQuestion),
    processed_unit_ids: raw.topic_unit_ids.map(String),
    skipped_topics: (raw.skipped_topics ?? []).map(String),
    should_skip_step: raw.should_skip_step ?? false,
  };
}

export async function submitPlacementAssessment(req: {
  session_id: string;
  answers: PlacementAnswerInput[];
}): Promise<PlacementSubmitResponse> {
  return api
    .post<PlacementSubmitResponse>("/api/placement-assessment/submit", {
      session_id: req.session_id,
      answers: req.answers.map((a) => ({
        item_id: a.item_id,
        selected_answer: a.selected_answer,
        topic_unit_id: a.topic_unit_id,
      })),
    })
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
