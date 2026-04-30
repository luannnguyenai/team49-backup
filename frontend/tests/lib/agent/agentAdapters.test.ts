import { describe, expect, it } from "vitest";

import {
  getActionCanonicalIds,
  getActionDisabledReason,
  getActionQuestionBudget,
  getCitationCourseId,
  getCitationHref,
  getCitationUnitName,
  getProposalDifficultyMix,
  getProposalQuestionCount,
  getReductionQuestionCount,
  getWorkflowId,
  type AgentAction,
} from "@/features/agent/api";

describe("agent API adapters", () => {
  it("accepts snake_case and camelCase action fields", () => {
    const action: AgentAction = {
      type: "start_assessment",
      label: "Start assessment",
      canonical_unit_ids: ["unit-a"],
      disabled_reason: null,
      question_budget: 38,
      eligible: true,
    };

    expect(getActionCanonicalIds(action)).toEqual(["unit-a"]);
    expect(getActionDisabledReason(action)).toBeNull();
    expect(getActionQuestionBudget(action)).toBe(38);

    expect(
      getWorkflowId({
        workflowId: "workflow-1",
        status: "assessment_ready",
        actions: [],
      }),
    ).toBe("workflow-1");
  });

  it("maps citation and proposal view fields defensively", () => {
    expect(
      getCitationHref({
        canonical_unit_id: "unit-a",
        course_id: "CS231n",
        unit_name: "Receptive fields",
        learn_href: "/courses/cs231n/learn/unit-a",
        source: "summary",
      }),
    ).toBe("/courses/cs231n/learn/unit-a");

    expect(getCitationCourseId({})).toBe("Course");
    expect(getCitationUnitName({})).toBe("Learning unit");
    expect(getProposalQuestionCount({ title: "Assessment", purpose: "", estimated_questions: 28, scope: [] })).toBe(28);
    expect(getProposalDifficultyMix({ title: "Assessment", purpose: "", difficulty_mix: { easy: 4 }, scope: [] })).toEqual({ easy: 4 });
    expect(getReductionQuestionCount({ id: "core", label: "Core", effect: "", estimated_questions_after_reduction: 20 })).toBe(20);
  });
});
