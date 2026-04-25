import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StepGoalSelection from "@/components/onboarding/StepGoalSelection";
import { useOnboardingStore } from "@/stores/onboardingStore";

describe("StepGoalSelection", () => {
  const onNextMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useOnboardingStore.getState().reset();
  });

  it("renders 2 goal cards", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    expect(screen.getByText("Computer Vision (CS231n)")).toBeInTheDocument();
    expect(screen.getByText("Natural Language Processing (CS224n)")).toBeInTheDocument();
  });

  it("Continue button is disabled when no goals are selected", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    const continueButton = screen.getByRole("button", { name: "Tiếp tục" });
    expect(continueButton).toBeDisabled();
  });

  it("clicking a card adds it to the store", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CS231n)"));

    expect(useOnboardingStore.getState().goalIds).toContain("computer_vision");
  });

  it("Continue button is enabled after selecting a goal", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CS231n)"));

    const continueButton = screen.getByRole("button", { name: "Tiếp tục" });
    expect(continueButton).not.toBeDisabled();
  });

  it("clicking a selected card deselects it", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CS231n)"));
    expect(useOnboardingStore.getState().goalIds).toContain("computer_vision");

    fireEvent.click(screen.getByText("Computer Vision (CS231n)"));
    expect(useOnboardingStore.getState().goalIds).not.toContain("computer_vision");
  });

  it("clicking Continue calls onNext when a goal is selected", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Natural Language Processing (CS224n)"));
    fireEvent.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(onNextMock).toHaveBeenCalledOnce();
  });

  it("clicking Continue does not call onNext when no goal is selected", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(onNextMock).not.toHaveBeenCalled();
  });

  it("multiple goals can be selected simultaneously", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CS231n)"));
    fireEvent.click(screen.getByText("Natural Language Processing (CS224n)"));

    const { goalIds } = useOnboardingStore.getState();
    expect(goalIds).toContain("computer_vision");
    expect(goalIds).toContain("nlp");
    expect(goalIds).toHaveLength(2);
  });
});
