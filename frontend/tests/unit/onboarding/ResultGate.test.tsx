import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ResultGate from "@/components/onboarding/ResultGate";
import type { TopicDecision } from "@/lib/placement-assessment-api";

// Mock the API call so tests don't make real network requests
vi.mock("@/lib/placement-assessment-api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/placement-assessment-api")>();
  return {
    ...actual,
    setTopicDecision: vi.fn().mockResolvedValue(undefined),
  };
});

import { setTopicDecision } from "@/lib/placement-assessment-api";

const mockResults: TopicDecision[] = [
  { topic_unit_id: "unit-skip", decision: "skip", score_pct: 90 },
  { topic_unit_id: "unit-relearn", decision: "relearn", score_pct: 20 },
  { topic_unit_id: "unit-review", decision: "review", score_pct: 55 },
];

describe("ResultGate", () => {
  const onConfirmMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders green badge for skip topics", () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    expect(screen.getByText("Mastered — đã miễn ✓")).toBeInTheDocument();
  });

  it("renders red badge for relearn topics", () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    expect(screen.getByText("Cần học lại ✗")).toBeInTheDocument();
  });

  it("renders two action buttons for review topics", () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    expect(screen.getByRole("button", { name: "Review (recommend)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bỏ qua" })).toBeInTheDocument();
  });

  it("Confirm button is disabled while review topics have no decision", () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    const confirmBtn = screen.getByRole("button", { name: "Xác nhận và tiếp tục" });
    expect(confirmBtn).toBeDisabled();
  });

  it("clicking Review calls setTopicDecision with user_choice=review", async () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    fireEvent.click(screen.getByRole("button", { name: "Review (recommend)" }));
    await waitFor(() => {
      expect(setTopicDecision).toHaveBeenCalledWith({
        topic_unit_id: "unit-review",
        user_choice: "review",
      });
    });
  });

  it("clicking Bỏ qua calls setTopicDecision with user_choice=skip", async () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    fireEvent.click(screen.getByRole("button", { name: "Bỏ qua" }));
    await waitFor(() => {
      expect(setTopicDecision).toHaveBeenCalledWith({
        topic_unit_id: "unit-review",
        user_choice: "skip",
      });
    });
  });

  it("Confirm button becomes enabled after all review topics are decided", async () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    fireEvent.click(screen.getByRole("button", { name: "Review (recommend)" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Xác nhận và tiếp tục" })).not.toBeDisabled();
    });
  });

  it("clicking Confirm calls onConfirm", async () => {
    render(<ResultGate results={mockResults} onConfirm={onConfirmMock} />);
    fireEvent.click(screen.getByRole("button", { name: "Review (recommend)" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Xác nhận và tiếp tục" })).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận và tiếp tục" }));
    expect(onConfirmMock).toHaveBeenCalledOnce();
  });

  it("renders Confirm enabled immediately when no review topics exist", () => {
    const noReviewResults: TopicDecision[] = [
      { topic_unit_id: "unit-skip", decision: "skip", score_pct: 90 },
      { topic_unit_id: "unit-relearn", decision: "relearn", score_pct: 20 },
    ];
    render(<ResultGate results={noReviewResults} onConfirm={onConfirmMock} />);
    expect(screen.getByRole("button", { name: "Xác nhận và tiếp tục" })).not.toBeDisabled();
  });
});
