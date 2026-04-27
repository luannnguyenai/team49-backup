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

    fireEvent.change(screen.getByLabelText("Kiến thức bạn đã học"), {
      target: { value: "Tôi đã học CNN và ResNet." },
    });
    fireEvent.change(screen.getByLabelText("Kỹ năng coding ML"), {
      target: { value: "Python và PyTorch cơ bản." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(onPriorKnowledgeChange).toHaveBeenCalledWith("Tôi đã học CNN và ResNet.");
    expect(onCodingExperienceChange).toHaveBeenCalledWith("Python và PyTorch cơ bản.");
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

