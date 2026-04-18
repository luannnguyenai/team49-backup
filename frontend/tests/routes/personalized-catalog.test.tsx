import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

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

// Mock auth store with controllable state
const authStoreMock = vi.hoisted(() => ({
  user: null as { id: string; full_name: string; is_onboarded: boolean } | null,
}));

vi.mock("@/stores/authStore", async () => {
  const { create } = await import("zustand");
  return {
    useAuthStore: (selector: (state: unknown) => unknown) =>
      selector({ user: authStoreMock.user }),
  };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const CS231N_ITEM = {
  id: "course_cs231n",
  slug: "cs231n",
  title: "CS231n: Deep Learning for Computer Vision",
  short_description: "Deep learning foundations for computer vision.",
  status: "ready" as const,
  cover_image_url: "/courses/cs231n/cover.jpg",
  hero_badge: "Available now",
  is_recommended: false,
};

const CS224N_ITEM = {
  id: "course_cs224n",
  slug: "cs224n",
  title: "CS224n: Natural Language Processing with Deep Learning",
  short_description: "Modern NLP systems and language modeling.",
  status: "coming_soon" as const,
  cover_image_url: "/courses/cs224n/cover.jpg",
  hero_badge: "Coming soon",
  is_recommended: false,
};

const CS231N_RECOMMENDED = { ...CS231N_ITEM, is_recommended: true };

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("personalized catalog (US2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authStoreMock.user = null;
  });

  it("shows only all-courses view for unauthenticated visitors (no tabs)", async () => {
    courseApiMock.catalog.mockResolvedValue({
      items: [CS231N_ITEM, CS224N_ITEM],
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("CS231n: Deep Learning for Computer Vision")).toBeInTheDocument();
    });

    // No tab buttons should exist for unauthenticated users
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("shows recommended and all-courses tabs for authenticated user with recommendations", async () => {
    authStoreMock.user = {
      id: "user_1",
      full_name: "Test User",
      is_onboarded: true,
    };

    // First call: all courses
    courseApiMock.catalog.mockImplementation(async (params: { view?: string }) => {
      if (params?.view === "recommended") {
        return { items: [CS231N_RECOMMENDED] };
      }
      return { items: [CS231N_ITEM, CS224N_ITEM] };
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(2);
    expect(tabs[0]).toHaveTextContent("Recommended for you");
    expect(tabs[1]).toHaveTextContent("All courses");
  });

  it("defaults to recommended tab when recommendations exist", async () => {
    authStoreMock.user = {
      id: "user_1",
      full_name: "Test User",
      is_onboarded: true,
    };

    courseApiMock.catalog.mockImplementation(async (params: { view?: string }) => {
      if (params?.view === "recommended") {
        return { items: [CS231N_RECOMMENDED] };
      }
      return { items: [CS231N_ITEM, CS224N_ITEM] };
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });

    // CS231n should appear (recommended)
    expect(screen.getByText("CS231n: Deep Learning for Computer Vision")).toBeInTheDocument();
  });

  it("shows all-courses view without tabs when authenticated but no recommendations", async () => {
    authStoreMock.user = {
      id: "user_1",
      full_name: "Test User",
      is_onboarded: true,
    };

    courseApiMock.catalog.mockImplementation(async (params: { view?: string }) => {
      if (params?.view === "recommended") {
        return { items: [] }; // No recommendations
      }
      return { items: [CS231N_ITEM, CS224N_ITEM] };
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("CS231n: Deep Learning for Computer Vision")).toBeInTheDocument();
    });

    // No tabs when there are no recommendations
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  it("shows personalized welcome message for authenticated users", async () => {
    authStoreMock.user = {
      id: "user_1",
      full_name: "Test User",
      is_onboarded: true,
    };

    courseApiMock.catalog.mockResolvedValue({
      items: [CS231N_ITEM, CS224N_ITEM],
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Welcome back, Test")).toBeInTheDocument();
    });
  });

  it("calls catalog API with recommended view when authenticated", async () => {
    authStoreMock.user = {
      id: "user_1",
      full_name: "Test User",
      is_onboarded: true,
    };

    courseApiMock.catalog.mockResolvedValue({
      items: [CS231N_ITEM, CS224N_ITEM],
    });

    render(<HomePage />);

    await waitFor(() => {
      // Should have been called for both 'all' and 'recommended' views
      expect(courseApiMock.catalog).toHaveBeenCalledWith(
        expect.objectContaining({ view: "all" }),
      );
      expect(courseApiMock.catalog).toHaveBeenCalledWith(
        expect.objectContaining({ view: "recommended" }),
      );
    });
  });
});
