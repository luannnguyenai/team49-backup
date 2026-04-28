import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PathItemResponse } from "@/types";
import RoadmapPlanner from "@/features/learning-path/components/RoadmapPlanner";
import PathRequiredState from "@/features/learning-path/components/PathRequiredState";
import { useLearningPathStore } from "@/features/learning-path/store";

function item(overrides: Partial<PathItemResponse> & { id: string; order_index: number }): PathItemResponse {
  return {
    id: overrides.id,
    learning_unit_id: overrides.learning_unit_id ?? overrides.id,
    learning_unit_title: overrides.learning_unit_title ?? `Unit ${overrides.id}`,
    section_title: overrides.section_title ?? "Deep Learning",
    action: overrides.action ?? "standard_learn",
    estimated_hours: overrides.estimated_hours ?? 1,
    order_index: overrides.order_index,
    week_number: overrides.week_number ?? null,
    status: overrides.status ?? "pending",
    canonical_unit_id: overrides.canonical_unit_id ?? null,
    segment_policy: overrides.segment_policy,
    phase_tag: overrides.phase_tag,
    is_locked: overrides.is_locked,
  };
}

describe("RoadmapPlanner", () => {
  beforeEach(() => {
    useLearningPathStore.setState({
      profile: null,
      previousProfile: null,
      generatedTopologyHash: null,
    });
  });

  it("renders collapsed lectures and expands visible learning units", () => {
    render(
      <RoadmapPlanner
        items={[
          item({ id: "hidden", order_index: 0, segment_policy: "hidden" }),
          item({ id: "a", order_index: 1, learning_unit_title: "Neural Networks" }),
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: /Deep Learning/ })).toBeInTheDocument();
    expect(screen.queryByText("Neural Networks")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Expand Deep Learning/ }));

    expect(screen.getByText("Neural Networks")).toBeInTheDocument();
    expect(screen.queryByText("Unit hidden")).not.toBeInTheDocument();
  });

  it("hides skipped/reference items but keeps locked phase B units as upcoming path content", () => {
    render(
      <RoadmapPlanner
        items={[
          item({ id: "core", order_index: 0, learning_unit_title: "Core Unit" }),
          item({ id: "skip", order_index: 1, learning_unit_title: "Already Mastered", action: "skip" }),
          item({ id: "skipped", order_index: 2, learning_unit_title: "User Skipped", status: "skipped" }),
          item({ id: "reference", order_index: 3, learning_unit_title: "Reference Only", segment_policy: "reference" }),
          item({ id: "hidden", order_index: 4, learning_unit_title: "Hidden Logistics", segment_policy: "hidden" }),
          item({
            id: "locked",
            order_index: 5,
            learning_unit_title: "Locked Phase B",
            phase_tag: "phase_b",
            is_locked: true,
          }),
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Expand Deep Learning/ }));

    expect(screen.getByText("Core Unit")).toBeInTheDocument();
    expect(screen.queryByText("Already Mastered")).not.toBeInTheDocument();
    expect(screen.queryByText("User Skipped")).not.toBeInTheDocument();
    expect(screen.queryByText("Reference Only")).not.toBeInTheDocument();
    expect(screen.queryByText("Hidden Logistics")).not.toBeInTheDocument();
    expect(screen.getByText("Locked Phase B")).toBeInTheDocument();
  });

  it("calls unit selection when a unit card is clicked", () => {
    const onSelectItem = vi.fn();

    render(
      <RoadmapPlanner
        items={[item({ id: "a", order_index: 0, learning_unit_title: "CNN Basics" })]}
        onSelectItem={onSelectItem}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Expand Deep Learning/ }));
    fireEvent.click(screen.getByRole("button", { name: /CNN Basics/ }));

    expect(onSelectItem).toHaveBeenCalledWith("a");
  });

  it("shows player insight only for the active learning unit", () => {
    render(
      <RoadmapPlanner
        items={[
          item({ id: "a", learning_unit_id: "unit-a", order_index: 0, learning_unit_title: "Active Unit" }),
          item({ id: "b", learning_unit_id: "unit-b", order_index: 1, learning_unit_title: "Other Unit" }),
        ]}
        currentProgress={{
          learning_unit_id: "unit-a",
          video_finished: true,
          has_end_quiz: true,
          inline_quiz: {},
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Expand Deep Learning/ }));

    expect(screen.getByText("End quiz đã mở")).toBeInTheDocument();
  });

  it("renders a path-required state for missing concrete path data", () => {
    render(<PathRequiredState />);

    expect(screen.getByText("Chọn lộ trình trước khi học")).toBeInTheDocument();
  });

  it("lets the user pick exactly one temporary path while onboarding is unavailable", () => {
    render(<PathRequiredState />);

    fireEvent.click(screen.getByRole("button", { name: /Natural Language Processing/ }));

    expect(useLearningPathStore.getState().profile).toMatchObject({
      pathKey: "nlp",
      selectedCourseIds: ["CS230", "CS224n"],
      source: "manual",
    });
  });
});
