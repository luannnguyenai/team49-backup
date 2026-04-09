// lib/api.ts
// Axios instance with JWT auto-attach and 401 auto-refresh interceptor

import axios, {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import Cookies from "js-cookie";

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
      : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"),
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
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/auth/refresh`,
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
        window.location.href = "/login";
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
  LoginPayload,
  OnboardingPayload,
  RegisterPayload,
  TokenPair,
  User,
} from "@/types";

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
