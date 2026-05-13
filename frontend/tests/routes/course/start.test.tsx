import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CourseStartPage from "@/app/courses/[courseSlug]/start/page";
import { ASSESSMENT_STORAGE_KEYS } from "@/lib/canonical-assessment-session";

const courseApiMock = vi.hoisted(() => ({
  start: vi.fn(),
  listUnits: vi.fn(),
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
      listUnits: courseApiMock.listUnits,
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
    window.sessionStorage.clear();
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

  it("writes course canonical units before redirecting to assessment", async () => {
    courseApiMock.start.mockResolvedValue({
      decision: "redirect",
      target: "/assessment?next=/courses/cs231n/start",
      reason: "skill_test_required",
    });
    courseApiMock.listUnits.mockResolvedValue([
      {
        slug: "lecture-5-image-classification-with-cnns",
        title: "What convolutional networks are and why they matter",
        status: "ready",
        unit_type: "lecture",
        order_index: 5,
        canonical_unit_id: "local::lecture_5_image_classification_with_cnns::seg1",
      },
      {
        slug: "lecture-9-visualizing-and-understanding",
        title: "Object detection as classification plus localization and the R-CNN family",
        status: "ready",
        unit_type: "lecture",
        order_index: 9,
        canonical_unit_id: "local::lecture_9_visualizing_and_understanding::seg1",
      },
    ]);

    render(<CourseStartPage params={{ courseSlug: "cs231n" }} />);

    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith(
        "/assessment?next=/courses/cs231n/start",
      );
    });
    expect(
      JSON.parse(
        window.sessionStorage.getItem(ASSESSMENT_STORAGE_KEYS.canonicalUnitIds) ?? "[]",
      ),
    ).toEqual([
      "local::lecture_5_image_classification_with_cnns::seg1",
      "local::lecture_9_visualizing_and_understanding::seg1",
    ]);
    expect(
      JSON.parse(window.sessionStorage.getItem(ASSESSMENT_STORAGE_KEYS.unitNames) ?? "{}"),
    ).toEqual({
      "local::lecture_5_image_classification_with_cnns::seg1":
        "What convolutional networks are and why they matter",
      "local::lecture_9_visualizing_and_understanding::seg1":
        "Object detection as classification plus localization and the R-CNN family",
    });
  });
});
