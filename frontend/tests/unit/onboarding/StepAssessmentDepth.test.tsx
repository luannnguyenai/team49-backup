import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StepAssessmentDepth from "@/components/onboarding/StepAssessmentDepth";
import { useOnboardingStore } from "@/stores/onboardingStore";

describe("StepAssessmentDepth", () => {
  const onNextMock = vi.fn();
  const onBackMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useOnboardingStore.getState().reset();
  });

  it("lets the user choose assessment depth after schedule", () => {
    render(<StepAssessmentDepth onBack={onBackMock} onNext={onNextMock} />);

    expect(screen.getByText("Nhanh")).toBeInTheDocument();
    expect(screen.getByText("tối đa 15 câu")).toBeInTheDocument();
    expect(screen.getByText("easy/medium")).toBeInTheDocument();
    expect(screen.getByText("Vừa")).toBeInTheDocument();
    expect(screen.getByText("tối đa 30 câu")).toBeInTheDocument();
    expect(screen.getByText("Kỹ")).toBeInTheDocument();
    expect(screen.getByText("tối đa 50 câu")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Kỹ/i }));
    expect(useOnboardingStore.getState().assessmentDepth).toBe("deep");
  });

  it("calls navigation handlers", () => {
    render(<StepAssessmentDepth onBack={onBackMock} onNext={onNextMock} />);

    fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
    fireEvent.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(onBackMock).toHaveBeenCalledOnce();
    expect(onNextMock).toHaveBeenCalledOnce();
  });
});
