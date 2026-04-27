import { describe, expect, it } from "vitest";
import { onboardingSchema } from "@/lib/onboarding-schema";

describe("onboardingSchema", () => {
  it("defaults hidden pacing fields and preferred learning method", () => {
    const parsed = onboardingSchema.parse({
      goal_ids: [],
      known_unit_ids: [],
      desired_section_ids: [],
      selected_course_ids: [],
    });

    expect(parsed.available_hours_per_week).toBe(5);
    expect(parsed.target_deadline).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(parsed.preferred_method).toBe("video");
  });
});
