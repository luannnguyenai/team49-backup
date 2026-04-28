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

export interface UserSkillSnapshot {
  label: string;
  value: number;
  level: MasteryLevel | "not_started";
}

export interface UserSkillOverview {
  skills: UserSkillSnapshot[];
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

export interface ForgotPasswordPayload {
  email: string;
  new_password: string;
}

export interface OnboardingPayload {
  goal_ids: string[];
  known_unit_ids: string[];
  desired_section_ids: string[];
  selected_course_ids: string[];
  available_hours_per_week: number;
  target_deadline: string;
  preferred_method: "reading" | "video";
}

export interface BootstrapCourse {
  id: string;
  slug: string;
  title: string;
  short_description: string;
  status: string;
  visibility: string;
  cover_image_url: string | null;
  hero_badge: string | null;
  primary_subject: string | null;
  sort_order: number;
}

export interface BootstrapCourseOption extends BootstrapCourse {
  canonical_course_id: string;
}

export interface BootstrapTopic {
  slug: string;
  module_slug: string;
  name: string;
  description: string;
  order_index: number;
  estimated_hours_beginner: number | null;
  estimated_hours_intermediate: number | null;
  estimated_hours_review: number | null;
}

export interface BootstrapTopicOption extends BootstrapTopic {
  course_slug: string | null;
  canonical_course_id: string | null;
}

export interface BootstrapTopicGroup {
  course_key: string;
  course_title: string;
  topics: BootstrapTopicOption[];
}

// ---- Content API shapes ----

export interface LearningUnitSelectionItem {
  id: string;
  canonical_unit_id?: string | null;
  title: string;
  description: string | null;
  order_index: number;
  estimated_hours_beginner: number | null;
  estimated_hours_intermediate: number | null;
}

export interface CourseSectionListItem {
  id: string;
  course_id: string;
  canonical_course_id?: string | null;
  title: string;
  description: string | null;
  order_index: number;
  prerequisite_section_ids: string[] | null;
  learning_units_count: number;
}

export interface CourseSectionDetail extends CourseSectionListItem {
  learning_units: LearningUnitSelectionItem[];
}

// ---- Assessment API shapes ----

export type BloomLevel = "remember" | "understand" | "apply" | "analyze";
export type DifficultyBucket = "easy" | "medium" | "hard";
export type SelectedAnswer = "A" | "B" | "C" | "D";
export type MasteryLevel = "not_started" | "novice" | "developing" | "proficient" | "mastered";

export interface QuestionForAssessment {
  id: string | null;
  item_id: string;
  canonical_item_id?: string | null;
  canonical_unit_id?: string | null;
  topic_id: string | null;
  bloom_level: BloomLevel | null;
  difficulty_bucket: DifficultyBucket | null;
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

export interface CanonicalAssessmentStartPayload {
  canonical_unit_ids: string[];
  assessment_depth?: "quick" | "standard" | "deep";
}

export interface AnswerInput {
  question_id?: string | null;
  canonical_item_id?: string | null;
  selected_answer: SelectedAnswer;
  response_time_ms: number | null;
}

export interface LearningUnitResult {
  learning_unit_id: string;
  learning_unit_title: string;
  score_percent: number;
  mastery_level: MasteryLevel;
  bloom_breakdown: Record<string, string>; // e.g. {"remember": "1/1"}
  weak_kcs: string[];
  misconceptions_detected: string[];
}

export interface TopicDecisionResult {
  topic_unit_id: string;
  topic_unit_name: string;
  score_pct: number;
  decision: string; // "skip" | "review" | "relearn"
  mastery_level: string;
  questions_total: number;
  questions_correct: number;
}

export interface AssessmentResultResponse {
  session_id: string;
  completed_at: string;
  overall_score_percent: number;
  learning_unit_results: LearningUnitResult[];
  topic_decisions?: TopicDecisionResult[];
}

export interface AssessmentAISummaryResponse {
  available: boolean;
  summary: string | null;
  highlights: string[];
  next_step: string | null;
  model_used: string | null;
  provider: string | null;
}

// ---- Topic content ----

export interface LearningUnitContentById {
  learning_unit_id: string;
  title: string;
  section_id: string;
  section_title: string;
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
  hero_kicker?: string | null;
  hero_badge: string | null;
  is_recommended: boolean;
  progress_percent?: number | null;
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

export interface CourseSectionSummary {
  id: string;
  course_id: string;
  course_slug: string;
  course_title: string;
  title: string;
  description: string | null;
  order_index: number;
  learning_units_count: number;
}

export interface CourseUnitListItem {
  slug: string;
  title: string;
  status: CourseStatus;
  unit_type: string;
  order_index: number;
  lecture_label?: string | null;
  is_completed?: boolean;
}

export interface LectureTocSection {
  section_number: number;
  timestamp: string;
  topic_title: string;
  detailed_summary: string;
  key_takeaways: string[];
}

export interface LectureTocResponse {
  lecture_title: string;
  table_of_contents: LectureTocSection[];
}

export interface LearningUnitSummary {
  id: string;
  slug: string;
  title: string;
  lecture_title?: string | null;
  lecture_order?: number | null;
  start_seconds?: number | null;
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

export interface LearningUnitQuizRef {
  learning_unit_id: string;
  canonical_artifact_unit_id: string | null;
  course_slug: string;
  unit_slug: string;
  title: string;
}

// ---- Quiz API shapes ----

export interface QuestionForQuiz {
  id: string;
  item_id: string;
  learning_unit_id: string;
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
  learning_unit_id: string;
  total_questions: number;
  questions: QuestionForQuiz[];
  source: string;
  checkpoint: string | null;
}

export interface InlineQuizStartPayload {
  learning_unit_id: string;
  count: number;
  source: "inline_video";
  checkpoint: "midpoint" | "end";
  exclude_item_ids: string[];
}

export interface LearningSessionInlineQuizState {
  shown?: boolean;
  active_session_id?: string | null;
  completed_session_id?: string | null;
  excluded_item_ids?: string[];
  item_ids?: string[];
  answered_item_ids?: string[];
  quiz_phase?: string | null;
}

export interface LearningSessionInlineQuizProgress {
  midpoint?: LearningSessionInlineQuizState | null;
  end?: LearningSessionInlineQuizState | null;
}

export interface LearningUnitProgressPayload {
  video_progress_s?: number | null;
  video_finished?: boolean;
  watch_percent?: number | null;
  inline_quiz?: LearningSessionInlineQuizProgress | null;
}

export interface LearningUnitProgressResponse {
  learning_unit_id: string;
  current_stage: string;
  current_progress: Record<string, unknown>;
  last_activity: string;
}

export interface ResumeStateResponse {
  resume_route: string;
  current_unit_id: string | null;
  current_stage: string | null;
  current_progress: Record<string, unknown> | null;
  last_activity: string | null;
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
  learning_unit_id: string;
  learning_unit_title: string;
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

// ---- Learning Path API shapes ----

export type PathAction =
  | "skip"
  | "quick_review"
  | "standard_learn"
  | "deep_practice"
  | "remediate";

export type PathStatus = "pending" | "in_progress" | "completed" | "skipped";

export interface PathItemResponse {
  id: string;
  learning_unit_id: string;
  learning_unit_title: string;
  section_title: string | null;
  course_id?: string | null;
  course_title?: string | null;
  course_slug?: string | null;
  unit_slug?: string | null;
  learn_href?: string | null;
  action: PathAction;
  estimated_hours: number | null;
  order_index: number;
  week_number: number | null;
  status: PathStatus;
  canonical_unit_id: string | null;
  reason_codes?: string[];
  prerequisite_gap_kp_ids?: string[];
  segment_policy?: "core" | "reference" | "hidden";
  content_type?: string | null;
  salience_score?: number | string | null;
  has_quiz_items?: boolean;
  is_worth_learning?: boolean | null;
  override_critical_kp?: boolean;
  phase_tag?: string | null;
  is_locked?: boolean;
}

export interface LearningPathResponse {
  total_units: number;
  completed_units: number;
  in_progress_units: number;
  items: PathItemResponse[];
}

export interface GeneratePathRequest {
  desired_section_ids?: string[];
  selected_course_ids?: string[];
}

export interface GeneratePathResponse {
  generated_at: string;
  total_units: number;
  total_hours: number;
  required_hours_per_week: number | null;
  warnings: string[];
  items: PathItemResponse[];
}

export interface WeekEntry {
  week: number;
  learning_units: PathItemResponse[];
  total_hours: number;
}

export interface TimelineResponse {
  total_weeks: number;
  items: WeekEntry[];
}

export interface UpdateStatusResponse {
  id: string;
  learning_unit_id: string;
  status: PathStatus;
  updated_at: string;
}

// ---- Module Test API shapes ----

export interface QuestionForModuleTest {
  id: string;
  item_id: string;
  learning_unit_id: string;
  bloom_level: BloomLevel;
  difficulty_bucket: DifficultyBucket;
  stem_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  time_expected_seconds: number | null;
}

export interface LearningUnitQuestionsGroup {
  learning_unit_id: string;
  learning_unit_title: string;
  questions: QuestionForModuleTest[];
}

export interface ModuleTestStartResponse {
  session_id: string;
  section_id: string;
  section_title: string;
  total_learning_units: number;
  total_questions: number;
  learning_units: LearningUnitQuestionsGroup[];
}

export interface ModuleTestAnswerInput {
  question_id: string;
  selected_answer: SelectedAnswer;
  response_time_ms: number | null;
}

export interface LearningUnitTestResult {
  learning_unit_id: string;
  learning_unit_title: string;
  score: string;
  score_percent: number;
  bloom_max: string | null;
  verdict: "pass" | "fail";
  weak_kcs: string[];
}

export interface ReviewLearningUnitSuggestion {
  learning_unit_id: string;
  learning_unit_title: string;
  weak_kcs: string[];
  misconceptions: string[];
  estimated_review_hours: number;
}

export interface NextSectionInfo {
  section_id: string;
  section_title: string;
}

export interface WrongAnswerDetail {
  question_id: string;
  learning_unit_id: string;
  learning_unit_title: string;
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
  section_id: string;
  section_title: string;
  total_score_percent: number;
  passed: boolean;
  per_learning_unit: LearningUnitTestResult[];
  recommended_review_units: ReviewLearningUnitSuggestion[];
  estimated_review_hours: number;
  next_section: NextSectionInfo | null;
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
  course_id: string | null;
  course_slug: string | null;
  learning_unit_id: string | null;
  section_id: string | null;
  score_percent: number | null;
  correct_count: number;
  total_questions: number;
  source: string | null;
  checkpoint: string | null;
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
  question_id: string | null;
  canonical_item_id?: string | null;
  sequence_position: number;
  learning_unit_title: string;
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
  source: string | null;
  checkpoint: string | null;
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
