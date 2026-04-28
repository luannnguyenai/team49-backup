import { describe, expect, it } from "vitest";
import {
  buildAssessmentNextHref,
  buildPostOnboardingHref,
} from "@/components/onboarding/onboardingNavigation";

describe("onboarding navigation", () => {
  it("routes users with placement checks through assessment and then back to learn", () => {
    expect(
      buildPostOnboardingHref({
        hasAssessmentUnits: true,
        requestedNext: null,
      }),
    ).toBe("/assessment?next=%2Flearn");
  });

  it("preserves an explicit next target when one is provided", () => {
    expect(
      buildPostOnboardingHref({
        hasAssessmentUnits: true,
        requestedNext: "/dashboard",
      }),
    ).toBe("/assessment?next=%2Fdashboard");
  });

  it("sends beginners or empty assessments directly to learn by default", () => {
    expect(
      buildPostOnboardingHref({
        hasAssessmentUnits: false,
        requestedNext: null,
      }),
    ).toBe("/learn");
  });

  it("defaults assessment results CTA to learn", () => {
    expect(buildAssessmentNextHref(null)).toBe("/learn");
    expect(buildAssessmentNextHref("/dashboard")).toBe("/dashboard");
  });
});
