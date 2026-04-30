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

    expect(screen.getByText("Quick")).toBeInTheDocument();
    expect(screen.getByText("up to 15 questions")).toBeInTheDocument();
    expect(screen.getByText("easy/medium")).toBeInTheDocument();
    expect(screen.getByText("Standard")).toBeInTheDocument();
    expect(screen.getByText("up to 30 questions")).toBeInTheDocument();
    expect(screen.getByText("Deep")).toBeInTheDocument();
    expect(screen.getByText("up to 50 questions")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Deep/i }));
    expect(useOnboardingStore.getState().assessmentDepth).toBe("deep");
  });

  it("calls navigation handlers", () => {
    render(<StepAssessmentDepth onBack={onBackMock} onNext={onNextMock} />);

    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(onBackMock).toHaveBeenCalledOnce();
    expect(onNextMock).toHaveBeenCalledOnce();
  });
});
