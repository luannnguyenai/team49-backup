import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PathItemResponse } from "@/types";
import TimelineBoard from "@/features/learning-path/components/TimelineBoard";
import { createLearningProfileForPath } from "@/features/learning-path/profile";
import { useLearningPathStore } from "@/features/learning-path/store";

function item(overrides: Partial<PathItemResponse> & { id: string; order_index: number }): PathItemResponse {
  return {
    id: overrides.id,
    learning_unit_id: overrides.learning_unit_id ?? overrides.id,
    learning_unit_title: overrides.learning_unit_title ?? `Unit ${overrides.id}`,
    section_title: overrides.section_title ?? "Lecture 2: Core",
    action: overrides.action ?? "standard_learn",
    estimated_hours: overrides.estimated_hours ?? 0.5,
    order_index: overrides.order_index,
    week_number: overrides.week_number ?? null,
    status: overrides.status ?? "pending",
    course_id: overrides.course_id ?? "CS230",
    course_title: overrides.course_title ?? "CS230: Deep Learning",
    canonical_unit_id: overrides.canonical_unit_id ?? null,
    segment_policy: overrides.segment_policy,
  };
}

describe("TimelineBoard", () => {
  beforeEach(() => {
    useLearningPathStore.setState({
      profile: createLearningProfileForPath("computer_vision", {
        weeklyHours: 1,
        source: "manual",
      }),
      items: [],
      timeline: null,
      selectedItemId: null,
      selectedSectionKey: null,
    });
  });

  it("renders only the next weekly lecture groups and hides skip/optional intro items", () => {
    const selectItem = vi.fn();
    useLearningPathStore.setState({
      items: [
        item({ id: "intro", order_index: 0, learning_unit_title: "Course intro", section_title: "Lecture 1: Introduction" }),
        item({ id: "done", order_index: 1, learning_unit_title: "Done unit", status: "completed" }),
        item({ id: "skip", order_index: 2, learning_unit_title: "Skipped unit", action: "skip" }),
        item({ id: "a", order_index: 3, learning_unit_title: "Next unit", estimated_hours: 0.5 }),
        item({ id: "b", order_index: 4, learning_unit_title: "Second unit", estimated_hours: 0.75 }),
        item({ id: "c", order_index: 5, learning_unit_title: "Outside budget", estimated_hours: 0.5 }),
      ],
      selectItem,
    });

    render(<TimelineBoard />);

    expect(screen.getByRole("heading", { name: "Việc cần học tiếp theo" })).toBeInTheDocument();
    expect(screen.getAllByText("1 giờ 15 phút").length).toBeGreaterThan(0);
    expect(screen.getByText("Next unit")).toBeInTheDocument();
    expect(screen.getByText("Second unit")).toBeInTheDocument();
    expect(screen.queryByText("Course intro")).not.toBeInTheDocument();
    expect(screen.queryByText("Skipped unit")).not.toBeInTheDocument();
    expect(screen.queryByText("Done unit")).not.toBeInTheDocument();
    expect(screen.queryByText("Outside budget")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Second unit/ }));
    expect(selectItem).toHaveBeenCalledWith("b");
  });
});
