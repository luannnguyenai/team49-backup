import { beforeEach, describe, expect, it } from "vitest";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { PlacementTopicResult } from "@/stores/onboardingStore";

describe("useOnboardingStore", () => {
  beforeEach(() => {
    useOnboardingStore.getState().reset();
  });

  it("has correct initial state", () => {
    const state = useOnboardingStore.getState();
    expect(state.currentStep).toBe(1);
    expect(state.goalIds).toEqual([]);
    expect(state.knownUnitIds).toEqual([]);
    expect(state.desiredSectionIds).toEqual([]);
    expect(state.weeklyHours).toBeNull();
    expect(state.learningMethod).toBeNull();
    expect(state.placementSessionId).toBeNull();
    expect(state.placementResults).toBeNull();
  });

  it("setGoalIds updates goalIds", () => {
    const ids = ["goal-1", "goal-2"];
    useOnboardingStore.getState().setGoalIds(ids);
    expect(useOnboardingStore.getState().goalIds).toEqual(ids);
  });

  it("setStep updates currentStep", () => {
    useOnboardingStore.getState().setStep(3);
    expect(useOnboardingStore.getState().currentStep).toBe(3);
  });

  it("setKnownUnitIds updates knownUnitIds", () => {
    const ids = ["unit-a", "unit-b"];
    useOnboardingStore.getState().setKnownUnitIds(ids);
    expect(useOnboardingStore.getState().knownUnitIds).toEqual(ids);
  });

  it("setDesiredSectionIds updates desiredSectionIds", () => {
    const ids = ["section-1"];
    useOnboardingStore.getState().setDesiredSectionIds(ids);
    expect(useOnboardingStore.getState().desiredSectionIds).toEqual(ids);
  });

  it("setWeeklyHours updates weeklyHours", () => {
    useOnboardingStore.getState().setWeeklyHours(10);
    expect(useOnboardingStore.getState().weeklyHours).toBe(10);
  });

  it("setLearningMethod updates learningMethod", () => {
    useOnboardingStore.getState().setLearningMethod("video");
    expect(useOnboardingStore.getState().learningMethod).toBe("video");
  });

  it("setPlacementSessionId updates placementSessionId", () => {
    const id = "session-uuid-123";
    useOnboardingStore.getState().setPlacementSessionId(id);
    expect(useOnboardingStore.getState().placementSessionId).toBe(id);
  });

  it("setPlacementResults updates placementResults", () => {
    const results: PlacementTopicResult[] = [
      { topic_unit_id: "unit-1", decision: "skip", score_pct: 90 },
      { topic_unit_id: "unit-2", decision: "relearn", score_pct: 20 },
    ];
    useOnboardingStore.getState().setPlacementResults(results);
    expect(useOnboardingStore.getState().placementResults).toEqual(results);
  });

  it("reset returns state to initial values", () => {
    // Populate state with non-default values
    const store = useOnboardingStore.getState();
    store.setStep(4);
    store.setGoalIds(["g-1"]);
    store.setKnownUnitIds(["k-1"]);
    store.setDesiredSectionIds(["s-1"]);
    store.setWeeklyHours(5);
    store.setLearningMethod("reading");
    store.setPlacementSessionId("some-session");
    store.setPlacementResults([
      { topic_unit_id: "u-1", decision: "review", score_pct: 50 },
    ]);

    // Reset
    useOnboardingStore.getState().reset();

    const state = useOnboardingStore.getState();
    expect(state.currentStep).toBe(1);
    expect(state.goalIds).toEqual([]);
    expect(state.knownUnitIds).toEqual([]);
    expect(state.desiredSectionIds).toEqual([]);
    expect(state.weeklyHours).toBeNull();
    expect(state.learningMethod).toBeNull();
    expect(state.placementSessionId).toBeNull();
    expect(state.placementResults).toBeNull();
  });
});
