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

    expect(screen.getByText("Which direction do you want to focus on?")).toBeInTheDocument();
    expect(screen.getByText("Computer Vision (CV)")).toBeInTheDocument();
    expect(screen.getByText("Natural Language Processing")).toBeInTheDocument();
  });

  it("Continue button is disabled when no goals are selected", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    const continueButton = screen.getByRole("button", { name: "Continue" });
    expect(continueButton).toBeDisabled();
  });

  it("clicking a card adds it to the store", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CV)"));

    expect(useOnboardingStore.getState().goalIds).toContain("computer_vision");
  });

  it("Continue button is enabled after selecting a goal", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CV)"));

    const continueButton = screen.getByRole("button", { name: "Continue" });
    expect(continueButton).not.toBeDisabled();
  });

  it("clicking another card replaces the current selection", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CV)"));
    expect(useOnboardingStore.getState().goalIds).toContain("computer_vision");

    fireEvent.click(screen.getByText("Natural Language Processing"));
    expect(useOnboardingStore.getState().goalIds).not.toContain("computer_vision");
    expect(useOnboardingStore.getState().goalIds).toEqual(["nlp"]);
  });

  it("clicking Continue calls onNext when a goal is selected", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Natural Language Processing"));
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(onNextMock).toHaveBeenCalledOnce();
  });

  it("clicking Continue does not call onNext when no goal is selected", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(onNextMock).not.toHaveBeenCalled();
  });

  it("only one goal can be selected at a time", () => {
    render(<StepGoalSelection onNext={onNextMock} />);

    fireEvent.click(screen.getByText("Computer Vision (CV)"));
    fireEvent.click(screen.getByText("Natural Language Processing"));

    const { goalIds } = useOnboardingStore.getState();
    expect(goalIds).toEqual(["nlp"]);
  });
});
