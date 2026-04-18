import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LearningPage from "@/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page";
import type { LearningUnitResponse } from "@/types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const courseApiMock = vi.hoisted(() => ({
  catalog: vi.fn(),
  overview: vi.fn(),
  start: vi.fn(),
  learningUnit: vi.fn(),
}));

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: courseApiMock,
    api: apiMock,
  };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const LECTURE_1_UNIT: LearningUnitResponse = {
  course: {
    slug: "cs231n",
    title: "CS231n: Deep Learning for Computer Vision",
  },
  unit: {
    id: "unit_lecture_01",
    slug: "lecture-1-introduction",
    title: "Lecture 1: Introduction",
    unit_type: "lecture",
    status: "ready",
    entry_mode: "video",
  },
  content: {
    body_markdown: null,
    video_url: "/data/CS231n/videos/lecture-1.mp4",
    transcript_available: true,
    slides_available: true,
  },
  tutor: {
    enabled: true,
    mode: "in_context",
    context_binding_id: "ctx_unit_lecture_01",
  },
};

const DISABLED_TUTOR_UNIT: LearningUnitResponse = {
  course: {
    slug: "cs231n",
    title: "CS231n: Deep Learning for Computer Vision",
  },
  unit: {
    id: "unit_lecture_99",
    slug: "lecture-99-placeholder",
    title: "Lecture 99: Placeholder",
    unit_type: "lecture",
    status: "ready",
    entry_mode: "video",
  },
  content: {
    body_markdown: "Some markdown content",
    video_url: null,
    transcript_available: false,
    slides_available: false,
  },
  tutor: {
    enabled: false,
    mode: "disabled",
    context_binding_id: null,
  },
};

const CHAPTERS = [
  {
    id: 1,
    lecture_id: "cs231n_lecture_01",
    title: "Introduction",
    summary: "Opening context",
    start_time: 0,
    end_time: 60,
  },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("learning unit page (US3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.get.mockResolvedValue({ data: [] });
  });

  it("renders loading state initially", () => {
    courseApiMock.learningUnit.mockImplementation(() => new Promise(() => {})); // never resolves

    render(
      <LearningPage params={{ courseSlug: "cs231n", unitSlug: "lecture-1-introduction" }} />,
    );

    expect(screen.getByText("Loading learning unit...")).toBeInTheDocument();
  });

  it("renders error state when unit is not found", async () => {
    courseApiMock.learningUnit.mockRejectedValue({
      response: { status: 404 },
    });

    render(
      <LearningPage params={{ courseSlug: "cs231n", unitSlug: "does-not-exist" }} />,
    );

    await waitFor(() => {
      expect(screen.getByText(/not available/i)).toBeInTheDocument();
    });
  });

  it("renders the learning unit shell after loading", async () => {
    courseApiMock.learningUnit.mockResolvedValue(LECTURE_1_UNIT);

    render(
      <LearningPage params={{ courseSlug: "cs231n", unitSlug: "lecture-1-introduction" }} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Lecture 1: Introduction")).toBeInTheDocument();
    });
  });

  it("renders the restored learning shell frame with preserved tutor cues", async () => {
    courseApiMock.learningUnit.mockResolvedValue(LECTURE_1_UNIT);
    apiMock.get.mockResolvedValue({ data: CHAPTERS });

    render(
      <LearningPage params={{ courseSlug: "cs231n", unitSlug: "lecture-1-introduction" }} />,
    );

    expect(
      await screen.findByRole("link", {
        name: "CS231n: Deep Learning for Computer Vision",
      }),
    ).toHaveAttribute("href", "/courses/cs231n");
    expect(screen.getByText("Lecture 1: Introduction")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AI Tutor" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Chapters")).toBeInTheDocument();
      expect(screen.getByText("00:00 · Introduction")).toBeInTheDocument();
    });
  });

  it("shows AI Tutor toggle when tutor is enabled", async () => {
    courseApiMock.learningUnit.mockResolvedValue(LECTURE_1_UNIT);

    render(
      <LearningPage params={{ courseSlug: "cs231n", unitSlug: "lecture-1-introduction" }} />,
    );

    await waitFor(() => {
      expect(screen.getByText("AI Tutor")).toBeInTheDocument();
    });
  });

  it("does not show AI Tutor toggle when tutor is disabled", async () => {
    courseApiMock.learningUnit.mockResolvedValue(DISABLED_TUTOR_UNIT);

    render(
      <LearningPage params={{ courseSlug: "cs231n", unitSlug: "lecture-99-placeholder" }} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Lecture 99: Placeholder")).toBeInTheDocument();
    });

    expect(screen.queryByText("AI Tutor")).not.toBeInTheDocument();
  });

  it("shows course breadcrumb link", async () => {
    courseApiMock.learningUnit.mockResolvedValue(LECTURE_1_UNIT);

    render(
      <LearningPage params={{ courseSlug: "cs231n", unitSlug: "lecture-1-introduction" }} />,
    );

    await waitFor(() => {
      const breadcrumb = screen.getByText("CS231n: Deep Learning for Computer Vision");
      expect(breadcrumb).toBeInTheDocument();
      expect(breadcrumb.closest("a")).toHaveAttribute("href", "/courses/cs231n");
    });
  });
});
