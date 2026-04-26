import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StepPlacementTest from "@/components/onboarding/StepPlacementTest";
import { useOnboardingStore } from "@/stores/onboardingStore";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockQuestions = [
  {
    item_id: "q1",
    question_text: "What is a convolution?",
    options: { A: "Option A", B: "Option B", C: "Option C", D: "Option D" },
    topic_unit_id: "unit-cnn",
  },
  {
    item_id: "q2",
    question_text: "What is pooling?",
    options: { A: "Opt A2", B: "Opt B2", C: "Opt C2", D: "Opt D2" },
    topic_unit_id: "unit-cnn",
  },
];

const mockStartResponse = {
  session_id: "sess-123",
  questions: mockQuestions,
  processed_unit_ids: ["unit-cnn"],
};

const mockSubmitResponse = {
  topic_decisions: [
    { topic_unit_id: "unit-cnn", decision: "skip" as const, score_pct: 90 },
  ],
  overall_score_pct: 90,
};

// ---------------------------------------------------------------------------
// Mock API module
// ---------------------------------------------------------------------------

vi.mock("@/lib/placement-assessment-api", () => ({
  startPlacementAssessment: vi.fn(),
  submitPlacementAssessment: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function importApi() {
  return await import("@/lib/placement-assessment-api");
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("StepPlacementTest", () => {
  const onCompleteMock = vi.fn();
  const onSkipMock = vi.fn();

  const defaultProps = {
    sessionId: "sess-123",
    unitIds: ["unit-cnn"],
    onComplete: onCompleteMock,
    onSkip: onSkipMock,
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    useOnboardingStore.getState().reset();

    const api = await importApi();
    vi.mocked(api.startPlacementAssessment).mockResolvedValue(mockStartResponse);
    vi.mocked(api.submitPlacementAssessment).mockResolvedValue(mockSubmitResponse);
  });

  it("shows loading state initially", () => {
    render(<StepPlacementTest {...defaultProps} />);
    expect(screen.getByText("Đang tải câu hỏi...")).toBeInTheDocument();
  });

  it("renders questions after start API resolves", async () => {
    render(<StepPlacementTest {...defaultProps} />);
    await waitFor(() =>
      expect(screen.getByText("What is a convolution?")).toBeInTheDocument(),
    );
    expect(screen.getByText("What is pooling?")).toBeInTheDocument();
    expect(screen.getByText("Option A")).toBeInTheDocument();
  });

  it("Submit button is disabled until all questions are answered", async () => {
    render(<StepPlacementTest {...defaultProps} />);
    await waitFor(() => screen.getByText("What is a convolution?"));

    const submitBtn = screen.getByRole("button", { name: "Nộp bài" });
    expect(submitBtn).toBeDisabled();

    // Answer only first question
    fireEvent.click(screen.getByText("Option A"));
    expect(submitBtn).toBeDisabled();
  });

  it("Submit button is enabled when all questions are answered", async () => {
    render(<StepPlacementTest {...defaultProps} />);
    await waitFor(() => screen.getByText("What is a convolution?"));

    const submitBtn = screen.getByRole("button", { name: "Nộp bài" });

    fireEvent.click(screen.getByText("Option A"));   // answer q1
    fireEvent.click(screen.getByText("Opt A2"));      // answer q2

    expect(submitBtn).not.toBeDisabled();
  });

  it("calls onComplete with topic_decisions after submit succeeds", async () => {
    render(<StepPlacementTest {...defaultProps} />);
    await waitFor(() => screen.getByText("What is a convolution?"));

    fireEvent.click(screen.getByText("Option A"));
    fireEvent.click(screen.getByText("Opt A2"));

    fireEvent.click(screen.getByRole("button", { name: "Nộp bài" }));

    // Results screen shows "Hoàn thành"
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Hoàn thành" })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Hoàn thành" }));
    expect(onCompleteMock).toHaveBeenCalledWith(mockSubmitResponse.topic_decisions);
  });

  it("shows results with decision labels after submit", async () => {
    render(<StepPlacementTest {...defaultProps} />);
    await waitFor(() => screen.getByText("What is a convolution?"));

    fireEvent.click(screen.getByText("Option A"));
    fireEvent.click(screen.getByText("Opt A2"));
    fireEvent.click(screen.getByRole("button", { name: "Nộp bài" }));

    await waitFor(() =>
      expect(screen.getByText("✓ Skip")).toBeInTheDocument(),
    );
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("shows error message if start API fails", async () => {
    const api = await importApi();
    vi.mocked(api.startPlacementAssessment).mockRejectedValueOnce(new Error("network error"));

    render(<StepPlacementTest {...defaultProps} />);
    await waitFor(() =>
      expect(screen.getByText("Không thể tải câu hỏi. Vui lòng thử lại.")).toBeInTheDocument(),
    );
  });

  it("calls onSkip when skip link is clicked", async () => {
    render(<StepPlacementTest {...defaultProps} />);
    await waitFor(() => screen.getByText("What is a convolution?"));

    fireEvent.click(screen.getByRole("button", { name: "Bỏ qua" }));
    expect(onSkipMock).toHaveBeenCalledOnce();
  });
});
