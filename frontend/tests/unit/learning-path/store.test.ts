import { beforeEach, describe, expect, it, vi } from "vitest";
import type { LearningPathResponse, PathItemResponse, TimelineResponse } from "@/types";
import { learningSessionApi } from "@/lib/api";
import { learningPathApi } from "@/features/learning-path/api";
import { createLearningProfileForPath } from "@/features/learning-path/profile";
import { useLearningPathStore } from "@/features/learning-path/store";

vi.mock("@/lib/api", () => ({
  learningSessionApi: {
    resume: vi.fn(),
  },
}));

vi.mock("@/features/learning-path/api", () => ({
  learningPathApi: {
    getLearningPath: vi.fn(),
    generatePath: vi.fn(),
    getTimeline: vi.fn(),
    updatePathStatus: vi.fn(),
  },
}));

function pathItem(overrides: Partial<PathItemResponse> & { id: string }): PathItemResponse {
  return {
    id: overrides.id,
    learning_unit_id: overrides.learning_unit_id ?? overrides.id,
    learning_unit_title: overrides.learning_unit_title ?? `Unit ${overrides.id}`,
    section_title: overrides.section_title ?? "Deep Learning",
    action: overrides.action ?? "standard_learn",
    estimated_hours: overrides.estimated_hours ?? 1,
    order_index: overrides.order_index ?? 0,
    week_number: overrides.week_number ?? null,
    status: overrides.status ?? "pending",
    canonical_unit_id: overrides.canonical_unit_id ?? null,
    reason_codes: overrides.reason_codes,
    prerequisite_gap_kp_ids: overrides.prerequisite_gap_kp_ids,
    segment_policy: overrides.segment_policy,
    content_type: overrides.content_type,
    salience_score: overrides.salience_score,
    has_quiz_items: overrides.has_quiz_items,
    is_worth_learning: overrides.is_worth_learning,
    override_critical_kp: overrides.override_critical_kp,
    phase_tag: overrides.phase_tag,
    is_locked: overrides.is_locked,
  };
}

function learningPath(items: PathItemResponse[]): LearningPathResponse {
  return {
    total_units: items.length,
    completed_units: 0,
    in_progress_units: 0,
    items,
  };
}

function emptyTimeline(): TimelineResponse {
  return {
    total_weeks: 0,
    items: [],
  };
}

function resetStore() {
  useLearningPathStore.setState({
    profile: null,
    generatedTopologyHash: null,
    previousProfile: null,
    currentProgress: null,
    items: [],
    summary: null,
    timeline: null,
    loading: false,
    error: null,
    selectedItemId: null,
    selectedSectionKey: null,
    updatingStatusById: {},
  });
}

describe("learning path store", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
    vi.mocked(learningPathApi.getTimeline).mockResolvedValue(emptyTimeline());
    vi.mocked(learningSessionApi.resume).mockRejectedValue(new Error("no active session"));
  });

  it("generates a concrete path from the selected profile when backend path is empty", async () => {
    const profile = createLearningProfileForPath("computer_vision", {
      weeklyHours: null,
      source: "manual",
    });
    const generatedItem = pathItem({
      id: "generated-cv",
      learning_unit_title: "CNN foundations",
    });

    useLearningPathStore.getState().setProfile(profile);
    vi.mocked(learningPathApi.getLearningPath).mockResolvedValue(learningPath([]));
    vi.mocked(learningPathApi.generatePath).mockResolvedValue({
      generated_at: "2026-04-28T00:00:00Z",
      total_units: 1,
      total_hours: 1,
      required_hours_per_week: null,
      warnings: [],
      items: [generatedItem],
    });

    await useLearningPathStore.getState().loadPath();

    expect(learningPathApi.generatePath).toHaveBeenCalledWith({
      desired_section_ids: [],
      selected_course_ids: ["CS230", "CS231n"],
    });
    expect(useLearningPathStore.getState()).toMatchObject({
      items: [generatedItem],
      generatedTopologyHash: profile.topologyHash,
      error: null,
    });
  });

  it("treats a missing backend path as empty when a concrete profile exists", async () => {
    const profile = createLearningProfileForPath("computer_vision", {
      weeklyHours: null,
      source: "manual",
    });
    const generatedItem = pathItem({
      id: "generated-after-404",
      learning_unit_title: "CNN foundations",
    });

    useLearningPathStore.getState().setProfile(profile);
    vi.mocked(learningPathApi.getLearningPath).mockRejectedValue({
      response: { status: 404 },
    });
    vi.mocked(learningPathApi.generatePath).mockResolvedValue({
      generated_at: "2026-04-28T00:00:00Z",
      total_units: 1,
      total_hours: 1,
      required_hours_per_week: null,
      warnings: [],
      items: [generatedItem],
    });

    await useLearningPathStore.getState().loadPath();

    expect(learningPathApi.generatePath).toHaveBeenCalledWith({
      desired_section_ids: [],
      selected_course_ids: ["CS230", "CS231n"],
    });
    expect(useLearningPathStore.getState()).toMatchObject({
      items: [generatedItem],
      error: null,
    });
  });

  it("regenerates when the persisted path hash does not match the current profile", async () => {
    const oldProfile = createLearningProfileForPath("computer_vision", {
      weeklyHours: null,
      source: "manual",
    });
    const nextProfile = createLearningProfileForPath("nlp", {
      weeklyHours: null,
      source: "manual",
    });
    const staleItem = pathItem({ id: "old-cv", learning_unit_title: "CNN foundations" });
    const generatedItem = pathItem({ id: "generated-nlp", learning_unit_title: "Transformers" });

    useLearningPathStore.getState().setProfile(oldProfile);
    useLearningPathStore.setState({ generatedTopologyHash: oldProfile.topologyHash });
    useLearningPathStore.getState().setProfile(nextProfile);
    vi.mocked(learningPathApi.getLearningPath).mockResolvedValue(learningPath([staleItem]));
    vi.mocked(learningPathApi.generatePath).mockResolvedValue({
      generated_at: "2026-04-28T00:00:00Z",
      total_units: 1,
      total_hours: 1,
      required_hours_per_week: null,
      warnings: [],
      items: [generatedItem],
    });

    await useLearningPathStore.getState().loadPath();

    expect(learningPathApi.generatePath).toHaveBeenCalledWith({
      desired_section_ids: [],
      selected_course_ids: ["CS230", "CS224n"],
    });
    expect(useLearningPathStore.getState()).toMatchObject({
      items: [generatedItem],
      generatedTopologyHash: nextProfile.topologyHash,
      previousProfile: oldProfile,
    });
  });

  it("summarizes the current main path instead of raw locked future units", async () => {
    const profile = createLearningProfileForPath("computer_vision", {
      weeklyHours: null,
      source: "manual",
    });
    const visible = pathItem({ id: "visible", status: "in_progress" });
    const skipped = pathItem({ id: "skipped", action: "skip" });
    const locked = pathItem({
      id: "locked",
      phase_tag: "phase_b",
      is_locked: true,
    });

    useLearningPathStore.getState().setProfile(profile);
    useLearningPathStore.setState({ generatedTopologyHash: profile.topologyHash });
    vi.mocked(learningPathApi.getLearningPath).mockResolvedValue(
      learningPath([visible, skipped, locked]),
    );

    await useLearningPathStore.getState().loadPath();

    expect(useLearningPathStore.getState().summary).toMatchObject({
      total_units: 2,
      completed_units: 1,
      in_progress_units: 1,
    });
  });
});
