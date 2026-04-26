import { describe, expect, it } from "vitest";

import {
  buildCatalogPageViewModel,
  buildCourseOverviewViewModel,
} from "@/features/course-platform/presenters";
import {
  CS224N_OVERVIEW,
  CS231N_OVERVIEW,
  CS231N_ITEM,
  CS231N_RECOMMENDED,
  CS224N_ITEM,
} from "@/tests/fixtures/coursePlatform";

describe("course platform presenters", () => {
  describe("buildCatalogPageViewModel", () => {
    it("returns a public catalog view model for unauthenticated visitors", () => {
      const model = buildCatalogPageViewModel({
        user: null,
        activeView: "all",
        allCourses: [CS231N_ITEM, CS224N_ITEM],
        recommendedCourses: [],
        hasRecommendations: false,
      });

      expect(model.hero.title).toContain("Start from the catalog");
      expect(model.catalog.kicker).toBe("Public catalog");
      expect(model.catalog.title).toBe("Explore available courses");
      expect(model.catalog.showTabs).toBe(false);
      expect(model.catalog.displayedCourses).toEqual([CS231N_ITEM, CS224N_ITEM]);
      expect(model.hero.primaryAction).toEqual({
        href: "/login",
        label: "Sign in to continue",
      });
    });

    it("returns a personalized catalog view model when recommendations exist", () => {
      const model = buildCatalogPageViewModel({
        user: {
          id: "user_1",
          full_name: "Test User",
          is_onboarded: true,
        },
        activeView: "recommended",
        allCourses: [CS231N_ITEM, CS224N_ITEM],
        recommendedCourses: [CS231N_RECOMMENDED],
        hasRecommendations: true,
      });

      expect(model.hero.title).toBe("Welcome back, Test");
      expect(model.catalog.kicker).toBe("Your catalog");
      expect(model.catalog.title).toBe("Your learning path");
      expect(model.catalog.showTabs).toBe(true);
      expect(model.catalog.displayedCourses).toEqual([CS231N_RECOMMENDED]);
      expect(model.hero.primaryAction).toBeNull();
    });
  });

  describe("buildCourseOverviewViewModel", () => {
    it("builds a startable overview model for ready courses", () => {
      const model = buildCourseOverviewViewModel({
        data: CS231N_OVERVIEW,
        isStarting: false,
      });

      expect(model.cta.label).toBe("Start learning");
      expect(model.cta.disabled).toBe(false);
      expect(model.bannerMessage).toBeNull();
      expect(model.courseTitle).toBe(CS231N_OVERVIEW.course.title);
    });

    it("builds a blocked overview model for coming-soon courses", () => {
      const model = buildCourseOverviewViewModel({
        data: CS224N_OVERVIEW,
        isStarting: false,
      });

      expect(model.cta.label).toBe("Coming soon");
      expect(model.cta.disabled).toBe(true);
      expect(model.bannerMessage).toContain("visible in the catalog");
    });
  });
});
