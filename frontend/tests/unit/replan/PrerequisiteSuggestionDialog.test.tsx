import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PrerequisiteSuggestionDialog from "@/components/replan/PrerequisiteSuggestionDialog";

const suggestions = [
  {
    canonicalUnitId: "unit_rcnn",
    title: "R-CNN",
    reason: "Prerequisite chain for Faster R-CNN",
    depth: 1,
  },
  {
    canonicalUnitId: "unit_cnn",
    title: "CNN foundations",
    reason: "Foundation for two-stage detectors",
    depth: 2,
  },
];

describe("PrerequisiteSuggestionDialog", () => {
  it("shows suggested prerequisite units without auto-accepting them", () => {
    const onInclude = vi.fn();
    render(
      <PrerequisiteSuggestionDialog
        suggestions={suggestions}
        onInclude={onInclude}
        onSkip={vi.fn()}
      />,
    );

    expect(screen.getByRole("dialog", { name: "Found related foundational topics" })).toBeInTheDocument();
    expect(screen.getByText("R-CNN")).toBeInTheDocument();
    expect(screen.getByText("CNN foundations")).toBeInTheDocument();
    expect(onInclude).not.toHaveBeenCalled();
  });

  it("calls include or skip based on the user's decision", () => {
    const onInclude = vi.fn();
    const onSkip = vi.fn();
    const { rerender } = render(
      <PrerequisiteSuggestionDialog
        suggestions={suggestions}
        onInclude={onInclude}
        onSkip={onSkip}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Add to assessment" }));
    expect(onInclude).toHaveBeenCalledWith(suggestions);
    expect(onSkip).not.toHaveBeenCalled();

    rerender(
      <PrerequisiteSuggestionDialog
        suggestions={suggestions}
        onInclude={onInclude}
        onSkip={onSkip}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(onSkip).toHaveBeenCalledOnce();
  });
});
