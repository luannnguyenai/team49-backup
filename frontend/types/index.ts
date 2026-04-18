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
  name: string;
  description: string | null;
  order_index: number;
  estimated_hours_beginner: number | null;
  estimated_hours_intermediate: number | null;
}

export interface ModuleListItem {
  id: string;
  name: string;
  description: string | null;
  order_index: number;
  prerequisite_module_ids: string[] | null;
  topics_count: number;
}

export interface ModuleDetail extends ModuleListItem {
  topics: TopicInModule[];
}

// ---- Assessment API shapes ----

export type BloomLevel = "remember" | "understand" | "apply" | "analyze";
export type DifficultyBucket = "easy" | "medium" | "hard";
export type SelectedAnswer = "A" | "B" | "C" | "D";
export type MasteryLevel = "not_started" | "novice" | "developing" | "proficient" | "mastered";

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

// ---- Topic content ----

export interface TopicContent {
  topic_id: string;
  topic_name: string;
  module_id: string;
  module_name: string;
  content_markdown: string | null;
  video_url: string | null;
}

// ---- Course platform API shapes ----

export type CourseStatus = "ready" | "coming_soon" | "metadata_partial";
export type CourseCatalogView = "all" | "recommended";
export type StartLearningReason =
  | "auth_required"
  | "skill_test_required"
  | "course_unavailable"
  | "learning_ready";

export interface CourseCatalogItem {
  id: string;
  slug: string;
  title: string;
  short_description: string;
  status: CourseStatus;
  cover_image_url: string | null;
  hero_badge: string | null;
  is_recommended: boolean;
}

export interface CourseCatalogResponse {
  items: CourseCatalogItem[];
}

export interface CourseOverviewContent {
  headline: string;
  subheadline: string | null;
  summary_markdown: string;
  learning_outcomes: string[];
  target_audience: string | null;
  prerequisites_summary: string | null;
  estimated_duration_text: string | null;
  structure_snapshot: Record<string, unknown> | null;
  cta_label: string | null;
}

export interface StartLearningDecisionResponse {
  decision: string;
  target: string;
  reason: StartLearningReason;
}

export interface CourseOverviewResponse {
  course: CourseCatalogItem;
  overview: CourseOverviewContent;
  entry: StartLearningDecisionResponse;
}

export interface LearningUnitCourseSummary {
  slug: string;
  title: string;
}

export interface LearningUnitSummary {
  id: string;
  slug: string;
  title: string;
  unit_type: string;
  status: CourseStatus;
  entry_mode: "text" | "video" | "hybrid";
}

export interface LearningUnitContentPayload {
  body_markdown: string | null;
  video_url: string | null;
  transcript_available: boolean;
  slides_available: boolean;
}

export interface TutorContextPayload {
  enabled: boolean;
  mode: string;
  context_binding_id: string | null;
  legacy_lecture_id?: string | null;
}

export interface LearningUnitResponse {
  course: LearningUnitCourseSummary;
  unit: LearningUnitSummary;
  content: LearningUnitContentPayload;
  tutor: TutorContextPayload;
}

// ---- Quiz API shapes ----

export interface QuestionForQuiz {
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

export interface QuizStartResponse {
  session_id: string;
  topic_id: string;
  total_questions: number;
  questions: QuestionForQuiz[];
}

export interface QuizAnswerResponse {
  is_correct: boolean;
  correct_answer: SelectedAnswer;
  explanation_text: string | null;
  questions_answered: number;
  questions_correct: number;
}

export interface QuizCompleteResponse {
  session_id: string;
  topic_id: string;
  topic_name: string;
  score: string; // e.g. "7/10"
  percent: number;
  mastery_before: number;
  mastery_after: number;
  mastery_level: MasteryLevel;
  bloom_breakdown: Record<string, string>;
  weak_kcs: string[];
  misconceptions: string[];
  time_total_seconds: number;
  avg_time_per_question: number;
  learning_path_updated: boolean;
}

// ---- Module Test API shapes ----

export interface QuestionForModuleTest {
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

export interface TopicQuestionsGroup {
  topic_id: string;
  topic_name: string;
  questions: QuestionForModuleTest[];
}

export interface ModuleTestStartResponse {
  session_id: string;
  module_id: string;
  module_name: string;
  total_topics: number;
  total_questions: number;
  topics: TopicQuestionsGroup[];
}

export interface ModuleTestAnswerInput {
  question_id: string;
  selected_answer: SelectedAnswer;
  response_time_ms: number | null;
}

export interface TopicTestResult {
  topic_id: string;
  topic_name: string;
  score: string;
  score_percent: number;
  bloom_max: string | null;
  verdict: "pass" | "fail";
  weak_kcs: string[];
}

export interface ReviewTopicSuggestion {
  topic_id: string;
  topic_name: string;
  weak_kcs: string[];
  misconceptions: string[];
  estimated_review_hours: number;
}

export interface NextModuleInfo {
  module_id: string;
  module_name: string;
}

export interface WrongAnswerDetail {
  question_id: string;
  topic_id: string;
  topic_name: string;
  stem_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  selected_answer: SelectedAnswer;
  correct_answer: SelectedAnswer;
  explanation_text: string | null;
}

export interface ModuleTestResultResponse {
  session_id: string;
  module_id: string;
  module_name: string;
  total_score_percent: number;
  passed: boolean;
  per_topic: TopicTestResult[];
  recommended_review_topics: ReviewTopicSuggestion[];
  estimated_review_hours: number;
  next_module: NextModuleInfo | null;
  wrong_answers: WrongAnswerDetail[];
}

// ---- History API shapes ----

export type SessionType = "assessment" | "quiz" | "module_test" | "practice";

export interface HistoryItem {
  session_id: string;
  session_type: SessionType;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  subject: string;
  topic_id: string | null;
  module_id: string | null;
  score_percent: number | null;
  correct_count: number;
  total_questions: number;
}

export interface ScoreTrendPoint {
  started_at: string;
  score_percent: number;
}

export interface HistorySummary {
  total_sessions: number;
  completed_sessions: number;
  avg_score: number | null;
  total_study_seconds: number;
  score_trend: ScoreTrendPoint[];
}

export interface HistoryResponse {
  summary: HistorySummary;
  total: number;
  page: number;
  page_size: number;
  items: HistoryItem[];
}

export interface QuestionInteractionDetail {
  question_id: string;
  sequence_position: number;
  topic_name: string;
  stem_text: string;
  bloom_level: BloomLevel;
  difficulty_bucket: DifficultyBucket;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  selected_answer: SelectedAnswer | null;
  correct_answer: SelectedAnswer;
  is_correct: boolean;
  response_time_ms: number | null;
  explanation_text: string | null;
}

export interface SessionDetailResponse {
  session_id: string;
  session_type: SessionType;
  bloom_breakdown: Record<string, string>;
  weak_kcs: string[];
  misconceptions: string[];
  questions: QuestionInteractionDetail[];
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
