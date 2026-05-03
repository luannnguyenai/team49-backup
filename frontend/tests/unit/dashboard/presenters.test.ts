import { describe, expect, it } from "vitest";

import {
  buildDashboardCourseCardModel,
  filterDashboardCourses,
} from "@/features/dashboard/presenters";
import {
  COMING_SOON_ITEM,
  CS224N_ITEM,
  CS231N_ITEM,
  CS231N_RECOMMENDED,
} from "@/tests/fixtures/coursePlatform";

describe("dashboard presenters", () => {
  it("routes ready courses to their own start page", () => {
    const model = buildDashboardCourseCardModel(CS231N_ITEM);

    expect(model.href).toBe("/courses/cs231n/start");
    expect(model.ctaLabel).toBe("Start learning");
  });

  it("routes coming-soon courses to their own overview page", () => {
    const model = buildDashboardCourseCardModel(COMING_SOON_ITEM);

    expect(model.href).toBe("/courses/upcoming-ai");
    expect(model.ctaLabel).toBe("View overview");
  });

  it("prefers recommended courses in the for-you tab", () => {
    const courses = [CS231N_RECOMMENDED, CS224N_ITEM];

    expect(filterDashboardCourses(courses, "for-you")).toEqual([CS231N_RECOMMENDED]);
  });

  it("returns an empty list when there are no recommendations", () => {
    const courses = [CS231N_ITEM, CS224N_ITEM];

    expect(filterDashboardCourses(courses, "for-you")).toEqual([]);
  });
});
