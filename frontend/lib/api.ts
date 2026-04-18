// lib/api.ts
// Axios instance with JWT auto-attach and 401 auto-refresh interceptor

import axios, {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import Cookies from "js-cookie";
import { buildUnauthorizedRedirectTarget } from "@/lib/auth-redirect";

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
  AnswerInput,
  AssessmentResultResponse,
  AssessmentStartResponse,
  HistoryResponse,
  LoginPayload,
  ModuleDetail,
  ModuleListItem,
  ModuleTestAnswerInput,
  ModuleTestResultResponse,
  ModuleTestStartResponse,
  CourseCatalogResponse,
  CourseCatalogView,
  CourseOverviewResponse,
  LearningUnitResponse,
  OnboardingPayload,
  QuizAnswerResponse,
  QuizCompleteResponse,
  QuizStartResponse,
  RegisterPayload,
  SelectedAnswer,
  SessionDetailResponse,
  SessionType,
  StartLearningDecisionResponse,
  TokenPair,
  TopicContent,
  User,
} from "@/types";

export const assessmentApi = {
  start: (topicIds: string[]) =>
    api
      .post<AssessmentStartResponse>("/api/assessment/start", { topic_ids: topicIds })
      .then((r) => r.data),

  submit: (sessionId: string, answers: AnswerInput[]) =>
    api
      .post<AssessmentResultResponse>(`/api/assessment/${sessionId}/submit`, { answers })
      .then((r) => r.data),

  results: (sessionId: string) =>
    api
      .get<AssessmentResultResponse>(`/api/assessment/${sessionId}/results`)
      .then((r) => r.data),
};

export const contentApi = {
  modules: () =>
    api.get<ModuleListItem[]>("/api/modules").then((r) => r.data),

  moduleDetail: (id: string) =>
    api.get<ModuleDetail>(`/api/modules/${id}`).then((r) => r.data),

  topicContent: (id: string) =>
    api.get<TopicContent>(`/api/topics/${id}/content`).then((r) => r.data),
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
    return api.get<CourseCatalogResponse>(`/api/courses${suffix}`).then((r) => r.data);
  },

  overview: (courseSlug: string) =>
    api
      .get<CourseOverviewResponse>(`/api/courses/${courseSlug}/overview`)
      .then((r) => r.data),

  start: (courseSlug: string) =>
    api
      .post<StartLearningDecisionResponse>(`/api/courses/${courseSlug}/start`)
      .then((r) => r.data),

  learningUnit: (courseSlug: string, unitSlug: string) =>
    api
      .get<LearningUnitResponse>(`/api/courses/${courseSlug}/units/${unitSlug}`)
      .then((r) => r.data),
};

export const quizApi = {
  start: (topicId: string) =>
    api.post<QuizStartResponse>("/api/quiz/start", { topic_id: topicId }).then((r) => r.data),

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
    module_id?: string;
    days?: number;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.session_type) q.set("session_type", params.session_type);
    if (params.module_id) q.set("module_id", params.module_id);
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
  start: (moduleId: string) =>
    api
      .post<ModuleTestStartResponse>("/api/module-test/start", { module_id: moduleId })
      .then((r) => r.data),

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

  refresh: (refreshToken: string) =>
    api
      .post<AccessToken>("/api/auth/refresh", { refresh_token: refreshToken })
      .then((r) => r.data),

  me: () => api.get<User>("/api/users/me").then((r) => r.data),

  onboarding: (data: OnboardingPayload) =>
    api.put<User>("/api/users/me/onboarding", data).then((r) => r.data),
};
