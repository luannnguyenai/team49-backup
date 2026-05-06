import { describe, expect, it } from "vitest";

import {
  getActionCanonicalIds,
  getActionDisabledReason,
  getActionPrerequisitePath,
  getActionQuestionBudget,
  getCitationCourseId,
  getCitationHref,
  getCitationUnitName,
  getProposalDifficultyMix,
  getProposalQuestionCount,
  getPrerequisiteNodeCanonicalId,
  getPrerequisiteNodeHref,
  getPrerequisiteNodeMasteryLcb,
  getPrerequisiteNodeName,
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

  it("maps prerequisite path nodes from backend aliases", () => {
    const action: AgentAction = {
      type: "review_prerequisite_path",
      label: "Review prerequisite order",
      prerequisite_path: {
        target_canonical_unit_id: "unit-target",
        nodes: [
          {
            canonical_unit_id: "unit-prereq",
            unit_name: "Object detection foundations",
            role: "prerequisite",
            status: "skipped",
            learn_href: "/learn/object-detection",
            mastery_lcb: 0.92,
          },
        ],
        edges: [],
      },
    };

    const path = getActionPrerequisitePath(action);
    expect(path?.target_canonical_unit_id).toBe("unit-target");
    expect(path?.nodes[0]).toBeDefined();
    expect(getPrerequisiteNodeCanonicalId(path!.nodes[0])).toBe("unit-prereq");
    expect(getPrerequisiteNodeName(path!.nodes[0])).toBe("Object detection foundations");
    expect(getPrerequisiteNodeHref(path!.nodes[0])).toBe("/learn/object-detection");
    expect(getPrerequisiteNodeMasteryLcb(path!.nodes[0])).toBe(0.92);
  });
});
