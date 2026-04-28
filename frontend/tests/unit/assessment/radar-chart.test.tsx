import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RadarChart from "@/components/assessment/RadarChart";

const SAMPLE_SKILLS = [
  { label: "Machine Learning", value: 72, level: "developing" },
  { label: "Deep Learning", value: 64, level: "developing" },
  { label: "Computer Vision", value: 58, level: "developing" },
  { label: "Natural Language Processing", value: 69, level: "proficient" },
  { label: "Large Language Models", value: 77, level: "proficient" },
];

describe("RadarChart", () => {
  it("adds outer padding in the viewBox so axis labels are not clipped", () => {
    render(<RadarChart data={SAMPLE_SKILLS} size={280} />);

    const svg = screen.getByRole("img", { name: "Mastery radar chart" });
    expect(svg).toHaveAttribute("viewBox", expect.stringMatching(/^0 0 (?!280 280\b)\d+(\.\d+)? \d+(\.\d+)?$/));

    const viewBox = svg.getAttribute("viewBox");
    const width = Number(viewBox?.split(" ")[2]);
    expect(width).toBeGreaterThan(392);
  });

  it("renders full skill labels instead of truncating them with ellipses", () => {
    render(<RadarChart data={SAMPLE_SKILLS} size={280} />);

    expect(screen.getByText("Machine Learning")).toBeInTheDocument();
    expect(screen.getByText("Computer Vision")).toBeInTheDocument();
    expect(screen.queryByText("Machine Learn…")).not.toBeInTheDocument();
    expect(screen.queryByText("Computer Visi…")).not.toBeInTheDocument();
  });

  it("offsets grid markers away from the axis so they remain readable", () => {
    render(<RadarChart data={SAMPLE_SKILLS} size={280} />);

    const marker = screen.getByText("100");
    expect(marker.getAttribute("text-anchor")).toBe("start");
  });
});
