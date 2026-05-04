import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ReplanScopeReviewStep from "@/components/replan/ReplanScopeReviewStep";

const units = [
  {
    canonicalUnitId: "unit_faster_rcnn",
    title: "Faster R-CNN",
    source: "matched_from_description" as const,
    knowledgePoints: [
      "Region Proposal Network",
      "Anchor boxes",
      "Two-stage detection",
      "RoI pooling / feature extraction",
    ],
    questionCounts: { easy: 3, medium: 4, hard: 2, application: 1 },
  },
  {
    canonicalUnitId: "unit_rcnn",
    title: "R-CNN",
    source: "suggested_prerequisite" as const,
    suggestedForTitle: "Faster R-CNN",
    knowledgePoints: ["Region proposals", "Selective search"],
    questionCounts: { easy: 2, medium: 3, hard: 1, application: 0 },
  },
];

describe("ReplanScopeReviewStep", () => {
  it("renders unit titles, knowledge points, source labels, and selected totals", () => {
    render(<ReplanScopeReviewStep units={units} onStartAssessment={vi.fn()} onDescribeAgain={vi.fn()} />);

    expect(screen.getByText("Faster R-CNN")).toBeInTheDocument();
    expect(screen.getByText("Region Proposal Network")).toBeInTheDocument();
    expect(screen.getByText("RoI pooling / feature extraction")).toBeInTheDocument();
    expect(screen.getByText("Source: Matched from your description")).toBeInTheDocument();
    expect(screen.getByText("Source: Suggested prerequisite for Faster R-CNN")).toBeInTheDocument();
    expect(screen.getByText("Easy 3 · Medium 4 · Hard 2 · Application 1")).toBeInTheDocument();
    expect(screen.getByText("Total selected questions: 16")).toBeInTheDocument();
    expect(screen.getByText("Estimated time: ~3 minutes")).toBeInTheDocument();
  });

  it("updates totals when units are unticked and difficulty filters change", () => {
    render(<ReplanScopeReviewStep units={units} onStartAssessment={vi.fn()} onDescribeAgain={vi.fn()} />);

    fireEvent.click(screen.getByRole("checkbox", { name: "Include R-CNN" }));
    expect(screen.getByText("Total selected questions: 10")).toBeInTheDocument();
    expect(screen.getByText("Estimated time: ~2 minutes")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Difficulty filter for Faster R-CNN"), {
      target: { value: "easy_medium" },
    });
    expect(screen.getByText("Total selected questions: 7")).toBeInTheDocument();
    expect(screen.getByText("Estimated time: ~2 minutes")).toBeInTheDocument();
  });

  it("calls navigation handlers", () => {
    const onStartAssessment = vi.fn();
    const onDescribeAgain = vi.fn();

    render(
      <ReplanScopeReviewStep
        units={units}
        onStartAssessment={onStartAssessment}
        onDescribeAgain={onDescribeAgain}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Describe again" }));
    fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));

    expect(onDescribeAgain).toHaveBeenCalledOnce();
    expect(onStartAssessment).toHaveBeenCalledOnce();
  });
});
