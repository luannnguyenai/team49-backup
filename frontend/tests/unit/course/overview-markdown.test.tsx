import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CourseOverview from "@/components/course/CourseOverview";
import type { CourseOverviewResponse } from "@/types";

describe("CourseOverview markdown rendering", () => {
  it("renders summary_markdown as formatted markdown instead of plain text", () => {
    const data: CourseOverviewResponse = {
      course: {
        id: "course_cs231n",
        slug: "cs231n",
        title: "CS231n: Deep Learning for Computer Vision",
        short_description: "Deep learning foundations for computer vision.",
        status: "ready",
        cover_image_url: null,
        hero_badge: "Available now",
        is_recommended: false,
      },
      overview: {
        headline: "Build deep intuition for modern vision systems",
        subheadline: "Learn the path from linear classifiers to transformers.",
        summary_markdown: "Learn **core vision models**.\n\n- CNNs\n- Transformers",
        learning_outcomes: ["Understand modern vision architectures"],
        target_audience: "Learners with Python basics",
        prerequisites_summary: "Comfort with Python",
        estimated_duration_text: "18 lectures",
        structure_snapshot: { summary: "Lecture-first course" },
        cta_label: "Start learning",
      },
      entry: {
        decision: "redirect",
        target: "/courses/cs231n/start",
        reason: "learning_ready",
      },
    };

    render(<CourseOverview data={data} onStart={vi.fn()} />);

    expect(screen.getByText("core vision models", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("CNNs", { selector: "li" })).toBeInTheDocument();
    expect(screen.getByText("Transformers", { selector: "li" })).toBeInTheDocument();
  });
});
