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

  it("renders section topics and visible learning units", () => {
    render(
      <RoadmapPlanner
        items={[
          item({ id: "hidden", order_index: 0, segment_policy: "hidden" }),
          item({ id: "a", order_index: 1, learning_unit_title: "Neural Networks" }),
        ]}
      />,
    );

    expect(screen.getByRole("button", { name: /Deep Learning 1 bài học/ })).toBeInTheDocument();
    expect(screen.getByText("Neural Networks")).toBeInTheDocument();
    expect(screen.queryByText("Unit hidden")).not.toBeInTheDocument();
  });

  it("calls unit selection when a unit card is clicked", () => {
    const onSelectItem = vi.fn();

    render(
      <RoadmapPlanner
        items={[item({ id: "a", order_index: 0, learning_unit_title: "CNN Basics" })]}
        onSelectItem={onSelectItem}
      />,
    );

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

    expect(screen.getByText("End quiz đã mở")).toBeInTheDocument();
  });

  it("renders a path-required state for missing concrete path data", () => {
    render(<PathRequiredState />);

    expect(screen.getByText("Chọn lộ trình trước khi học")).toBeInTheDocument();
  });

  it("lets the user pick exactly one temporary path while onboarding is unavailable", () => {
    render(<PathRequiredState />);

    fireEvent.click(screen.getByRole("button", { name: /Deep Learning → NLP/ }));

    expect(useLearningPathStore.getState().profile).toMatchObject({
      pathKey: "dl_nlp",
      selectedCourseIds: ["CS230", "CS224n"],
      source: "manual",
    });
  });
});
