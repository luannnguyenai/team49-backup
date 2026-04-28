import { describe, expect, it } from "vitest";
import {
  createLearningProfileForPath,
  isProfilePathStale,
  onboardingToLearningProfile,
  profileHash,
  topologyHash,
} from "@/features/learning-path/profile";

describe("learning path profile", () => {
  it("creates a concrete CV path without mutating display order", () => {
    const profile = createLearningProfileForPath("computer_vision", {
      weeklyHours: 6,
      source: "onboarding",
    });

    expect(profile).toMatchObject({
      pathKey: "computer_vision",
      label: "Computer Vision",
      startCourse: "CS230",
      selectedCourseIds: ["CS230", "CS231n"],
      weeklyHours: 6,
      source: "onboarding",
    });
    expect(profile.generatedFromProfileHash).toBe(profileHash(profile));
    expect(profile.topologyHash).toBe(topologyHash(profile));
  });

  it("uses sorted course IDs only for hash stability", () => {
    const first = createLearningProfileForPath("nlp", {
      weeklyHours: null,
      source: "manual",
    });
    const sameTopologyDifferentOrder = {
      ...first,
      selectedCourseIds: ["CS224n", "CS230"],
    };

    expect(first.selectedCourseIds).toEqual(["CS230", "CS224n"]);
    expect(topologyHash(first)).toBe(topologyHash(sameTopologyDifferentOrder));
  });

  it("normalizes lowercase onboarding path courses through the selected path", () => {
    const profile = onboardingToLearningProfile({
      selected_path_key: "nlp",
      available_hours_per_week: 8,
    });

    expect(profile.pathKey).toBe("nlp");
    expect(profile.selectedCourseIds).toEqual(["CS230", "CS224n"]);
    expect(profile.pacingHash).toBe("weekly:8");
  });

  it("rejects missing, unknown, or combined planner paths", () => {
    expect(() =>
      onboardingToLearningProfile({
        selected_path_key: "dl_cv_nlp",
        available_hours_per_week: null,
      }),
    ).toThrow("Planner V1 requires exactly one path");

    expect(() =>
      onboardingToLearningProfile({
        selected_path_key: null,
        available_hours_per_week: null,
      }),
    ).toThrow("Planner V1 requires exactly one path");
  });

  it("marks stale only when topology changes, not pacing", () => {
    const generated = createLearningProfileForPath("computer_vision", {
      weeklyHours: 4,
      source: "onboarding",
    });
    const sameTopologyNewPacing = createLearningProfileForPath("computer_vision", {
      weeklyHours: 12,
      source: "onboarding",
    });
    const differentTopology = createLearningProfileForPath("nlp", {
      weeklyHours: 4,
      source: "onboarding",
    });

    expect(isProfilePathStale(generated.topologyHash, sameTopologyNewPacing)).toBe(false);
    expect(isProfilePathStale(generated.topologyHash, differentTopology)).toBe(true);
  });
});
