import { beforeEach, describe, expect, it } from "vitest";

import { readPendingCanonicalAssessment } from "@/lib/canonical-assessment-session";
import {
  buildReplanAssessmentHref,
  readReplanAssessmentScope,
  writeReplanAssessmentContext,
} from "@/lib/replan-assessment-context";

describe("replan assessment context", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("writes selected canonical units for the existing assessment page", () => {
    writeReplanAssessmentContext({
      units: [
        {
          canonicalUnitId: "unit_faster_rcnn",
          title: "Faster R-CNN",
          difficultyFilter: "all",
          selectedQuestionCount: 10,
        },
        {
          canonicalUnitId: "unit_rcnn",
          title: "R-CNN",
          difficultyFilter: "easy_medium_hard",
          selectedQuestionCount: 6,
        },
      ],
    });

    expect(readPendingCanonicalAssessment()).toEqual({
      canonicalUnitIds: ["unit_faster_rcnn", "unit_rcnn"],
      unitNameMap: {
        unit_faster_rcnn: "Faster R-CNN",
        unit_rcnn: "R-CNN",
      },
      assessmentDepth: "deep",
    });
    expect(readReplanAssessmentScope()).toEqual({
      selectedUnits: [
        {
          canonicalUnitId: "unit_faster_rcnn",
          title: "Faster R-CNN",
          difficultyFilter: "all",
          selectedQuestionCount: 10,
        },
        {
          canonicalUnitId: "unit_rcnn",
          title: "R-CNN",
          difficultyFilter: "easy_medium_hard",
          selectedQuestionCount: 6,
        },
      ],
      questionTotal: 16,
      estimatedSeconds: 160,
      scope: "current_path_only",
    });
  });

  it("builds an assessment href that returns to learn by default", () => {
    expect(buildReplanAssessmentHref()).toBe("/assessment?next=%2Flearn");
    expect(buildReplanAssessmentHref("/agent")).toBe("/assessment?next=%2Fagent");
  });
});
