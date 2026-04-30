import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LearningUnitLoading from "@/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/loading";
import LearningUnitShell from "@/components/learn/LearningUnitShell";
import LearningPageScreen from "@/components/learn/LearningPageScreen";
import TopNav from "@/components/layout/TopNav";
import {
  COMING_SOON_ITEM,
  CS224N_ITEM,
  CS231N_ITEM,
  CS231N_RECOMMENDED,
} from "@/tests/fixtures/coursePlatform";
import type { LearningUnitResponse } from "@/types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

const courseApiMock = vi.hoisted(() => ({
  catalog: vi.fn(),
  listUnits: vi.fn(),
  lectureToc: vi.fn(),
}));

const learningSessionApiMock = vi.hoisted(() => ({
  resume: vi.fn(),
  updateProgress: vi.fn(),
}));

const canonicalQuizApiMock = vi.hoisted(() => ({
  start: vi.fn(),
}));

const quizApiMock = vi.hoisted(() => ({
  answer: vi.fn(),
  complete: vi.fn(),
}));

const navigationMock = vi.hoisted(() => ({
  pathname: "/",
  searchParams: new URLSearchParams(),
  router: {
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  },
}));

const authStoreMock = vi.hoisted(() => ({
  user: {
    id: "user_1",
    full_name: "Test User",
    is_onboarded: true,
  } as { id: string; full_name: string; is_onboarded: boolean } | null,
  logout: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: apiMock,
    courseApi: {
      ...actual.courseApi,
      catalog: courseApiMock.catalog,
      listUnits: courseApiMock.listUnits,
      lectureToc: courseApiMock.lectureToc,
    },
    learningSessionApi: {
      ...actual.learningSessionApi,
      resume: learningSessionApiMock.resume,
      updateProgress: learningSessionApiMock.updateProgress,
    },
    canonicalQuizApi: {
      ...actual.canonicalQuizApi,
      start: canonicalQuizApiMock.start,
    },
    quizApi: {
      ...actual.quizApi,
      answer: quizApiMock.answer,
      complete: quizApiMock.complete,
    },
  };
});

vi.mock("@/stores/authStore", async () => {
  return {
    useAuthStore: (selector?: (state: unknown) => unknown) => {
      const state = { user: authStoreMock.user, logout: authStoreMock.logout };
      return selector ? selector(state) : state;
    },
  };
});

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    usePathname: () => navigationMock.pathname,
    useSearchParams: () => navigationMock.searchParams,
    useRouter: () => navigationMock.router,
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

const DISABLED_TUTOR_UNIT: LearningUnitResponse = {
  course: {
    slug: "cs231n",
    title: "CS231n: Deep Learning for Computer Vision",
  },
  unit: {
    id: "unit_lecture_99",
    slug: "lecture-99-placeholder",
    title: "Lecture 99: Placeholder",
    lecture_title: "Lecture 99: Placeholder",
    lecture_order: 99,
    start_seconds: null,
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
    legacy_lecture_id: null,
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
        "The lecture sets up the course scope.",
      ],
    },
    {
      section_number: 2,
      timestamp: "00:05:00",
      topic_title: "Course Logistics",
      detailed_summary: "Logistics overview",
      key_takeaways: [
        "Assignments matter.",
      ],
    },
  ],
};

const LECTURE_2_UNIT: LearningUnitResponse = {
  course: {
    slug: "cs231n",
    title: "CS231n: Deep Learning for Computer Vision",
  },
  unit: {
    id: "unit_lecture_02",
    slug: "lecture-2-linear-classifiers",
    title: "Lecture 2: Image Classification with Linear Classifiers",
    lecture_title: "Lecture 2: Image Classification with Linear Classifiers",
    lecture_order: 2,
    start_seconds: null,
    unit_type: "lecture",
    status: "ready",
    entry_mode: "video",
  },
  content: {
    body_markdown: null,
    video_url: "/data/courses/CS231n/videos/lecture-2.mp4",
    transcript_available: true,
    slides_available: true,
  },
  tutor: {
    enabled: true,
    mode: "in_context",
    context_binding_id: "ctx_unit_lecture_02",
    legacy_lecture_id: "cs231n-lecture-2",
  },
};

const TOC_SUMMARY_2 = {
  lecture_title: "CS231N: Lecture 2",
  table_of_contents: [
    {
      section_number: 1,
      timestamp: "00:00:00",
      topic_title: "Linear Classification",
      detailed_summary: "Linear classifier overview",
      key_takeaways: [
        "Linear classifiers map features to scores.",
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("learning unit page (US3)", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { resetCachedAllCourseCatalog } = await import("@/lib/course-catalog-cache");
    resetCachedAllCourseCatalog();
    apiMock.get.mockResolvedValue({ data: [] });
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
    courseApiMock.listUnits.mockResolvedValue([]);
    courseApiMock.lectureToc.mockImplementation((courseSlug: string, lectureOrder: number) => {
      if (courseSlug === "cs231n" && lectureOrder === 1) {
        return Promise.resolve(TOC_SUMMARY);
      }
      if (courseSlug === "cs231n" && lectureOrder === 2) {
        return Promise.resolve(TOC_SUMMARY_2);
      }
      return Promise.resolve({ lecture_title: "", table_of_contents: [] });
    });
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
    canonicalQuizApiMock.start.mockReset();
    quizApiMock.answer.mockReset();
    quizApiMock.complete.mockReset();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(TOC_SUMMARY), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    navigationMock.pathname = "/";
    navigationMock.searchParams = new URLSearchParams();
  });

  it("renders route loading state while the server component is resolving", () => {
    render(<LearningUnitLoading />);
    expect(screen.getByText("Loading learning unit...")).toBeInTheDocument();
  });

  it("renders error state when the server wrapper reports a missing unit", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="does-not-exist"
        error="This learning unit is not available. It may not exist or the course content has not been published yet."
      />,
    );

    expect(screen.getByText(/not available/i)).toBeInTheDocument();
  });

  it("renders the learning unit shell from server-provided data", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    await waitFor(() => {
      expect(screen.getAllByText("Lecture 1: Introduction").length).toBeGreaterThan(0);
    });
  });

  it("renders the restored learning shell frame with preserved tutor cues", async () => {
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

    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    expect(
      await screen.findByRole("link", {
        name: "CS231n: Deep Learning for Computer Vision",
      }),
    ).toHaveAttribute("href", "/courses/cs231n");
    expect(screen.getAllByText("Lecture 1: Introduction").length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByText("Lessons")).toBeInTheDocument();
      expect(screen.getByText("Lecture 01")).toBeInTheDocument();
      expect(screen.getByText("Lecture 02")).toBeInTheDocument();
      expect(screen.getByLabelText("Lecture 01 completed")).toBeInTheDocument();
      expect(screen.getAllByText("Introduction").length).toBeGreaterThan(0);
      expect(screen.getByText("Key ideas at this moment")).toBeInTheDocument();
      expect(screen.getByText("Neural networks learn layered visual features.")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Ask about this lecture...")).toBeInTheDocument();
      expect(screen.getByText("Explain the main idea of this section in simpler terms")).toBeInTheDocument();
      expect(screen.getByLabelText("Video progress rail")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Hide lessons panel" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Close tutor" })).toBeInTheDocument();
    });
  });

  it("ignores stale toc summary responses when switching lectures quickly", async () => {
    let resolveLecture1: ((value: typeof TOC_SUMMARY) => void) | undefined;
    let resolveLecture2: ((value: typeof TOC_SUMMARY_2) => void) | undefined;

    courseApiMock.lectureToc.mockImplementation((courseSlug: string, lectureOrder: number) => {
      if (courseSlug === "cs231n" && lectureOrder === 1) {
        return new Promise((resolve) => {
          resolveLecture1 = resolve;
        });
      }
      if (courseSlug === "cs231n" && lectureOrder === 2) {
        return new Promise((resolve) => {
          resolveLecture2 = resolve;
        });
      }
      return Promise.resolve({ lecture_title: "", table_of_contents: [] });
    });

    const { rerender } = render(
      <LearningUnitShell data={LECTURE_1_UNIT} courseSlug="cs231n" />,
    );

    await waitFor(() => {
      expect(courseApiMock.lectureToc).toHaveBeenCalledWith(
        "cs231n",
        1,
      );
    });

    rerender(<LearningUnitShell data={LECTURE_2_UNIT} courseSlug="cs231n" />);

    await waitFor(() => {
      expect(courseApiMock.lectureToc).toHaveBeenCalledWith(
        "cs231n",
        2,
      );
    });

    resolveLecture2?.(TOC_SUMMARY_2);

    await waitFor(() => {
      expect(screen.getByText("Linear classifiers map features to scores.")).toBeInTheDocument();
    });

    resolveLecture1?.(TOC_SUMMARY);

    await waitFor(() => {
      expect(screen.queryByText("Neural networks learn layered visual features.")).not.toBeInTheDocument();
      expect(screen.getByText("Linear classifiers map features to scores.")).toBeInTheDocument();
    });
  });

  it("shows the AI Tutor panel by default when tutor is enabled", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("AI Tutor")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Ask about this lecture...")).toBeInTheDocument();
    });
  });

  it("renders key ideas before timestamps in the desktop shell", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const keyIdeasHeading = await screen.findByText("Key ideas at this moment");
    const timestampsHeading = await screen.findByText("Timestamps");

    expect(
      keyIdeasHeading.compareDocumentPosition(timestampsHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("allows hiding and reopening both desktop side panels", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const hideLessons = await screen.findByRole("button", { name: "Hide lessons panel" });
    fireEvent.click(hideLessons);
    expect(screen.getByRole("button", { name: "Open lessons panel" })).toBeInTheDocument();

    const closeTutor = screen.getByRole("button", { name: "Close tutor" });
    fireEvent.click(closeTutor);
    expect(screen.getByRole("button", { name: "Open AI Tutor panel" })).toBeInTheDocument();
  });

  it("renders chapter and checkpoint markers on the custom progress rail when duration is known", async () => {
    const { container } = render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const video = container.querySelector("video");
    expect(video).not.toBeNull();

    Object.defineProperty(video, "duration", {
      configurable: true,
      writable: true,
      value: 600,
    });

    fireEvent(video!, new Event("durationchange"));

    await waitFor(() => {
      expect(screen.getAllByTestId("chapter-marker")).toHaveLength(2);
      expect(screen.getAllByTestId("checkpoint-marker")).toHaveLength(2);
    });
  });

  it("syncs video duration from loaded metadata so chapter markers remain visible", async () => {
    const { container } = render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const video = container.querySelector("video");
    expect(video).not.toBeNull();

    Object.defineProperty(video, "duration", {
      configurable: true,
      writable: true,
      value: 600,
    });

    fireEvent(video!, new Event("loadedmetadata"));

    await waitFor(() => {
      expect(screen.getAllByTestId("chapter-marker")).toHaveLength(2);
      expect(screen.getAllByText(/00:00 \/ 10:00/).length).toBeGreaterThan(0);
    });
  });

  it("seeks to the selected canonical unit timestamp after video metadata loads", async () => {
    const targetUnit = {
      ...LECTURE_1_UNIT,
      unit: {
        ...LECTURE_1_UNIT.unit,
        start_seconds: 300,
      },
    };

    const { container } = render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={targetUnit}
      />,
    );

    const video = container.querySelector("video");
    expect(video).not.toBeNull();

    Object.defineProperty(video, "duration", {
      configurable: true,
      writable: true,
      value: 600,
    });
    Object.defineProperty(video, "currentTime", {
      configurable: true,
      writable: true,
      value: 0,
    });

    fireEvent(video!, new Event("loadedmetadata"));

    await waitFor(() => {
      expect(video!.currentTime).toBe(300);
      expect(screen.getAllByText(/05:00 \/ 10:00/).length).toBeGreaterThan(0);
    });
  });

  it("shows the mid-video quiz overlay prompt when the viewer reaches the midpoint", async () => {
    const { container } = render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const video = container.querySelector("video");
    expect(video).not.toBeNull();

    Object.defineProperty(video, "duration", {
      configurable: true,
      writable: true,
      value: 600,
    });
    Object.defineProperty(video, "currentTime", {
      configurable: true,
      writable: true,
      value: 300,
    });

    fireEvent(video!, new Event("durationchange"));
    fireEvent(video!, new Event("timeupdate"));

    expect(await screen.findByRole("button", { name: "Start quiz" })).toBeInTheDocument();
  });

  it("pauses the video as soon as the mid-video quiz prompt appears", async () => {
    const { container } = render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const video = container.querySelector("video");
    expect(video).not.toBeNull();

    const pauseSpy = vi.fn();
    Object.defineProperty(video, "duration", {
      configurable: true,
      writable: true,
      value: 600,
    });
    Object.defineProperty(video, "currentTime", {
      configurable: true,
      writable: true,
      value: 300,
    });
    Object.defineProperty(video, "paused", {
      configurable: true,
      get: () => false,
    });
    Object.defineProperty(video, "pause", {
      configurable: true,
      writable: true,
      value: pauseSpy,
    });

    fireEvent(video!, new Event("durationchange"));
    fireEvent(video!, new Event("timeupdate"));

    expect(await screen.findByRole("button", { name: "Start quiz" })).toBeInTheDocument();
    expect(pauseSpy).toHaveBeenCalledTimes(1);
  });

  it("shows the end-of-video quiz overlay when playback finishes", async () => {
    const { container } = render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const video = container.querySelector("video");
    expect(video).not.toBeNull();

    Object.defineProperty(video, "duration", {
      configurable: true,
      writable: true,
      value: 600,
    });
    Object.defineProperty(video, "currentTime", {
      configurable: true,
      writable: true,
      value: 300,
    });

    fireEvent(video!, new Event("durationchange"));
    fireEvent(video!, new Event("timeupdate"));

    const dismissButton = await screen.findByRole("button", { name: "Dismiss for now" });
    fireEvent.click(dismissButton);

    Object.defineProperty(video, "currentTime", {
      configurable: true,
      writable: true,
      value: 600,
    });

    fireEvent(video!, new Event("ended"));

    expect(await screen.findAllByText("End-of-video quiz")).toHaveLength(2);
    expect(await screen.findByRole("button", { name: "Start quiz" })).toBeInTheDocument();
  });

  it("pauses the video as soon as the end-of-video quiz prompt appears", async () => {
    const { container } = render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    const video = container.querySelector("video");
    expect(video).not.toBeNull();

    const pauseSpy = vi.fn();
    Object.defineProperty(video, "duration", {
      configurable: true,
      writable: true,
      value: 600,
    });
    Object.defineProperty(video, "currentTime", {
      configurable: true,
      writable: true,
      value: 300,
    });
    Object.defineProperty(video, "paused", {
      configurable: true,
      get: () => false,
    });
    Object.defineProperty(video, "pause", {
      configurable: true,
      writable: true,
      value: pauseSpy,
    });

    fireEvent(video!, new Event("durationchange"));
    fireEvent(video!, new Event("timeupdate"));

    const dismissButton = await screen.findByRole("button", { name: "Dismiss for now" });
    fireEvent.click(dismissButton);

    Object.defineProperty(video, "currentTime", {
      configurable: true,
      writable: true,
      value: 600,
    });

    fireEvent(video!, new Event("ended"));

    expect(await screen.findByRole("button", { name: "Start quiz" })).toBeInTheDocument();
    expect(await screen.findAllByText("End-of-video quiz")).toHaveLength(2);
    expect(pauseSpy).toHaveBeenCalledTimes(2);
  });

  it("does not show AI Tutor toggle when tutor is disabled", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-99-placeholder"
        data={DISABLED_TUTOR_UNIT}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Lecture 99: Placeholder")).toBeInTheDocument();
    });

    expect(screen.queryByText("AI Tutor")).not.toBeInTheDocument();
  });

  it("shows course breadcrumb link", async () => {
    render(
      <LearningPageScreen
        courseSlug="cs231n"
        unitSlug="lecture-1-introduction"
        data={LECTURE_1_UNIT}
      />,
    );

    await waitFor(() => {
      const breadcrumb = screen.getByText("CS231n: Deep Learning for Computer Vision");
      expect(breadcrumb).toBeInTheDocument();
      expect(breadcrumb.closest("a")).toHaveAttribute("href", "/courses/cs231n");
    });
  });

  async function renderTopNavAndWaitForCatalog() {
    render(<TopNav />);

    await waitFor(() => {
      expect(courseApiMock.catalog).toHaveBeenCalledWith({
        view: "all",
        includeUnavailable: true,
      });
    });
  }

  it("hides the Courses nav item after login on a nested learning route", async () => {
    navigationMock.pathname = "/courses/cs231n/learn/lecture-1-introduction";

    await renderTopNavAndWaitForCatalog();

    expect(screen.queryByRole("link", { name: "Courses" })).not.toBeInTheDocument();
  });

  it("renders desktop top nav in the order logo, search, then navigation links", async () => {
    navigationMock.pathname = "/dashboard";

    await renderTopNavAndWaitForCatalog();

    const brand = screen.getByRole("link", { name: "AI Learning Hub" });
    const search = screen.getByLabelText("Search courses");
    const tutorLink = screen.getByRole("link", { name: "AI Tutor" });

    const headerRow = brand.closest("header")?.firstElementChild;
    expect(headerRow).not.toBeNull();
    expect(headerRow?.contains(brand)).toBe(true);
    expect(headerRow?.contains(search)).toBe(true);
    expect(headerRow?.contains(tutorLink)).toBe(true);
    expect(
      brand.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      search.compareDocumentPosition(tutorLink) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("returns to the landing page after logout from top nav", async () => {
    let resolveLogout!: () => void;
    authStoreMock.logout.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveLogout = resolve;
        }),
    );

    navigationMock.pathname = "/dashboard";

    await renderTopNavAndWaitForCatalog();

    fireEvent.click(screen.getByRole("button", { name: /sign out/i }));

    expect(authStoreMock.logout).toHaveBeenCalledTimes(1);
    expect(navigationMock.router.push).not.toHaveBeenCalled();

    resolveLogout();

    await waitFor(() => {
      expect(navigationMock.router.push).toHaveBeenCalledWith("/");
    });
  });

  it("shows the search input on non-course routes as a global nav control", async () => {
    navigationMock.pathname = "/history";

    await renderTopNavAndWaitForCatalog();

    expect(screen.getByLabelText("Search courses")).toBeInTheDocument();
  });

  it("loads the course catalog when the dropdown search is activated", async () => {
    navigationMock.pathname = "/dashboard";

    render(<TopNav />);

    fireEvent.focus(screen.getByLabelText("Search courses"));

    await waitFor(() => {
      expect(courseApiMock.catalog).toHaveBeenCalledWith({
        view: "all",
        includeUnavailable: true,
      });
    });
  });

  it("preloads the course catalog before the search input is focused", async () => {
    navigationMock.pathname = "/dashboard";

    await renderTopNavAndWaitForCatalog();
  });

  it("shows matching courses in a dropdown beneath the search input", async () => {
    navigationMock.pathname = "/learn";

    render(<TopNav />);

    const input = screen.getByLabelText("Search courses");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "vision" } });

    expect(
      await screen.findByRole("button", { name: /cs231n: deep learning for computer vision/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("topnav-search-dropdown")).toHaveClass("absolute");
    expect(screen.getByText(/deep learning foundations for computer vision/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: /cs224n: natural language processing with deep learning/i,
      }),
    ).not.toBeInTheDocument();
  });

  it("hides the clear button when the search input is empty", async () => {
    navigationMock.pathname = "/dashboard";

    await renderTopNavAndWaitForCatalog();

    expect(
      screen.queryByRole("button", { name: "Clear search query" }),
    ).not.toBeInTheDocument();
  });

  it("shows the clear button when the search input has a value", async () => {
    navigationMock.pathname = "/dashboard";

    render(<TopNav />);

    fireEvent.change(screen.getByLabelText("Search courses"), {
      target: { value: "cs231n" },
    });

    await waitFor(() => {
      expect(courseApiMock.catalog).toHaveBeenCalled();
    });

    expect(
      screen.getByRole("button", { name: "Clear search query" }),
    ).toBeInTheDocument();
  });

  it("clears the search input and closes the dropdown when clear button is pressed", async () => {
    navigationMock.pathname = "/dashboard";

    render(<TopNav />);

    const input = screen.getByLabelText("Search courses");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "cs231n" } });

    await screen.findByRole("button", { name: /cs231n: deep learning for computer vision/i });

    fireEvent.click(
      screen.getByRole("button", { name: "Clear search query" }),
    );

    expect(input).toHaveValue("");
    expect(
      screen.queryByRole("button", { name: /cs231n: deep learning for computer vision/i }),
    ).not.toBeInTheDocument();
  });

  it("routes to the selected course when a dropdown result is clicked", async () => {
    navigationMock.pathname = "/profile";

    render(<TopNav />);

    const input = screen.getByLabelText("Search courses");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "language" } });

    fireEvent.click(
      await screen.findByRole("button", {
        name: /cs224n: natural language processing with deep learning/i,
      }),
    );

    expect(navigationMock.router.push).toHaveBeenCalledWith("/courses/cs224n");
  });

  it("routes to the first matching course when Enter is pressed in the search input", async () => {
    navigationMock.pathname = "/profile";

    render(<TopNav />);

    const input = screen.getByLabelText("Search courses");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "language" } });

    await screen.findByRole("button", {
      name: /cs224n: natural language processing with deep learning/i,
    });

    fireEvent.keyDown(input, { key: "Enter" });

    expect(navigationMock.router.push).toHaveBeenCalledWith("/courses/cs224n");
  });

  it("exits the loading state in React strict mode after catalog preloading resolves", async () => {
    navigationMock.pathname = "/dashboard";

    render(
      <StrictMode>
        <TopNav />
      </StrictMode>,
    );

    const input = screen.getByLabelText("Search courses");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "deep learning" } });

    expect(await screen.findByText("CS231n: Deep Learning for Computer Vision")).toBeInTheDocument();
    expect(screen.queryByText("Loading courses...")).not.toBeInTheDocument();
  });

});
