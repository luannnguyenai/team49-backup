import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LearningPageScreen from "@/components/learn/LearningPageScreen";
import type { LearningUnitResponse } from "@/types";

const courseApiMock = vi.hoisted(() => ({
  listUnits: vi.fn(),
  lectureToc: vi.fn(),
}));

const learningSessionApiMock = vi.hoisted(() => ({
  resume: vi.fn(),
  updateProgress: vi.fn(),
}));

const navigationMock = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: {
      ...actual.courseApi,
      listUnits: courseApiMock.listUnits,
      lectureToc: courseApiMock.lectureToc,
    },
    learningSessionApi: {
      ...actual.learningSessionApi,
      resume: learningSessionApiMock.resume,
      updateProgress: learningSessionApiMock.updateProgress,
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

const LECTURE_1_UNIT: LearningUnitResponse = {
  course: {
    slug: "cs231n",
    title: "CS231n: Deep Learning for Computer Vision",
  },
  unit: {
    id: "unit_lecture_01",
    slug: "lecture-1-introduction",
    title: "Lecture 1: Introduction",
    lecture_title: "Lecture 1: Introduction",
    lecture_order: 1,
    start_seconds: null,
    unit_type: "lecture",
    status: "ready",
    entry_mode: "video",
  },
  content: {
    body_markdown: null,
    video_url: "/data/courses/CS231n/videos/lecture-1.mp4",
    transcript_available: true,
    slides_available: true,
  },
  tutor: {
    enabled: true,
    mode: "in_context",
    context_binding_id: "ctx_unit_lecture_01",
    legacy_lecture_id: "cs231n-lecture-1",
  },
};

const TOC_SUMMARY = {
  lecture_title: "CS231N: Lecture 1",
  table_of_contents: [
    {
      section_number: 1,
      timestamp: "00:00:00",
      topic_title: "Introduction",
      detailed_summary: "Opening context",
      key_takeaways: [
        "Neural networks learn layered visual features.",
      ],
    },
    {
      section_number: 2,
      timestamp: "00:05:00",
      topic_title: "Course Logistics",
      detailed_summary: "Logistics overview",
      key_takeaways: ["Assignments matter."],
    },
  ],
};

describe("learning unit mobile shell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();

    vi.stubGlobal("matchMedia", vi.fn().mockImplementation((query: string) => ({
      matches: query === "(max-width: 767px)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })));

    courseApiMock.listUnits.mockResolvedValue([
      {
        slug: "lecture-1-introduction",
        title: "Introduction",
        status: "ready",
        unit_type: "lecture",
        order_index: 1,
        lecture_label: "Lecture 01",
        is_completed: true,
      },
      {
        slug: "lecture-2-linear-classifiers",
        title: "Linear Classifiers",
        status: "ready",
        unit_type: "lecture",
        order_index: 2,
        lecture_label: "Lecture 02",
        is_completed: false,
      },
    ]);
    courseApiMock.lectureToc.mockResolvedValue(TOC_SUMMARY);
    learningSessionApiMock.resume.mockResolvedValue({
      resume_route: "/courses/cs231n/learn/lecture-1-introduction",
      current_unit_id: null,
      current_stage: null,
      current_progress: null,
      last_activity: null,
    });
    learningSessionApiMock.updateProgress.mockResolvedValue({
      learning_unit_id: "unit_lecture_01",
      current_stage: "watching",
      current_progress: {},
      last_activity: "2026-04-25T00:00:00Z",
    });
  });

  it("exposes lessons, tutor, and key ideas through mobile-native sheets", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    expect(await screen.findByRole("button", { name: "Lessons" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tutor" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Key ideas" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Lessons" }));
    expect(await screen.findByRole("dialog", { name: "Lessons" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tutor" }));
    expect(await screen.findByRole("dialog", { name: "AI Tutor" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ask about this lecture...")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Key ideas" }));
    expect(await screen.findByRole("dialog", { name: "Key ideas" })).toBeInTheDocument();
    expect(screen.getByText("Neural networks learn layered visual features.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /00:05:00 Course Logistics/i })).toBeInTheDocument();
  });

  it("returns focus to the mobile toolbar trigger after closing a sheet", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const lessonsButton = await screen.findByRole("button", { name: "Lessons" });
    lessonsButton.focus();
    fireEvent.click(lessonsButton);

    const closeButton = await screen.findByRole("button", { name: "Close Lessons" });
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(document.activeElement).toBe(lessonsButton);
    });
  });
});
