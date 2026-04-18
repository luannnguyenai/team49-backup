import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";
import CourseOverviewPage from "@/app/courses/[courseSlug]/page";

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

describe("course catalog routes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders both demo courses on the public catalog home", async () => {
    courseApiMock.catalog.mockResolvedValue({
      items: [
        {
          id: "course_cs231n",
          slug: "cs231n",
          title: "CS231n: Deep Learning for Computer Vision",
          short_description: "Deep learning foundations for computer vision.",
          status: "ready",
          cover_image_url: "/courses/cs231n/cover.jpg",
          hero_badge: "Available now",
          is_recommended: false,
        },
        {
          id: "course_cs224n",
          slug: "cs224n",
          title: "CS224n: Natural Language Processing with Deep Learning",
          short_description: "Modern NLP systems and language modeling.",
          status: "coming_soon",
          cover_image_url: "/courses/cs224n/cover.jpg",
          hero_badge: "Coming soon",
          is_recommended: false,
        },
      ],
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("CS231n: Deep Learning for Computer Vision")).toBeInTheDocument();
    });
    expect(
      screen.getByText("CS224n: Natural Language Processing with Deep Learning"),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open overview" })).toHaveLength(2);
  });

  it("shows a startable overview for CS231n", async () => {
    courseApiMock.overview.mockResolvedValue({
      course: {
        id: "course_cs231n",
        slug: "cs231n",
        title: "CS231n: Deep Learning for Computer Vision",
        short_description: "Deep learning foundations for computer vision.",
        status: "ready",
        cover_image_url: "/courses/cs231n/cover.jpg",
        hero_badge: "Available now",
        is_recommended: false,
      },
      overview: {
        headline: "Build deep intuition for modern vision systems",
        subheadline: "Learn the path from linear classifiers to transformers.",
        summary_markdown: "Course summary...",
        learning_outcomes: ["Understand the core architecture families used in computer vision"],
        target_audience: "Learners with Python basics",
        prerequisites_summary: "Comfort with Python",
        estimated_duration_text: "18 lectures",
        structure_snapshot: { summary: "Lecture-first course" },
        cta_label: "Start learning",
      },
      entry: {
        decision: "redirect",
        target: "/courses/cs231n/start",
        reason: "learning_ready",
      },
    });

    render(<CourseOverviewPage params={{ courseSlug: "cs231n" }} />);

    await waitFor(() => {
      expect(screen.getByText("Build deep intuition for modern vision systems")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Start learning" })).toBeEnabled();
  });

  it("shows a blocked overview for CS224n", async () => {
    courseApiMock.overview.mockResolvedValue({
      course: {
        id: "course_cs224n",
        slug: "cs224n",
        title: "CS224n: Natural Language Processing with Deep Learning",
        short_description: "Modern NLP systems and language modeling.",
        status: "coming_soon",
        cover_image_url: "/courses/cs224n/cover.jpg",
        hero_badge: "Coming soon",
        is_recommended: false,
      },
      overview: {
        headline: "Explore modern NLP and language modeling workflows",
        subheadline: "Visible but blocked until metadata is ready.",
        summary_markdown: "Overview placeholder.",
        learning_outcomes: ["See the upcoming NLP curriculum in the public catalog"],
        target_audience: "Learners interested in NLP",
        prerequisites_summary: "Basic Python",
        estimated_duration_text: "Coming soon",
        structure_snapshot: { summary: "Overview only for now" },
        cta_label: "Coming soon",
      },
      entry: {
        decision: "redirect",
        target: "/courses/cs224n",
        reason: "course_unavailable",
      },
    });

    render(<CourseOverviewPage params={{ courseSlug: "cs224n" }} />);

    await waitFor(() => {
      expect(
        screen.getByText("Explore modern NLP and language modeling workflows"),
      ).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Coming soon" })).toBeDisabled();
  });
});
