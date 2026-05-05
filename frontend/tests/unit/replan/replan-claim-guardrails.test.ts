import { describe, expect, it } from "vitest";
import { validateReplanKnowledgeClaim } from "@/lib/replan-claim-guardrails";

describe("validateReplanKnowledgeClaim", () => {
  it("rejects empty or too-short claims", () => {
    expect(validateReplanKnowledgeClaim("   ")).toEqual({
      ok: false,
      reason: "too_short",
      message: 'Please describe specific concepts or units you know, e.g., "CNN, R-CNN, Faster R-CNN".',
    });
    expect(validateReplanKnowledgeClaim("I")).toMatchObject({
      ok: false,
      reason: "too_short",
    });
    expect(validateReplanKnowledgeClaim("1")).toMatchObject({
      ok: false,
      reason: "too_short",
    });
  });

  it("allows compact single-token claims to continue into search and LLM unit selection", () => {
    expect(validateReplanKnowledgeClaim("know")).toEqual({
      ok: true,
      specificity: "specific",
    });
    expect(validateReplanKnowledgeClaim("bert")).toEqual({
      ok: true,
      specificity: "specific",
    });
    expect(validateReplanKnowledgeClaim("Word2vec")).toEqual({
      ok: true,
      specificity: "specific",
    });
    expect(validateReplanKnowledgeClaim("cnn")).toEqual({
      ok: true,
      specificity: "specific",
    });
  });

  it("blocks skip-all commands instead of creating a broad assessment", () => {
    expect(validateReplanKnowledgeClaim("tôi biết hết, bỏ hết path này đi")).toEqual({
      ok: false,
      reason: "skip_all",
      message: "I cannot create an assessment to skip your entire learning path from such a general description. Please specify the concepts or units you already know.",
    });
    expect(validateReplanKnowledgeClaim("skip all")).toMatchObject({
      ok: false,
      reason: "skip_all",
    });
  });

  it("allows broad but usable claims with a warning flag", () => {
    expect(validateReplanKnowledgeClaim("Tôi biết object detection cơ bản")).toEqual({
      ok: true,
      specificity: "broad",
      warning: "Your description is quite broad. Please carefully review the selected unit list before starting the assessment.",
    });
  });

  it("allows specific claims without warning", () => {
    expect(validateReplanKnowledgeClaim("Tôi biết Faster R-CNN và Region Proposal Network")).toEqual({
      ok: true,
      specificity: "specific",
    });
  });
});
