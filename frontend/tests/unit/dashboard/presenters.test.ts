import { describe, expect, it } from "vitest";

import {
  buildDashboardCourseCardModel,
  filterDashboardCourses,
} from "@/features/dashboard/presenters";
import { CS224N_ITEM, CS231N_ITEM, CS231N_RECOMMENDED } from "@/tests/fixtures/coursePlatform";

describe("dashboard presenters", () => {
  it("routes ready courses to their own start page", () => {
    const model = buildDashboardCourseCardModel(CS231N_ITEM);

    expect(model.href).toBe("/courses/cs231n/start");
    expect(model.ctaLabel).toBe("Bắt đầu học");
  });

  it("routes coming-soon courses to their own overview page", () => {
    const model = buildDashboardCourseCardModel(CS224N_ITEM);

    expect(model.href).toBe("/courses/cs224n");
    expect(model.ctaLabel).toBe("Xem tổng quan");
  });

  it("prefers recommended courses in the for-you tab", () => {
    const courses = [CS231N_RECOMMENDED, CS224N_ITEM];

    expect(filterDashboardCourses(courses, "for-you")).toEqual([CS231N_RECOMMENDED]);
  });

  it("falls back to all courses when there are no recommendations", () => {
    const courses = [CS231N_ITEM, CS224N_ITEM];

    expect(filterDashboardCourses(courses, "for-you")).toEqual(courses);
  });
});
