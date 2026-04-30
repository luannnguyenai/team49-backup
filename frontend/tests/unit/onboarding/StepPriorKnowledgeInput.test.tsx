import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import StepPriorKnowledgeInput from "@/components/onboarding/StepPriorKnowledgeInput";

describe("StepPriorKnowledgeInput", () => {
  it("collects manual prior profile and calls next for AI analysis", () => {
    const onPriorKnowledgeChange = vi.fn();
    const onCodingExperienceChange = vi.fn();
    const onNext = vi.fn();

    render(
      <StepPriorKnowledgeInput
        goalId="computer_vision"
        priorKnowledgeText=""
        codingExperienceText=""
        isAnalyzing={false}
        onPriorKnowledgeChange={onPriorKnowledgeChange}
        onCodingExperienceChange={onCodingExperienceChange}
        onBack={vi.fn()}
        onNext={onNext}
      />,
    );

    fireEvent.change(screen.getByLabelText("Knowledge you have studied"), {
      target: { value: "I have studied CNN and ResNet." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Intermediate coding skill" }));
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(onPriorKnowledgeChange).toHaveBeenCalledWith("I have studied CNN and ResNet.");
    expect(onCodingExperienceChange).toHaveBeenCalledWith(
      "Intermediate: comfortable with Python and basic PyTorch training/debugging, but not advanced production ML tooling.",
    );
    expect(onNext).toHaveBeenCalledOnce();
  });

  it("shows AI thinking while analysis is running", () => {
    render(
      <StepPriorKnowledgeInput
        goalId="nlp"
        priorKnowledgeText=""
        codingExperienceText=""
        isAnalyzing
        onPriorKnowledgeChange={vi.fn()}
        onCodingExperienceChange={vi.fn()}
        onBack={vi.fn()}
        onNext={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "AI thinking..." })).toBeDisabled();
  });
});
