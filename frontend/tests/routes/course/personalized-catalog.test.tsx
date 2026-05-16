import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";

const courseApiMock = vi.hoisted(() => ({
  catalog: vi.fn(),
  overview: vi.fn(),
  start: vi.fn(),
  learningUnit: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: courseApiMock,
  };
});

const authStoreMock = vi.hoisted(() => ({
  user: null as { id: string; full_name: string; is_onboarded: boolean } | null,
}));

vi.mock("@/stores/authStore", async () => {
  return {
    useAuthStore: (selector?: (state: unknown) => unknown) => {
      const state = { user: authStoreMock.user, logout: vi.fn() };
      return selector ? selector(state) : state;
    },
  };
});

describe("landing page catalog boundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authStoreMock.user = null;
  });

  it("does not fetch the course catalog for unauthenticated visitors", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: "Your Personal Path to Mastery" })).toBeInTheDocument();
    expect(courseApiMock.catalog).not.toHaveBeenCalled();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  it("keeps authenticated catalog behavior out of the public landing route", () => {
    authStoreMock.user = {
      id: "user_1",
      full_name: "Test User",
      is_onboarded: true,
    };

    render(<HomePage />);

    expect(screen.getByRole("heading", { name: "Your Personal Path to Mastery" })).toBeInTheDocument();
    expect(screen.queryByText("Welcome back, Test")).not.toBeInTheDocument();
    expect(courseApiMock.catalog).not.toHaveBeenCalled();
  });
});
