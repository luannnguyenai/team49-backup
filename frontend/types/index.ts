// types/index.ts
// Global TypeScript types shared across the app

export interface User {
  id: string;
  email: string;
  full_name: string;
  available_hours_per_week: number | null;
  target_deadline: string | null; // ISO date string YYYY-MM-DD
  preferred_method: "reading" | "video" | null;
  is_onboarded: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number; // seconds
}

export interface AccessToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ---- Auth request shapes ----

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface OnboardingPayload {
  known_topic_ids: string[];
  desired_module_ids: string[];
  available_hours_per_week: number;
  target_deadline: string;
  preferred_method: "reading" | "video";
}

// ---- Content API shapes ----

export interface TopicInModule {
  id: string;
  title: string;
  slug: string;
  order_index: number;
  estimated_minutes: number;
  prerequisites_count: number;
}

export interface ModuleListItem {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  order_index: number;
  topics_count: number;
}

export interface ModuleDetail extends ModuleListItem {
  topics: TopicInModule[];
}

// ---- Assessment API shapes ----

export type BloomLevel = "remember" | "understand" | "apply" | "analyze";
export type DifficultyBucket = "easy" | "medium" | "hard";
export type SelectedAnswer = "A" | "B" | "C" | "D";
export type MasteryLevel = "novice" | "developing" | "proficient" | "mastered";

export interface QuestionForAssessment {
  id: string;
  item_id: string;
  topic_id: string;
  bloom_level: BloomLevel;
  difficulty_bucket: DifficultyBucket;
  stem_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  time_expected_seconds: number | null;
}

export interface AssessmentStartResponse {
  session_id: string;
  total_questions: number;
  questions: QuestionForAssessment[];
}

export interface AnswerInput {
  question_id: string;
  selected_answer: SelectedAnswer;
  response_time_ms: number | null;
}

export interface TopicResult {
  topic_id: string;
  topic_name: string;
  score_percent: number;
  mastery_level: MasteryLevel;
  bloom_breakdown: Record<string, string>; // e.g. {"remember": "1/1"}
  weak_kcs: string[];
  misconceptions_detected: string[];
}

export interface AssessmentResultResponse {
  session_id: string;
  completed_at: string;
  overall_score_percent: number;
  topic_results: TopicResult[];
}

// ---- API error shape ----

export interface ApiError {
  detail: string | { msg: string; type: string }[];
}

// ---- Navigation ----

export interface NavItem {
  label: string;
  href: string;
  icon: string; // Lucide icon name
  badge?: number;
}
