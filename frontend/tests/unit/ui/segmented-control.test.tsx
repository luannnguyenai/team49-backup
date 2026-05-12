import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SegmentedControl from "@/components/ui/SegmentedControl";

describe("SegmentedControl", () => {
  it("renders the active option and emits changes for inactive options", () => {
    const onChange = vi.fn();

    render(
      <SegmentedControl
        ariaLabel="Planner view"
        value="timeline"
        onChange={onChange}
        options={[
          { label: "Timeline", value: "timeline" },
          { label: "Graph", value: "graph" },
        ]}
      />,
    );

    expect(screen.getByRole("tab", { name: "Timeline" })).toHaveAttribute("aria-selected", "true");

    fireEvent.click(screen.getByRole("tab", { name: "Graph" }));

    expect(onChange).toHaveBeenCalledWith("graph");
  });
});
