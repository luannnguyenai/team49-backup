import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProfilePage from "@/app/(protected)/profile/page";

const authApiMock = vi.hoisted(() => ({
  mySkills: vi.fn(),
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

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      mySkills: authApiMock.mySkills,
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

describe("profile page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authApiMock.mySkills.mockResolvedValue({
      skills: [],
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
      page_size: 100,
      items: [],
    });
  });

  it("sets the browser tab title for the profile route", async () => {
    render(<ProfilePage />);

    await waitFor(() => {
      expect(document.title).toBe("AI Learning Hub - Profile");
    });
  });
});
