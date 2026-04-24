import { describe, expect, it } from "vitest";

import {
  buildModuleTestRuntimeRef,
  buildQuizRuntimeRef,
} from "@/lib/canonical-learning-runtime";

describe("canonical learning runtime refs", () => {
  it("builds quiz runtime refs from a canonical learning unit id", () => {
    expect(buildQuizRuntimeRef("unit_lecture_01")).toEqual({
      learningUnitId: "unit_lecture_01",
      resultStorageKey: "quiz_result_unit_lecture_01",
      learnHref: "/learn/unit_lecture_01",
      resultsHref: "/quiz/unit_lecture_01/results",
      restartHref: "/quiz/unit_lecture_01",
    });
  });

  it("builds module-test runtime refs from a canonical section id", () => {
    expect(
      buildModuleTestRuntimeRef("0d3b2f7a-82fe-4562-98c5-40a49922f0a1"),
    ).toEqual({
      sectionId: "0d3b2f7a-82fe-4562-98c5-40a49922f0a1",
      resultStorageKey:
        "module_test_result_0d3b2f7a-82fe-4562-98c5-40a49922f0a1",
      resultsHref:
        "/module-test/0d3b2f7a-82fe-4562-98c5-40a49922f0a1/results",
      restartHref: "/module-test/0d3b2f7a-82fe-4562-98c5-40a49922f0a1",
    });
  });
});
