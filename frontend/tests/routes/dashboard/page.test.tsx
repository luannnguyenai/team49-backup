import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/(protected)/dashboard/page";
import {
  COMING_SOON_ITEM,
  CS224N_ITEM,
  CS231N_ITEM,
  CS231N_RECOMMENDED,
} from "@/tests/fixtures/coursePlatform";

const courseApiMock = vi.hoisted(() => ({
  catalog: vi.fn(),
}));

const historyApiMock = vi.hoisted(() => ({
  list: vi.fn(),
}));

const catalogCacheMock = vi.hoisted(() => ({
  getCachedAllCourseCatalog: vi.fn(),
  resetCachedAllCourseCatalog: vi.fn(),
}));

const authStoreMock = vi.hoisted(() => ({
  user: {
    id: "user_1",
    full_name: "Test User",
    is_onboarded: true,
  } as { id: string; full_name: string; is_onboarded: boolean } | null,
}));

const navigationMock = vi.hoisted(() => ({
  searchParams: new URLSearchParams(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: {
      ...actual.courseApi,
      catalog: courseApiMock.catalog,
    },
    historyApi: {
      ...actual.historyApi,
      list: historyApiMock.list,
    },
  };
});

vi.mock("@/stores/authStore", () => ({
  useAuthStore: (selector?: (state: unknown) => unknown) => {
    const state = { user: authStoreMock.user };
    return selector ? selector(state) : state;
  },
}));

vi.mock("@/lib/course-catalog-cache", () => ({
  getCachedAllCourseCatalog: (...args: unknown[]) => catalogCacheMock.getCachedAllCourseCatalog(...args),
  resetCachedAllCourseCatalog: () => catalogCacheMock.resetCachedAllCourseCatalog(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useSearchParams: () => navigationMock.searchParams,
  };
});

describe("dashboard search", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    catalogCacheMock.resetCachedAllCourseCatalog();
    navigationMock.searchParams = new URLSearchParams();

    const catalogResponse = {
      items: [
        CS231N_RECOMMENDED,
        CS224N_ITEM,
        {
          ...COMING_SOON_ITEM,
          title: "Upcoming AI Operations",
          short_description: "Production readiness for AI systems.",
        },
      ],
    };
    courseApiMock.catalog.mockResolvedValue(catalogResponse);
    catalogCacheMock.getCachedAllCourseCatalog.mockResolvedValue(catalogResponse);

    historyApiMock.list.mockResolvedValue({
      summary: {
        total_sessions: 0,
        completed_sessions: 0,
        avg_score: null,
        total_study_seconds: 0,
        score_trend: [],
      },
      total: 0,
      page: 1,
      page_size: 1,
      items: [],
    });
  });

  it("filters dashboard courses by the q param", async () => {
    navigationMock.searchParams = new URLSearchParams("q=language");

    render(<DashboardPage />);

    expect(await screen.findByText("Explore courses")).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("tab", { name: "All" }));

    expect(await screen.findByText(CS224N_ITEM.title)).toBeInTheDocument();
    expect(screen.queryByText(CS231N_ITEM.title)).not.toBeInTheDocument();
  });

  it("renders the dashboard filters as a segmented tablist", async () => {
    render(<DashboardPage />);

    const tablist = await screen.findByRole("tablist", { name: "Course filters" });
    expect(tablist).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "For you" })).toHaveAttribute("aria-selected", "true");
  });

  it("sets the browser tab title for the dashboard route", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(document.title).toBe("AI Learning Hub - Dashboard");
    });
  });

  it("does not show overlapping ready-state helper text for available courses", async () => {
    render(<DashboardPage />);

    fireEvent.click(await screen.findByRole("tab", { name: "Ready" }));

    expect(await screen.findByText(CS231N_ITEM.title)).toBeInTheDocument();
    expect(screen.queryByText("Ready to learn")).not.toBeInTheDocument();
    expect(screen.queryByText("Ready to start right now")).not.toBeInTheDocument();
  });

  it("renders course card progress from the catalog response", async () => {
    const catalogResponse = {
      items: [
        {
          ...CS231N_RECOMMENDED,
          progress_percent: 100,
        },
      ],
    };
    catalogCacheMock.getCachedAllCourseCatalog.mockResolvedValue(catalogResponse);

    render(<DashboardPage />);

    expect(await screen.findByText(CS231N_ITEM.title)).toBeInTheDocument();
    expect(screen.getByText("Progress: 100%")).toBeInTheDocument();
  });

  it("applies search after the active dashboard tab filter", async () => {
    navigationMock.searchParams = new URLSearchParams("q=operations");

    render(<DashboardPage />);

    fireEvent.click(await screen.findByRole("tab", { name: "Coming soon" }));

    expect(await screen.findByText("Upcoming AI Operations")).toBeInTheDocument();
    expect(screen.queryByText(CS231N_ITEM.title)).not.toBeInTheDocument();
  });

  it("shows a search-specific empty state when no course matches the query", async () => {
    navigationMock.searchParams = new URLSearchParams("q=graph rag systems");

    render(<DashboardPage />);

    expect(
      await screen.findByText(/no courses matched the keyword/i),
    ).toBeInTheDocument();
  });

  it("shows a recommendation-specific empty state on the default for-you tab", async () => {
    const catalogResponse = {
      items: [CS231N_ITEM, CS224N_ITEM],
    };
    courseApiMock.catalog.mockResolvedValue(catalogResponse);
    catalogCacheMock.getCachedAllCourseCatalog.mockResolvedValue(catalogResponse);

    render(<DashboardPage />);

    expect(
      await screen.findByText(/there are no personalized recommendations for you yet/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(CS231N_ITEM.title)).not.toBeInTheDocument();
    expect(screen.queryByText(CS224N_ITEM.title)).not.toBeInTheDocument();
  });

  it("does not show fake in-progress state for coming-soon courses", async () => {
    render(<DashboardPage />);

    fireEvent.click(await screen.findByRole("tab", { name: "Coming soon" }));

    expect(await screen.findByText("Upcoming AI Operations")).toBeInTheDocument();
    expect(screen.queryByText("In progress")).not.toBeInTheDocument();
    expect(screen.queryByText("Progress: 0%")).not.toBeInTheDocument();
    expect(screen.getByText("This course is visible before its metadata is finalized")).toBeInTheDocument();
  });
});
