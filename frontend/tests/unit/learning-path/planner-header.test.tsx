import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PlannerHeader from "@/features/learning-path/components/PlannerHeader";
import { createLearningProfileForPath } from "@/features/learning-path/profile";

describe("PlannerHeader", () => {
  it("shows a compact path switcher next to the goal title", () => {
    const onProfileChange = vi.fn();
    const profile = createLearningProfileForPath("computer_vision", {
      weeklyHours: 5,
      source: "manual",
    });

    render(
      <PlannerHeader
        profile={profile}
        summary={{ total_units: 12, completed_units: 2, in_progress_units: 1 }}
        view="graph"
        onViewChange={vi.fn()}
        onProfileChange={onProfileChange}
      />,
    );

    expect(screen.queryByText(/Render theo path cụ thể/)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Computer Vision" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Đổi" }));

    expect(screen.getByRole("dialog", { name: "Đổi lộ trình" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Natural Language Processing/ }));

    expect(onProfileChange).toHaveBeenCalledWith(
      expect.objectContaining({
        pathKey: "nlp",
        selectedCourseIds: ["CS230", "CS224n"],
        weeklyHours: 5,
        source: "manual",
      }),
    );
  });
});
