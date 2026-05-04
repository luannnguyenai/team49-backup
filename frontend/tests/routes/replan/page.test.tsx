import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReplanPage from "@/app/replan/page";
import { readPendingCanonicalAssessment } from "@/lib/canonical-assessment-session";
import { replanApi } from "@/lib/replan-api";

const navigationMock = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
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
    });
    vi.mocked(replanApi.startAssessment).mockResolvedValue({
      sessionId: "test-session-123",
      totalQuestions: 10,
      canonicalUnitIds: ["unit_faster_rcnn"],
      unitNameMap: { unit_faster_rcnn: "Faster R-CNN" },
      assessmentHref: "/assessment?next=%2Flearn",
    });
  });

  it("renders a scope-builder wizard without a cancel flow", () => {
    render(<ReplanPage />);

    expect(screen.getByRole("heading", { name: "Tối ưu lộ trình học" })).toBeInTheDocument();
    expect(screen.getByText(/Mô tả này không tự động bỏ qua bài học/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Bạn đã biết phần nào rồi?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /cancel/i })).not.toBeInTheDocument();
  });

  it("shows guardrail feedback before continuing", () => {
    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("Bạn đã biết phần nào rồi?"), {
      target: { value: "skip all" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(/không thể tạo bài kiểm tra để bỏ toàn bộ lộ trình/i)).toBeInTheDocument();
  });

  it("continues from a valid claim to scope review and starts the existing assessment flow", async () => {
    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("Bạn đã biết phần nào rồi?"), {
      target: { value: "I know Faster R-CNN and CNN feature extraction" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    // Wait for API call to complete
    expect(await screen.findByText("Review verification scope")).toBeInTheDocument();
    expect(replanApi.analyze).toHaveBeenCalledWith("I know Faster R-CNN and CNN feature extraction");
    expect(screen.getByText("Faster R-CNN")).toBeInTheDocument();
    expect(screen.getByText("Region Proposal Network")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));

    // Verify startAssessment API was called
    expect(replanApi.startAssessment).toHaveBeenCalledWith([
      { canonicalUnitId: "unit_faster_rcnn", difficultyFilter: "all" },
    ]);

    expect(readPendingCanonicalAssessment()).toMatchObject({
      canonicalUnitIds: ["unit_faster_rcnn"],
      unitNameMap: {
        unit_faster_rcnn: "Faster R-CNN",
      },
      assessmentDepth: "deep",
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
    });

    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("Bạn đã biết phần nào rồi?"), {
      target: { value: "I know Faster R-CNN and CNN feature extraction" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("dialog", { name: /Mình tìm thấy một vài phần nền tảng liên quan/i })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "Include R-CNN" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Thêm vào bài kiểm tra" }));

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
    });

    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("Bạn đã biết phần nào rồi?"), {
      target: { value: "I already mastered Faster R-CNN" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByText(/Không tìm thấy unit nào/i)).toBeInTheDocument();
    expect(screen.queryByText("Review verification scope")).not.toBeInTheDocument();
  });
});
