import { describe, expect, it } from "vitest";
import { onboardingSchema } from "@/lib/onboarding-schema";

describe("onboardingSchema", () => {
  it("defaults preferred learning method to video", () => {
    const parsed = onboardingSchema.parse({
      goal_ids: [],
      known_unit_ids: [],
      desired_section_ids: [],
      selected_course_ids: [],
      available_hours_per_week: 5,
      target_deadline: "2026-05-01",
    });

    expect(parsed.preferred_method).toBe("video");
  });
});
