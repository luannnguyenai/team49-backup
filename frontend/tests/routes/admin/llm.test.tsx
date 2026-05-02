import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminLlmPage from "@/app/admin/llm/page";

const adminApiMock = vi.hoisted(() => ({
  overview: vi.fn(),
  llmStats: vi.fn(),
  llmRecent: vi.fn(),
  feedbackStats: vi.fn(),
  feedbackNegative: vi.fn(),
}));

vi.mock("@/lib/admin-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/admin-api")>("@/lib/admin-api");
  return {
    ...actual,
    adminApi: {
      ...actual.adminApi,
      overview: adminApiMock.overview,
      llmStats: adminApiMock.llmStats,
      llmRecent: adminApiMock.llmRecent,
      feedbackStats: adminApiMock.feedbackStats,
      feedbackNegative: adminApiMock.feedbackNegative,
    },
  };
});

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 960, height: 320 }}>{children}</div>
    ),
  };
});

describe("admin llm page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminApiMock.overview.mockResolvedValue({
      total_users: 42,
      dau: 7,
      mau: 21,
      signups_7d: 5,
      llm_calls_24h: 14,
      avg_latency_ms: 832.5,
      error_rate: 0.01,
      uptime_seconds: 3600,
    });
    adminApiMock.llmStats.mockResolvedValue({
      window_hours: 24,
      total_calls: 14,
      errors: 1,
      calls_per_hour: [{ hour: "2026-05-03T00:00:00+00:00", count: 4 }],
      top_users: [{ user_id: "user-1", count: 3 }],
      tutor_latency_per_hour: [
        {
          hour: "2026-05-03T00:00:00+00:00",
          first_status_p50_ms: 140,
          first_status_p95_ms: 420,
          first_answer_p50_ms: 360,
          first_answer_p95_ms: 920,
          sample_count: 6,
        },
      ],
    });
    adminApiMock.llmRecent.mockResolvedValue([]);
    adminApiMock.feedbackStats.mockResolvedValue({
      total_ratings: 2,
      positive: 1,
      negative: 1,
      positive_ratio: 0.5,
      unrated_24h: 3,
      trend: [],
    });
    adminApiMock.feedbackNegative.mockResolvedValue([]);
  });

  it("renders tutor latency KPIs and chart panel", async () => {
    render(<AdminLlmPage />);

    await waitFor(() => {
      expect(screen.getByText("Tutor streaming latency")).toBeInTheDocument();
    });

    expect(screen.getByText("First status p95")).toBeInTheDocument();
    expect(screen.getByText("420 ms")).toBeInTheDocument();
    expect(screen.getByText("First answer p95")).toBeInTheDocument();
    expect(screen.getByText("920 ms")).toBeInTheDocument();
  });
});
