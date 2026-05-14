import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminLogsPage from "@/app/admin/logs/page";

const adminApiMock = vi.hoisted(() => ({
  logsSummary: vi.fn(),
  logsEvents: vi.fn(),
}));

vi.mock("@/lib/admin-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/admin-api")>("@/lib/admin-api");
  return {
    ...actual,
    adminApi: {
      ...actual.adminApi,
      logsSummary: adminApiMock.logsSummary,
      logsEvents: adminApiMock.logsEvents,
    },
  };
});

describe("admin logs page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminApiMock.logsSummary.mockResolvedValue({
      totals: {
        events: 4,
        errors: 2,
        warnings: 1,
        services: 3,
      },
      sources: {
        app: { status: "healthy", count: 1, message: null },
        access: { status: "healthy", count: 1, message: null },
        cloudwatch: { status: "healthy", count: 1, message: null },
        loki: { status: "healthy", count: 1, message: null },
        container: { status: "unavailable", count: 0, message: "docker cli not available" },
      },
    });
    adminApiMock.logsEvents.mockResolvedValue({
      total: 4,
      items: [
        {
          id: "evt-0",
          timestamp: "2026-05-14T08:11:00+00:00",
          source: "cloudwatch",
          service: "a20-backend",
          level: "error",
          message: "Task stopped with exit code 1",
          raw: { logGroup: "/ecs/a20-backend" },
        },
        {
          id: "evt-1",
          timestamp: "2026-05-14T08:10:00+00:00",
          source: "access",
          service: "backend",
          level: "error",
          message: "GET /api/admin/logs 500",
          raw: { path: "/api/admin/logs", status: 500 },
        },
        {
          id: "evt-2",
          timestamp: "2026-05-14T08:09:00+00:00",
          source: "app",
          service: "backend",
          level: "info",
          message: "Tutor answer generated",
          raw: { question: "What is backprop?" },
        },
        {
          id: "evt-3",
          timestamp: "2026-05-14T08:08:00+00:00",
          source: "loki",
          service: "loki",
          level: "warn",
          message: "promtail delayed",
          raw: { stream: { source: "access" } },
        },
      ],
      sources: {
        app: { status: "healthy", count: 1, message: null },
        access: { status: "healthy", count: 1, message: null },
        cloudwatch: { status: "healthy", count: 1, message: null },
        loki: { status: "healthy", count: 1, message: null },
        container: { status: "unavailable", count: 0, message: "docker cli not available" },
      },
    });
  });

  it("renders overview counts, source states, and event detail panel", async () => {
    render(<AdminLogsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unified Log Explorer")).toBeInTheDocument();
    });

    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText(/cloudwatch · healthy/i)).toBeInTheDocument();
    expect(screen.getByText("docker cli not available")).toBeInTheDocument();
    expect(screen.getAllByText("GET /api/admin/logs 500").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByText("Tutor answer generated"));

    expect(screen.getByText("Event detail")).toBeInTheDocument();
    expect(screen.getByText(/What is backprop/)).toBeInTheDocument();
  });
});
