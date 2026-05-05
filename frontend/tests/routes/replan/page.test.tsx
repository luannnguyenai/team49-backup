import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReplanPage from "@/app/replan/page";
import {
  readPendingCanonicalAssessment,
  readStartedCanonicalAssessment,
} from "@/lib/canonical-assessment-session";
import { replanApi } from "@/lib/replan-api";

const navigationMock = vi.hoisted(() => ({
  push: vi.fn(),
  back: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
    useSearchParams: () => navigationMock.searchParams,
  };
});

// Mock replan API calls
vi.mock("@/lib/replan-api", () => ({
  replanApi: {
    analyze: vi.fn(),
    startAssessment: vi.fn(),
  },
}));

describe("replan page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    navigationMock.searchParams = new URLSearchParams();
    // Default successful API responses
    vi.mocked(replanApi.analyze).mockResolvedValue({
      units: [
        {
          canonicalUnitId: "unit_faster_rcnn",
          title: "Faster R-CNN",
          source: "matched_from_description",
          suggestedForTitle: null,
          knowledgePoints: ["Region Proposal Network", "ROI Pooling"],
          questionCounts: { easy: 5, medium: 8, hard: 6, application: 3 },
        },
      ],
      prerequisites: [],
      keywordPlanSpecificity: "specific",
      guardrailFlags: [],
      status: "ready",
      popup: null,
    });
    vi.mocked(replanApi.startAssessment).mockResolvedValue({
      sessionId: "test-session-123",
      totalQuestions: 10,
      canonicalUnitIds: ["unit_faster_rcnn"],
      unitNameMap: { unit_faster_rcnn: "Faster R-CNN" },
      assessmentHref: "/assessment?next=%2Flearn",
      questions: [
        {
          id: null,
          item_id: "item-1",
          canonical_item_id: "item-1",
          canonical_unit_id: "unit_faster_rcnn",
          topic_id: null,
          bloom_level: null,
          difficulty_bucket: "easy",
          stem_text: "Question",
          option_a: "A",
          option_b: "B",
          option_c: "C",
          option_d: "D",
          time_expected_seconds: 30,
        },
      ],
    });
  });

  it("renders a scope-builder wizard without a cancel flow", () => {
    render(<ReplanPage />);

    expect(screen.getByRole("heading", { name: "Optimize Learning Path" })).toBeInTheDocument();
    expect(screen.getByText(/This description does not automatically skip lessons/i)).toBeInTheDocument();
    expect(screen.getByLabelText("What do you already know?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /cancel/i })).not.toBeInTheDocument();
  });

  it("returns to the explicit source route when launched with a return target", () => {
    navigationMock.searchParams = new URLSearchParams("source=agent&returnTo=%2Fagent");

    render(<ReplanPage />);

    fireEvent.click(screen.getByRole("button", { name: "Back" }));

    expect(navigationMock.push).toHaveBeenCalledWith("/agent");
    expect(navigationMock.back).not.toHaveBeenCalled();
  });

  it("uses the backend guardrail classification before showing skip-all feedback", async () => {
    vi.mocked(replanApi.analyze).mockResolvedValue({
      units: [],
      prerequisites: [],
      keywordPlanSpecificity: "broad",
      guardrailFlags: ["skip_all"],
      status: "guardrail_blocked",
      popup: {
        kind: "guardrail_blocked",
        title: "Scope too broad",
        message: "Specify the concepts or units you already know instead of trying to skip the entire path.",
      },
    });

    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("What do you already know?"), {
      target: { value: "skip all" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => {
      expect(replanApi.analyze).toHaveBeenCalledWith("skip all");
    });
    expect(await screen.findByRole("dialog", { name: "Scope too broad" })).toBeInTheDocument();
    expect(screen.getByText(/instead of trying to skip the entire path/i)).toBeInTheDocument();
  });

  it("continues from a valid claim to scope review and starts the existing assessment flow", async () => {
    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("What do you already know?"), {
      target: { value: "I know Faster R-CNN and CNN feature extraction" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    // Wait for API call to complete
    expect(await screen.findByText("Review verification scope")).toBeInTheDocument();
    expect(replanApi.analyze).toHaveBeenCalledWith("I know Faster R-CNN and CNN feature extraction");
    expect(screen.getByText("Faster R-CNN")).toBeInTheDocument();
    expect(screen.getByText("Region Proposal Network")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));

    // Wait for async operations to complete
    await vi.waitFor(() => {
      expect(replanApi.startAssessment).toHaveBeenCalledWith([
        { canonicalUnitId: "unit_faster_rcnn", difficultyFilter: "all" },
      ]);
    });

    expect(readPendingCanonicalAssessment()).toMatchObject({
      canonicalUnitIds: ["unit_faster_rcnn"],
      unitNameMap: {
        unit_faster_rcnn: "Faster R-CNN",
      },
      assessmentDepth: "deep",
    });
    expect(readStartedCanonicalAssessment()).toMatchObject({
      sessionId: "test-session-123",
      canonicalUnitIds: ["unit_faster_rcnn"],
      questions: [
        expect.objectContaining({
          canonical_item_id: "item-1",
          canonical_unit_id: "unit_faster_rcnn",
        }),
      ],
    });
    expect(navigationMock.push).toHaveBeenCalledWith("/assessment?next=%2Flearn");
  });

  it("adds prerequisite suggestions only after the learner accepts the popup", async () => {
    // Mock API response with prerequisites
    vi.mocked(replanApi.analyze).mockResolvedValue({
      units: [
        {
          canonicalUnitId: "unit_faster_rcnn",
          title: "Faster R-CNN",
          source: "matched_from_description",
          suggestedForTitle: null,
          knowledgePoints: ["Region Proposal Network"],
          questionCounts: { easy: 5, medium: 8, hard: 6, application: 3 },
        },
      ],
      prerequisites: [
        {
          canonicalUnitId: "unit_rcnn",
          title: "R-CNN",
          reason: "Foundation for Faster R-CNN",
          depth: 1,
          reviewUnit: {
            canonicalUnitId: "unit_rcnn",
            title: "R-CNN",
            source: "suggested_prerequisite",
            suggestedForTitle: "Faster R-CNN",
            knowledgePoints: ["Selective Search"],
            questionCounts: { easy: 3, medium: 4, hard: 2, application: 1 },
          },
        },
      ],
      keywordPlanSpecificity: "specific",
      guardrailFlags: [],
      status: "ready",
      popup: null,
    });

    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("What do you already know?"), {
      target: { value: "I know Faster R-CNN and CNN feature extraction" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("dialog", { name: /Found related foundational topics/i })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "Include R-CNN" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add to assessment" }));

    expect(screen.getByRole("checkbox", { name: "Include R-CNN" })).toBeChecked();
    expect(screen.getByText("Source: Suggested prerequisite for Faster R-CNN")).toBeInTheDocument();
  });

  it("notifies when the claim only matches already handled units", async () => {
    // Mock API response indicating all units are already mastered
    vi.mocked(replanApi.analyze).mockResolvedValue({
      units: [],
      prerequisites: [],
      keywordPlanSpecificity: "specific",
      guardrailFlags: ["all_already_mastered"],
      status: "all_already_mastered",
      popup: {
        kind: "all_already_mastered",
        title: "Already mastered",
        message: "These units are already marked as mastered in your learning path.",
      },
    });

    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("What do you already know?"), {
      target: { value: "I already mastered Faster R-CNN" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("dialog", { name: "Already mastered" })).toBeInTheDocument();
    expect(screen.getByText(/already marked as mastered/i)).toBeInTheDocument();
    expect(screen.queryByText("Review verification scope")).not.toBeInTheDocument();
  });
});
