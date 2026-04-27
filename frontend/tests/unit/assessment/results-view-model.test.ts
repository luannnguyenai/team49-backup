import { describe, expect, it } from "vitest";
import { buildAssessmentResultViewModel } from "@/lib/assessment-results-view-model";
import type { AssessmentResultResponse } from "@/types";

const result: AssessmentResultResponse = {
  session_id: "s1",
  completed_at: "2026-04-27T00:00:00Z",
  overall_score_percent: 82.8,
  learning_unit_results: [
    {
      learning_unit_id: "u1",
      learning_unit_title: "Activation functions",
      score_percent: 0,
      mastery_level: "novice",
      bloom_breakdown: { remember: "0/1" },
      weak_kcs: ["relu"],
      misconceptions_detected: [],
    },
    {
      learning_unit_id: "u2",
      learning_unit_title: "CNN components recap",
      score_percent: 0,
      mastery_level: "novice",
      bloom_breakdown: { remember: "0/1" },
      weak_kcs: [],
      misconceptions_detected: ["normalization"],
    },
    {
      learning_unit_id: "u3",
      learning_unit_title: "Convolution layers",
      score_percent: 100,
      mastery_level: "mastered",
      bloom_breakdown: { apply: "1/1" },
      weak_kcs: [],
      misconceptions_detected: [],
    },
  ],
  topic_decisions: [
    {
      topic_unit_id: "u1",
      topic_unit_name: "Activation functions",
      score_pct: 0,
      decision: "relearn",
      mastery_level: "novice",
      questions_total: 1,
      questions_correct: 0,
    },
    {
      topic_unit_id: "u2",
      topic_unit_name: "CNN components recap",
      score_pct: 0,
      decision: "review",
      mastery_level: "novice",
      questions_total: 1,
      questions_correct: 0,
    },
    {
      topic_unit_id: "u3",
      topic_unit_name: "Convolution layers",
      score_pct: 100,
      decision: "skip",
      mastery_level: "mastered",
      questions_total: 1,
      questions_correct: 1,
    },
  ],
};

describe("buildAssessmentResultViewModel", () => {
  it("summarizes result into compact counts and priority items", () => {
    const viewModel = buildAssessmentResultViewModel(result);

    expect(viewModel.counts).toEqual({
      relearn: 1,
      review: 1,
      skip: 1,
      mastered: 1,
      total: 3,
    });
    expect(viewModel.priorityItems.map((item) => item.title)).toEqual([
      "Activation functions",
      "CNN components recap",
    ]);
    expect(viewModel.masteredPreview).toHaveLength(1);
    expect(viewModel.misconceptions).toEqual([
      { learningUnit: "CNN components recap", id: "normalization" },
    ]);
  });
});
