// lib/admin-api.ts
// Thin wrapper around the existing axios client for /api/admin/* endpoints.
// Reuses JWT auto-attach + refresh interceptor from lib/api.ts.

import { api } from "@/lib/api";

export type AdminOverview = {
  total_users: number;
  dau: number;
  mau: number;
  active_now: number;
  signups_7d: number;
  llm_calls_24h: number;
  avg_latency_ms: number | null;
  error_rate: number | null;
  uptime_seconds: number;
};

export type CurrentModel = {
  name: string;
  provider: string;
  fast_model: string;
};

export type ModelHealthRow = {
  id: string;
  label: string;
  provider: string;
  model: string;
  base_url?: string | null;
  is_default?: boolean;
  status: "healthy" | "degraded" | "down" | string;
  latency_ms: number | null;
  checked_at: string;
  error?: string | null;
};

export type ModelHealthResponse = {
  models: ModelHealthRow[];
};

export type AdminUserRow = {
  id: string;
  email: string;
  full_name: string;
  role: "user" | "admin";
  is_onboarded: boolean;
  created_at: string | null;
};

export type AdminUsersPage = {
  total: number;
  page: number;
  size: number;
  items: AdminUserRow[];
};

export type SignupPoint = { date: string; count: number };

export type SystemHealth = {
  cpu_pct: number | null;
  ram_pct: number | null;
  disk_pct: number | null;
  db_connections: number;
  redis_hit_rate: number | null;
  uptime_seconds: number;
  services: { name: string; status: "healthy" | "degraded" | "down" | string }[];
};

export type TrafficSummary = {
  rps_1m: number | null;
  latency_seconds: { p50: number | null; p95: number | null; p99: number | null };
  rate_4xx: number | null;
  rate_5xx: number | null;
  prometheus_url: string;
};

export type LlmStats = {
  window_hours: number;
  total_calls: number;
  errors: number;
  calls_per_hour: { hour: string; count: number }[];
  top_users: { user_id: string; count: number }[];
  tutor_latency_per_hour: {
    hour: string;
    first_status_p50_ms: number | null;
    first_status_p95_ms: number | null;
    first_answer_p50_ms: number | null;
    first_answer_p95_ms: number | null;
    sample_count: number | null;
  }[];
};

export type FeedbackTrendPoint = { date: string; positive: number; negative: number };

export type FeedbackStats = {
  total_ratings: number;
  positive: number;
  negative: number;
  positive_ratio: number | null;
  unrated_24h: number;
  trend: FeedbackTrendPoint[];
};

export type NegativeFeedbackRow = {
  id: number;
  lecture_id: string;
  question: string;
  answer: string;
  context_binding_id: string | null;
  created_at: string | null;
};

export type AdminLogSourceState = {
  status: "healthy" | "degraded" | "unavailable" | "skipped" | string;
  count: number;
  message: string | null;
};

export type AdminLogEvent = {
  id: string;
  timestamp: string | null;
  source: "app" | "access" | "cloudwatch" | "loki" | "container" | string;
  service: string;
  level: "info" | "warn" | "error" | string;
  message: string;
  request_id?: string | null;
  user_id?: string | null;
  trace_id?: string | null;
  raw: Record<string, unknown>;
};

export type AdminLogsSummary = {
  totals: {
    events: number;
    errors: number;
    warnings: number;
    services: number;
  };
  sources: Record<string, AdminLogSourceState>;
};

export type AdminLogsEventsResponse = {
  total: number;
  items: AdminLogEvent[];
  sources: Record<string, AdminLogSourceState>;
};

export const adminApi = {
  overview: () => api.get<AdminOverview>("/api/admin/stats/overview").then((r) => r.data),
  currentModel: () => api.get<CurrentModel>("/api/admin/model/current").then((r) => r.data),
  modelHealth: () => api.get<ModelHealthResponse>("/api/admin/model/health").then((r) => r.data),
  users: (page = 1, size = 20, q?: string) =>
    api
      .get<AdminUsersPage>("/api/admin/users", { params: { page, size, q } })
      .then((r) => r.data),
  signups: (days = 30) =>
    api
      .get<SignupPoint[]>("/api/admin/signups/timeseries", { params: { days } })
      .then((r) => r.data),
  llmRecent: (limit = 50) =>
    api.get<Record<string, unknown>[]>("/api/admin/llm/recent", { params: { limit } }).then((r) => r.data),
  llmStats: (hours = 24) =>
    api.get<LlmStats>("/api/admin/llm/stats", { params: { hours } }).then((r) => r.data),
  systemHealth: () => api.get<SystemHealth>("/api/admin/system/health").then((r) => r.data),
  trafficSummary: () => api.get<TrafficSummary>("/api/admin/traffic/summary").then((r) => r.data),
  feedbackStats: (days = 14) =>
    api.get<FeedbackStats>("/api/admin/feedback/stats", { params: { days } }).then((r) => r.data),
  feedbackNegative: (limit = 20) =>
    api
      .get<NegativeFeedbackRow[]>("/api/admin/feedback/recent-negative", { params: { limit } })
      .then((r) => r.data),
  logsSummary: (limit = 100) =>
    api.get<AdminLogsSummary>("/api/admin/logs/summary", { params: { limit } }).then((r) => r.data),
  logsEvents: (params?: { limit?: number; sources?: string[] }) =>
    api
      .get<AdminLogsEventsResponse>("/api/admin/logs/events", {
        params: {
          limit: params?.limit ?? 100,
          sources: params?.sources,
        },
      })
      .then((r) => r.data),
};
