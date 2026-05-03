import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CourseStatusBadge from "@/components/course/CourseStatusBadge";

describe("CourseStatusBadge", () => {
  it("keeps semantic status colors and the pill badge shape", () => {
    render(<CourseStatusBadge status="ready" />);

    const badge = screen.getByText("Ready");
    expect(badge.className).toContain("rounded-full");
    expect(badge.className).toContain("border-emerald-200");
    expect(badge.className).toContain("bg-emerald-50");
  });
});
