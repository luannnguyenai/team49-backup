import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LearningUnitLoading from "@/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/loading";
import LearningUnitShell from "@/components/learn/LearningUnitShell";
import LearningPageScreen from "@/components/learn/LearningPageScreen";
import TopNav from "@/components/layout/TopNav";
import type { LearningUnitResponse } from "@/types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

const courseApiMock = vi.hoisted(() => ({
  listUnits: vi.fn(),
}));

const navigationMock = vi.hoisted(() => ({
  pathname: "/",
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
      listUnits: courseApiMock.listUnits,
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
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.get.mockResolvedValue({ data: [] });
    courseApiMock.listUnits.mockResolvedValue([]);
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
      },
      {
        slug: "lecture-2-linear-classifiers",
        title: "Linear Classifiers",
        status: "ready",
        unit_type: "lecture",
        order_index: 2,
        lecture_label: "Lecture 02",
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
      expect(screen.getByText("Bài học")).toBeInTheDocument();
      expect(screen.getByText("Lecture 01")).toBeInTheDocument();
      expect(screen.getByText("Lecture 02")).toBeInTheDocument();
      expect(screen.getAllByText("Introduction").length).toBeGreaterThan(0);
      expect(screen.getByText("Key ideas at this moment")).toBeInTheDocument();
      expect(screen.getByText("Neural networks learn layered visual features.")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Ask about this lecture...")).toBeInTheDocument();
      expect(screen.getByText("Giải thích ý chính của đoạn này dễ hiểu hơn")).toBeInTheDocument();
    });
  });

  it("ignores stale toc summary responses when switching lectures quickly", async () => {
    let resolveLecture1: ((value: Response) => void) | undefined;
    let resolveLecture2: ((value: Response) => void) | undefined;

    vi.stubGlobal(
      "fetch",
      vi.fn((url: string | URL | Request) => {
        const value = String(url);
        if (value.includes("lecture-1.json")) {
          return new Promise((resolve) => {
            resolveLecture1 = resolve;
          });
        }
        if (value.includes("lecture-2.json")) {
          return new Promise((resolve) => {
            resolveLecture2 = resolve;
          });
        }
        return Promise.resolve(
          new Response(JSON.stringify(TOC_SUMMARY), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
    );

    const { rerender } = render(
      <LearningUnitShell data={LECTURE_1_UNIT} courseSlug="cs231n" />,
    );

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/data/courses/CS231n/ToC_Summary/lecture-1.json",
      );
    });

    rerender(<LearningUnitShell data={LECTURE_2_UNIT} courseSlug="cs231n" />);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/data/courses/CS231n/ToC_Summary/lecture-2.json",
      );
    });

    resolveLecture2?.(
      new Response(JSON.stringify(TOC_SUMMARY_2), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await waitFor(() => {
      expect(screen.getByText("Linear classifiers map features to scores.")).toBeInTheDocument();
    });

    resolveLecture1?.(
      new Response(JSON.stringify(TOC_SUMMARY), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

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

  it("keeps the Courses nav item active on a nested learning route", async () => {
    navigationMock.pathname = "/courses/cs231n/learn/lecture-1-introduction";

    render(<TopNav />);

    expect(screen.getByRole("link", { name: "Courses" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
