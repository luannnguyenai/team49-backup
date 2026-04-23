import { describe, expect, it } from "vitest";

import {
  buildCanonicalAssessmentContext,
  getAssessmentQuestionKey,
} from "@/lib/canonical-assessment-session";
import type { ModuleDetail, QuestionForAssessment } from "@/types";

const MODULES: ModuleDetail[] = [
  {
    id: "section_foundations",
    name: "Foundations",
    description: "Core foundations",
    order_index: 1,
    prerequisite_module_ids: null,
    topics_count: 2,
    topics: [
      {
        id: "learning_unit_1",
        canonical_unit_id: "local::lecture01::seg1",
        name: "Vectors",
        description: null,
        order_index: 1,
        estimated_hours_beginner: 1,
        estimated_hours_intermediate: 0.5,
      },
      {
        id: "learning_unit_2",
        canonical_unit_id: "local::lecture01::seg2",
        name: "Linear algebra",
        description: null,
        order_index: 2,
        estimated_hours_beginner: 1.5,
        estimated_hours_intermediate: 1,
      },
    ],
  },
  {
    id: "section_models",
    name: "Models",
    description: "Model building",
    order_index: 2,
    prerequisite_module_ids: null,
    topics_count: 1,
    topics: [
      {
        id: "learning_unit_3",
        canonical_unit_id: "local::lecture02::seg1",
        name: "Optimization",
        description: null,
        order_index: 1,
        estimated_hours_beginner: 2,
        estimated_hours_intermediate: 1.5,
      },
    ],
  },
];

describe("canonical assessment session helpers", () => {
  it("builds canonical assessment context from selected known topics", () => {
    expect(
      buildCanonicalAssessmentContext({
        modules: MODULES,
        knownTopicIds: ["learning_unit_2", "learning_unit_3"],
        desiredModuleIds: ["section_foundations"],
      }),
    ).toEqual({
      canonicalUnitIds: ["local::lecture01::seg2", "local::lecture02::seg1"],
      unitNameMap: {
        "local::lecture01::seg2": "Linear algebra",
        "local::lecture02::seg1": "Optimization",
      },
    });
  });

  it("falls back to selected modules when no known topics were chosen", () => {
    expect(
      buildCanonicalAssessmentContext({
        modules: MODULES,
        knownTopicIds: [],
        desiredModuleIds: ["section_foundations"],
      }),
    ).toEqual({
      canonicalUnitIds: ["local::lecture01::seg1", "local::lecture01::seg2"],
      unitNameMap: {
        "local::lecture01::seg1": "Vectors",
        "local::lecture01::seg2": "Linear algebra",
      },
    });
  });

  it("prefers canonical item ids for assessment question keys", () => {
    const canonicalQuestion: QuestionForAssessment = {
      id: null,
      item_id: "legacy-surrogate",
      canonical_item_id: "item::canonical",
      canonical_unit_id: "local::lecture01::seg2",
      topic_id: null,
      bloom_level: null,
      difficulty_bucket: null,
      stem_text: "Question",
      option_a: "A",
      option_b: "B",
      option_c: "C",
      option_d: "D",
      time_expected_seconds: null,
    };

    const legacyQuestion: QuestionForAssessment = {
      ...canonicalQuestion,
      id: "question_uuid",
      canonical_item_id: null,
      canonical_unit_id: null,
      topic_id: "topic_uuid",
    };

    expect(getAssessmentQuestionKey(canonicalQuestion)).toBe("item::canonical");
    expect(getAssessmentQuestionKey(legacyQuestion)).toBe("question_uuid");
  });
});
