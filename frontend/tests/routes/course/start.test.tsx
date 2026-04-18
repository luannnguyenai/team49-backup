import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CourseStartPage from "@/app/courses/[courseSlug]/start/page";

const courseApiMock = vi.hoisted(() => ({
  start: vi.fn(),
}));

const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: {
      ...actual.courseApi,
      start: courseApiMock.start,
    },
  };
});

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
  };
});

describe("course start page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects to login when start decision requires auth", async () => {
    courseApiMock.start.mockResolvedValue({
      decision: "redirect",
      target: "/login?next=/courses/cs231n/start",
      reason: "auth_required",
    });

    render(<CourseStartPage params={{ courseSlug: "cs231n" }} />);

    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith(
        "/login?next=/courses/cs231n/start",
      );
    });
  });

  it("redirects to the canonical learning unit when learning is ready", async () => {
    courseApiMock.start.mockResolvedValue({
      decision: "redirect",
      target: "/courses/cs231n/learn/lecture-1-introduction",
      reason: "learning_ready",
    });

    render(<CourseStartPage params={{ courseSlug: "cs231n" }} />);

    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith(
        "/courses/cs231n/learn/lecture-1-introduction",
      );
    });
  });
});
