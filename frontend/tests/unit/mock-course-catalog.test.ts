import { describe, expect, it } from "vitest";

import {
  findMockCourseOverview,
  getMockCourseStartDecision,
  mergeMockCourses,
} from "@/lib/mock-course-catalog";

describe("mock course catalog", () => {
  it("appends coming-soon mock courses without dropping real catalog items", () => {
    const response = mergeMockCourses({
      items: [
        {
          id: "course_cs231n",
          slug: "cs231n",
          title: "CS231n",
          short_description: "Real course",
          status: "ready",
          cover_image_url: null,
          hero_badge: "Available now",
          is_recommended: false,
        },
      ],
    });

    expect(response.items.some((item) => item.slug === "cs231n")).toBe(true);
    expect(response.items.some((item) => item.slug === "rag-production-systems")).toBe(true);
    expect(response.items.filter((item) => item.slug === "rag-production-systems")).toHaveLength(1);
  });

  it("returns a viewable overview and blocked start decision for mock courses", () => {
    const overview = findMockCourseOverview("agent-evaluation-playbook");
    const decision = getMockCourseStartDecision("agent-evaluation-playbook");

    expect(overview?.course.status).toBe("coming_soon");
    expect(overview?.overview.headline).toContain("sẽ mở sớm");
    expect(decision?.reason).toBe("course_unavailable");
  });
});
