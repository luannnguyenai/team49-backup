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

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useSearchParams: () => navigationMock.searchParams,
  };
});

describe("dashboard search", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigationMock.searchParams = new URLSearchParams();

    courseApiMock.catalog.mockResolvedValue({
      items: [
        CS231N_RECOMMENDED,
        CS224N_ITEM,
        {
          ...COMING_SOON_ITEM,
          title: "Upcoming AI Operations",
          short_description: "Production readiness for AI systems.",
        },
      ],
    });

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

    const allButtons = await screen.findAllByRole("button", { name: "Tất cả" });
    fireEvent.click(allButtons[1]);

    expect(await screen.findByText(CS224N_ITEM.title)).toBeInTheDocument();
    expect(screen.queryByText(CS231N_ITEM.title)).not.toBeInTheDocument();
  });

  it("applies search after the active dashboard tab filter", async () => {
    navigationMock.searchParams = new URLSearchParams("q=operations");

    render(<DashboardPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Sắp ra mắt" }));

    expect(await screen.findByText("Upcoming AI Operations")).toBeInTheDocument();
    expect(screen.queryByText(CS231N_ITEM.title)).not.toBeInTheDocument();
  });

  it("shows a search-specific empty state when no course matches the query", async () => {
    navigationMock.searchParams = new URLSearchParams("q=graph rag systems");

    render(<DashboardPage />);

    expect(
      await screen.findByText(/không tìm thấy khóa học phù hợp với từ khóa/i),
    ).toBeInTheDocument();
  });
});
