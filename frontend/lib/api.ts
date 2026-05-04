// lib/api.ts
// Axios instance with JWT auto-attach and 401 auto-refresh interceptor

import axios, {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import Cookies from "js-cookie";
import { buildUnauthorizedRedirectTarget } from "@/lib/auth-redirect";
import {
  buildCanonicalAssessmentStartPayload,
  mapCourseCatalogItemToSectionCard,
} from "@/lib/canonical-content";
import {
  findMockCourseOverview,
  getMockCourseStartDecision,
  mergeMockCourses,
} from "@/lib/mock-course-catalog";

// ---------------------------------------------------------------------------
// Token cookie helpers
// ---------------------------------------------------------------------------

const TOKEN_KEYS = {
  access: "al_access_token",
  refresh: "al_refresh_token",
  expiresAt: "al_token_expires_at",
} as const;

export const tokenStorage = {
  getAccess: () => Cookies.get(TOKEN_KEYS.access) ?? null,
  getRefresh: () => Cookies.get(TOKEN_KEYS.refresh) ?? null,
  getExpiresAt: (): number => Number(Cookies.get(TOKEN_KEYS.expiresAt) ?? 0),

  set(access: string, refresh: string, expiresInSeconds: number) {
    const expiresAt = Date.now() + expiresInSeconds * 1000;
    // access token in a session cookie (cleared on browser close)
    Cookies.set(TOKEN_KEYS.access, access, { sameSite: "Lax" });
    // refresh token persists 7 days
    Cookies.set(TOKEN_KEYS.refresh, refresh, {
      expires: 7,
      sameSite: "Lax",
    });
    Cookies.set(TOKEN_KEYS.expiresAt, String(expiresAt), {
      expires: 7,
      sameSite: "Lax",
    });
  },

  clear() {
    Cookies.remove(TOKEN_KEYS.access);
    Cookies.remove(TOKEN_KEYS.refresh);
    Cookies.remove(TOKEN_KEYS.expiresAt);
  },

  /** True if the access token will expire within the next 60 seconds. */
  isExpiringSoon(): boolean {
    const exp = tokenStorage.getExpiresAt();
    return exp > 0 && Date.now() >= exp - 60_000;
  },
};

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

export const api = axios.create({
  baseURL:
    typeof window !== "undefined"
      ? "" // use Next.js rewrite proxy in the browser
      : (process.env.API_INTERNAL_URL ?? "http://backend:8000"),
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

// ---------------------------------------------------------------------------
// Request interceptor: attach Bearer token
// ---------------------------------------------------------------------------

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccess();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ---------------------------------------------------------------------------
// Response interceptor: auto-refresh on 401
// ---------------------------------------------------------------------------

let _refreshPromise: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  const refreshToken = tokenStorage.getRefresh();
  if (!refreshToken) return null;

  try {
    const res = await axios.post<{
      access_token: string;
      expires_in: number;
    }>(
      "/api/auth/refresh",
      { refresh_token: refreshToken }
    );
    const { access_token, expires_in } = res.data;
    // Update stored access token only (keep existing refresh token)
    const existingRefresh = tokenStorage.getRefresh()!;
    tokenStorage.set(access_token, existingRefresh, expires_in);
    return access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      // Deduplicate concurrent refresh calls
      if (!_refreshPromise) {
        _refreshPromise = doRefresh().finally(() => {
          _refreshPromise = null;
        });
      }

      const newToken = await _refreshPromise;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }

      // Refresh failed → redirect to login
      if (typeof window !== "undefined") {
        const currentPath = `${window.location.pathname}${window.location.search}`;
        window.location.href = buildUnauthorizedRedirectTarget(currentPath);
      }
    }

    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Typed API methods consumed by the auth store
// ---------------------------------------------------------------------------

import type {
  AccessToken,
  AssessmentAISummaryResponse,
  AnswerInput,
  AssessmentResultResponse,
  AssessmentStartResponse,
  BootstrapCourse,
  BootstrapTopic,
  CanonicalAssessmentStartPayload,
  CourseCatalogItem,
  CourseSectionDetail,
  CourseSectionListItem,
  HistoryResponse,
  InlineQuizStartPayload,
  LearningUnitContentById,
  LearningUnitProgressPayload,
  LearningUnitProgressResponse,
  LoginPayload,
  ModuleTestAnswerInput,
  ModuleTestResultResponse,
  ModuleTestStartResponse,
  CourseCatalogResponse,
  CourseCatalogView,
  CourseOverviewResponse,
  CourseUnitListItem,
  LearningUnitResponse,
  LectureTocResponse,
  OnboardingPayload,
  ForgotPasswordPayload,
  QuizAnswerResponse,
  QuizCompleteResponse,
  QuizStartResponse,
  RegisterPayload,
  ResumeStateResponse,
  SelectedAnswer,
  SessionDetailResponse,
  SessionType,
  StartLearningDecisionResponse,
  TokenPair,
  TopicDecisionResult,
  User,
  UserSkillOverview,
} from "@/types";

const staticDataClient = axios.create({
  baseURL: "",
  timeout: 15_000,
});

export const assessmentApi = {
  start: (learningUnitIds: string[]) =>
    api
      .post<AssessmentStartResponse>("/api/assessment/start", { learning_unit_ids: learningUnitIds })
      .then((r) => r.data),

  submit: (sessionId: string, answers: AnswerInput[]) =>
    api
      .post<AssessmentResultResponse>(`/api/assessment/${sessionId}/submit`, { answers })
      .then((r) => r.data),

  results: (sessionId: string) =>
    api
      .get<AssessmentResultResponse>(`/api/assessment/${sessionId}/results`)
      .then((r) => r.data),

  summary: (sessionId: string) =>
    api
      .get<AssessmentAISummaryResponse>(`/api/assessment/${sessionId}/summary`, {
        timeout: 60_000,
      })
      .then((r) => r.data),

  updateTopicDecision: (sessionId: string, topicUnitId: string, userChoice: string) =>
    api
      .patch<TopicDecisionResult>("/api/assessment/topic-decision", {
        session_id: sessionId,
        topic_unit_id: topicUnitId,
        user_choice: userChoice,
      })
      .then((r) => r.data),
};

export const courseApi = {
  catalog: (params?: {
    view?: CourseCatalogView;
    includeUnavailable?: boolean;
  }) => {
    const q = new URLSearchParams();
    if (params?.view) q.set("view", params.view);
    if (params?.includeUnavailable != null) {
      q.set("include_unavailable", String(params.includeUnavailable));
    }
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return api.get<CourseCatalogResponse>(`/api/courses${suffix}`).then((r) => {
      if (params?.view === "recommended") {
        return r.data;
      }

      return mergeMockCourses(r.data);
    });
  },

  overview: (courseSlug: string) =>
    api
      .get<CourseOverviewResponse>(`/api/courses/${courseSlug}/overview`)
      .then((r) => r.data)
      .catch((err) => {
        const fallback = findMockCourseOverview(courseSlug);
        if (fallback) {
          return fallback;
        }
        return Promise.reject(err);
      }),

  start: (courseSlug: string) =>
    api
      .post<StartLearningDecisionResponse>(`/api/courses/${courseSlug}/start`)
      .then((r) => r.data)
      .catch((err) => {
        const fallback = getMockCourseStartDecision(courseSlug);
        if (fallback) {
          return fallback;
        }
        return Promise.reject(err);
      }),

  learningUnit: (courseSlug: string, unitSlug: string) =>
    api
      .get<LearningUnitResponse>(`/api/courses/${courseSlug}/units/${unitSlug}`)
      .then((r) => r.data),

  listUnits: (courseSlug: string) =>
    api
      .get<{ units: CourseUnitListItem[] }>(
        `/api/courses/${courseSlug}/units`
      )
      .then((r) => r.data.units),

  lectureToc: (courseSlug: string, lectureOrder: number) =>
    api
      .get<LectureTocResponse>(
        `/api/courses/${courseSlug}/lectures/${lectureOrder}/toc`,
      )
      .then((r) => r.data),
};

export const canonicalSectionApi = {
  list: () =>
    api
      .get<CourseSectionListItem[]>("/api/course-sections")
      .then((r) => r.data),

  detail: (id: string) =>
    api
      .get<CourseSectionDetail>(`/api/course-sections/${id}`)
      .then((r) => r.data),

  catalogCards: (params?: {
    view?: CourseCatalogView;
    includeUnavailable?: boolean;
  }) =>
    courseApi.catalog(params).then((response) =>
      response.items.map((course: CourseCatalogItem) =>
        mapCourseCatalogItemToSectionCard(course),
      ),
    ),
};

export const bootstrapDataApi = {
  courses: () =>
    staticDataClient
      .get<BootstrapCourse[]>("/data/bootstrap/courses.json")
      .then((r) => r.data),

  topics: () =>
    staticDataClient
      .get<BootstrapTopic[]>("/data/bootstrap/topics.json")
      .then((r) => r.data),
};

export const learningUnitApi = {
  contentById: (id: string) =>
    api
      .get<LearningUnitContentById>(`/api/learning-units/${id}/content`)
      .then((r) => r.data),
};

export const canonicalAssessmentApi = {
  start: (payload: CanonicalAssessmentStartPayload | string[]) =>
    api
      .post<AssessmentStartResponse>(
        "/api/assessment/start",
        Array.isArray(payload)
          ? buildCanonicalAssessmentStartPayload(payload)
          : payload,
      )
      .then((r) => r.data),
};

export const canonicalQuizApi = {
  start: (payload: string | InlineQuizStartPayload) =>
    api
      .post<QuizStartResponse>(
        "/api/quiz/start",
        typeof payload === "string" ? { learning_unit_id: payload } : payload,
      )
      .then((r) => r.data),
};

export const learningSessionApi = {
  resume: () =>
    api
      .get<ResumeStateResponse>("/api/learning-session/resume")
      .then((r) => r.data),

  updateProgress: (learningUnitId: string, payload: LearningUnitProgressPayload) =>
    api
      .put<LearningUnitProgressResponse>(
        `/api/learning-session/learning-units/${learningUnitId}/progress`,
        payload,
      )
      .then((r) => r.data),
};

export const canonicalModuleTestApi = {
  start: (sectionId: string) =>
    api
      .post<ModuleTestStartResponse>("/api/module-test/start", { section_id: sectionId })
      .then((r) => r.data),
};

export const quizApi = {
  answer: (
    sessionId: string,
    data: { question_id: string; selected_answer: SelectedAnswer; response_time_ms: number | null }
  ) =>
    api.post<QuizAnswerResponse>(`/api/quiz/${sessionId}/answer`, data).then((r) => r.data),

  complete: (sessionId: string) =>
    api.post<QuizCompleteResponse>(`/api/quiz/${sessionId}/complete`).then((r) => r.data),
};

export const historyApi = {
  list: (params: {
    session_type?: SessionType;
    section_id?: string;
    days?: number;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.session_type) q.set("session_type", params.session_type);
    if (params.section_id) q.set("section_id", params.section_id);
    if (params.days != null) q.set("days", String(params.days));
    if (params.page != null) q.set("page", String(params.page));
    if (params.page_size != null) q.set("page_size", String(params.page_size));
    return api
      .get<HistoryResponse>(`/api/history?${q.toString()}`)
      .then((r) => r.data);
  },

  detail: (sessionId: string) =>
    api
      .get<SessionDetailResponse>(`/api/history/${sessionId}/detail`)
      .then((r) => r.data),
};

export const moduleTestApi = {
  submit: (sessionId: string, answers: ModuleTestAnswerInput[]) =>
    api
      .post<ModuleTestResultResponse>(`/api/module-test/${sessionId}/submit`, { answers })
      .then((r) => r.data),

  results: (sessionId: string) =>
    api
      .get<ModuleTestResultResponse>(`/api/module-test/${sessionId}/results`)
      .then((r) => r.data),
};

export const authApi = {
  register: (data: RegisterPayload) =>
    api.post<TokenPair>("/api/auth/register", data).then((r) => r.data),

  login: (data: LoginPayload) =>
    api.post<TokenPair>("/api/auth/login", data).then((r) => r.data),

  forgotPassword: (data: ForgotPasswordPayload) =>
    api.post<{ status: string }>("/api/auth/forgot-password", data).then((r) => r.data),

  refresh: (refreshToken: string) =>
    api
      .post<AccessToken>("/api/auth/refresh", { refresh_token: refreshToken })
      .then((r) => r.data),

  me: () => api.get<User>("/api/users/me").then((r) => r.data),

  mySkills: () => api.get<UserSkillOverview>("/api/users/me/skills").then((r) => r.data),

  onboarding: (data: OnboardingPayload) =>
    api.put<User>("/api/users/me/onboarding", data).then((r) => r.data),

  logout: () => api.post("/api/auth/logout").then(() => undefined),
};
