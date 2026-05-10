import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AssessmentResultsPage from "@/app/assessment/results/page";
import { assessmentApi } from "@/lib/api";
import type { AssessmentResultResponse } from "@/types";

const navigationMock = vi.hoisted(() => ({
  push: vi.fn(),
  searchParams: new URLSearchParams("session_id=session-1"),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => ({ push: navigationMock.push }),
    useSearchParams: () => navigationMock.searchParams,
  };
});

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    assessmentApi: {
      results: vi.fn(),
      summary: vi.fn(),
      updateTopicDecision: vi.fn(),
    },
  };
});

const assessmentResult: AssessmentResultResponse = {
  session_id: "session-1",
  completed_at: "2026-05-05T00:00:00Z",
  overall_score_percent: 88,
  learning_unit_results: [
    {
      learning_unit_id: "u1",
      learning_unit_title: "Word2vec training setup and likelihood objective",
      score_percent: 100,
      mastery_level: "mastered",
      bloom_breakdown: { remember: "1/1" },
      weak_kcs: [],
      misconceptions_detected: [],
    },
    {
      learning_unit_id: "u2",
      learning_unit_title: "Word2vec mechanics and word-vector analogy behavior",
      score_percent: 60,
      mastery_level: "developing",
      bloom_breakdown: { apply: "1/2" },
      weak_kcs: [],
      misconceptions_detected: [],
    },
  ],
  topic_decisions: [
    {
      topic_unit_id: "u1",
      topic_unit_name: "Word2vec training setup and likelihood objective",
      score_pct: 100,
      decision: "skip",
      mastery_level: "mastered",
      questions_total: 1,
      questions_correct: 1,
    },
    {
      topic_unit_id: "u2",
      topic_unit_name: "Word2vec mechanics and word-vector analogy behavior",
      score_pct: 60,
      decision: "review",
      mastery_level: "developing",
      questions_total: 2,
      questions_correct: 1,
    },
  ],
};

describe("assessment results page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigationMock.searchParams = new URLSearchParams("session_id=session-1");
    vi.mocked(assessmentApi.results).mockResolvedValue(assessmentResult);
    vi.mocked(assessmentApi.summary).mockResolvedValue({
      available: false,
      summary: null,
      highlights: [],
      next_step: null,
      model_used: null,
      provider: null,
    });
  });

  it("shows the names of sections that will be skipped", async () => {
    render(<AssessmentResultsPage />);

    expect(await screen.findByText("1 sections will be skipped")).toBeInTheDocument();
    expect(screen.getByText("Word2vec training setup and likelihood objective")).toBeInTheDocument();
  });

  it("renders AI summary when available", async () => {
    vi.mocked(assessmentApi.summary).mockResolvedValue({
      available: true,
      summary: "Review activation functions before moving on.",
      highlights: ["1 unit needs review"],
      next_step: "Start with the weakest unit.",
      model_used: "gpt-5.4-mini",
      provider: "openai",
    });

    render(<AssessmentResultsPage />);

    expect(await screen.findByText("AI summary")).toBeInTheDocument();
    expect(screen.getByText("Review activation functions before moving on.")).toBeInTheDocument();
  });

  it("shows an unavailable AI feedback state instead of silently hiding it", async () => {
    render(<AssessmentResultsPage />);

    expect(
      await screen.findByText("AI feedback is temporarily unavailable. Your scored placement results below are still saved."),
    ).toBeInTheDocument();
  });
});
