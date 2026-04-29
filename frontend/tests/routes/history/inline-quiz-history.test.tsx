import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HistoryPage from "@/app/(protected)/history/page";

const historyApiMock = vi.hoisted(() => ({
  list: vi.fn(),
  detail: vi.fn(),
}));

const canonicalSectionApiMock = vi.hoisted(() => ({
  list: vi.fn(),
}));

const navigationMock = vi.hoisted(() => ({
  searchParams: new URLSearchParams(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    historyApi: historyApiMock,
    canonicalSectionApi: canonicalSectionApiMock,
  };
});

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useSearchParams: () => navigationMock.searchParams,
  };
});

describe("history page inline quiz rows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigationMock.searchParams = new URLSearchParams("session_id=session-inline-1");
    canonicalSectionApiMock.list.mockResolvedValue([]);
  });

  it("renders inline midpoint badges and auto-expands the targeted session review when the row is on the page", async () => {
    historyApiMock.list.mockResolvedValue({
      summary: {
        total_sessions: 1,
        completed_sessions: 1,
        avg_score: 75,
        total_study_seconds: 300,
        score_trend: [],
      },
      total: 1,
      page: 1,
      page_size: 20,
      items: [
        {
          session_id: "session-inline-1",
          session_type: "quiz",
          started_at: "2026-04-25T00:00:00Z",
          completed_at: "2026-04-25T00:05:00Z",
          duration_seconds: 300,
          subject: "Backpropagation",
          learning_unit_id: "unit-1",
          section_id: "section-1",
          score_percent: 75,
          correct_count: 3,
          total_questions: 4,
          source: "inline_video",
          checkpoint: "midpoint",
        },
      ],
    });
    historyApiMock.detail.mockResolvedValue({
      session_id: "session-inline-1",
      session_type: "quiz",
      bloom_breakdown: {},
      weak_kcs: [],
      misconceptions: [],
      source: "inline_video",
      checkpoint: "midpoint",
      questions: [
        {
          question_id: null,
          canonical_item_id: "canonical-question-1",
          sequence_position: 1,
          learning_unit_title: "Backpropagation",
          stem_text: "Which choice is correct?",
          bloom_level: "remember",
          difficulty_bucket: "easy",
          option_a: "A",
          option_b: "B",
          option_c: "C",
          option_d: "D",
          selected_answer: "A",
          correct_answer: "B",
          is_correct: false,
          response_time_ms: 1000,
          explanation_text: "Because B is correct.",
        },
      ],
    });

    render(<HistoryPage />);

    await waitFor(() => {
      expect(historyApiMock.list).toHaveBeenCalled();
    });

    expect(screen.getByText("Mid-video quiz")).toBeInTheDocument();

    await waitFor(() => {
      expect(historyApiMock.detail).toHaveBeenCalledWith("session-inline-1");
    });

    expect(await screen.findByText("Question details (1 questions)")).toBeInTheDocument();
    expect(screen.getByText("Which choice is correct?")).toBeInTheDocument();
  });

  it("shows a dedicated deep-link review panel when the target session is not in the loaded page", async () => {
    historyApiMock.list.mockResolvedValue({
      summary: {
        total_sessions: 1,
        completed_sessions: 1,
        avg_score: 75,
        total_study_seconds: 300,
        score_trend: [],
      },
      total: 1,
      page: 1,
      page_size: 20,
      items: [
        {
          session_id: "different-session",
          session_type: "quiz",
          started_at: "2026-04-25T00:00:00Z",
          completed_at: "2026-04-25T00:05:00Z",
          duration_seconds: 300,
          subject: "Other quiz",
          learning_unit_id: "unit-2",
          section_id: "section-2",
          score_percent: 50,
          correct_count: 2,
          total_questions: 4,
          source: null,
          checkpoint: null,
        },
      ],
    });
    historyApiMock.detail.mockResolvedValue({
      session_id: "session-inline-1",
      session_type: "quiz",
      bloom_breakdown: {},
      weak_kcs: [],
      misconceptions: [],
      source: "inline_video",
      checkpoint: "midpoint",
      questions: [
        {
          question_id: null,
          canonical_item_id: "canonical-question-2",
          sequence_position: 2,
          learning_unit_title: "Backpropagation",
          stem_text: "Why is B correct?",
          bloom_level: "understand",
          difficulty_bucket: "medium",
          option_a: "A",
          option_b: "B",
          option_c: "C",
          option_d: "D",
          selected_answer: "A",
          correct_answer: "B",
          is_correct: false,
          response_time_ms: 900,
          explanation_text: "Because of the gradient signal.",
        },
      ],
    });

    render(<HistoryPage />);

    await waitFor(() => {
      expect(historyApiMock.detail).toHaveBeenCalledWith("session-inline-1");
    });

    expect(await screen.findByText("Review opened from link")).toBeInTheDocument();
    expect(screen.getByText("Mid-video quiz")).toBeInTheDocument();
    expect(screen.getByText("Why is B correct?")).toBeInTheDocument();
  });
});
