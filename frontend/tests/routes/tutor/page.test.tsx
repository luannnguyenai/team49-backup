import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TutorPage from "@/app/tutor/page";
import {
  COMING_SOON_ITEM,
  CS224N_ITEM,
  CS231N_ITEM,
} from "@/tests/fixtures/coursePlatform";

const courseApiMock = vi.hoisted(() => ({
  catalog: vi.fn(),
}));

const historyApiMock = vi.hoisted(() => ({
  list: vi.fn(),
}));

const navigationMock = vi.hoisted(() => ({
  searchParams: new URLSearchParams(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: {
      ...actual.courseApi,
      catalog: courseApiMock.catalog,
    },
    historyApi: {
      ...actual.historyApi,
      list: historyApiMock.list,
    },
  };
});

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useSearchParams: () => navigationMock.searchParams,
  };
});

describe("tutor page search", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigationMock.searchParams = new URLSearchParams();
    window.sessionStorage.clear();
    window.sessionStorage.setItem(
      "al_active_learning_unit",
      JSON.stringify({
        courseSlug: CS231N_ITEM.slug,
        unitSlug: "lecture-1-introduction",
      }),
    );

    courseApiMock.catalog.mockResolvedValue({
      items: [
        CS231N_ITEM,
        CS224N_ITEM,
        {
          ...COMING_SOON_ITEM,
          id: "course_ai_language_ops",
          slug: "ai-language-ops",
          title: "AI Language Operations",
          short_description: "Language systems in production.",
          is_recommended: true,
        },
        {
          ...COMING_SOON_ITEM,
          id: "course_vision_rollout",
          slug: "vision-rollout",
          title: "Vision Rollout Foundations",
          short_description: "Computer vision deployment patterns.",
          is_recommended: true,
        },
      ],
    });

    historyApiMock.list.mockResolvedValue({
      summary: {
        total_sessions: 1,
        completed_sessions: 1,
        avg_score: 85,
        total_study_seconds: 1800,
        score_trend: [],
      },
      total: 1,
      page: 1,
      page_size: 100,
      items: [
        {
          session_id: "session_1",
          session_type: "learning_unit",
          started_at: "2026-04-28T10:00:00Z",
          completed_at: "2026-04-28T10:30:00Z",
          duration_seconds: 1800,
          subject: "NLP basics",
          course_id: CS224N_ITEM.id,
          course_slug: CS224N_ITEM.slug,
          learning_unit_id: "unit_1",
          section_id: null,
          score_percent: 85,
          correct_count: 8,
          total_questions: 10,
          source: "unit_test",
          checkpoint: null,
        },
      ],
    });
  });

  it("filters joined and recommended courses by q while keeping the active course visible", async () => {
    navigationMock.searchParams = new URLSearchParams("q=language");

    render(<TutorPage />);

    expect(await screen.findByText("Tiếp tục học")).toBeInTheDocument();
    expect(screen.getByText(CS231N_ITEM.title)).toBeInTheDocument();
    expect(await screen.findByText(CS224N_ITEM.title)).toBeInTheDocument();
    expect(screen.getByText("AI Language Operations")).toBeInTheDocument();
    expect(screen.queryByText("Vision Rollout Foundations")).not.toBeInTheDocument();
  });

  it("shows a search-specific empty state without hiding the active course panel", async () => {
    navigationMock.searchParams = new URLSearchParams("q=graph rag systems");

    render(<TutorPage />);

    expect(await screen.findByText("Tiếp tục học")).toBeInTheDocument();
    expect(screen.getByText(CS231N_ITEM.title)).toBeInTheDocument();
    expect(
      await screen.findByText(/không tìm thấy khóa học phù hợp với từ khóa/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(CS224N_ITEM.title)).not.toBeInTheDocument();
    expect(screen.queryByText("AI Language Operations")).not.toBeInTheDocument();
  });
});
