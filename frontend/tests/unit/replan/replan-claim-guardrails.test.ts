import { describe, expect, it } from "vitest";
import { validateReplanKnowledgeClaim } from "@/lib/replan-claim-guardrails";

describe("validateReplanKnowledgeClaim", () => {
  it("rejects empty or too-short claims", () => {
    expect(validateReplanKnowledgeClaim("   ")).toEqual({
      ok: false,
      reason: "too_short",
      message: 'Hãy mô tả cụ thể concept hoặc unit bạn đã biết, ví dụ: "CNN, R-CNN, Faster R-CNN".',
    });
    expect(validateReplanKnowledgeClaim("CNN")).toMatchObject({
      ok: false,
      reason: "too_short",
    });
  });

  it("blocks skip-all commands instead of creating a broad assessment", () => {
    expect(validateReplanKnowledgeClaim("tôi biết hết, bỏ hết path này đi")).toEqual({
      ok: false,
      reason: "skip_all",
      message: "Mình không thể tạo bài kiểm tra để bỏ toàn bộ lộ trình từ một mô tả quá chung. Hãy nêu cụ thể những concept hoặc unit bạn đã biết.",
    });
  });

  it("allows broad but usable claims with a warning flag", () => {
    expect(validateReplanKnowledgeClaim("Tôi biết object detection cơ bản")).toEqual({
      ok: true,
      specificity: "broad",
      warning: "Mô tả của bạn khá rộng. Hãy kiểm tra kỹ danh sách unit được chọn trước khi bắt đầu assessment.",
    });
  });

  it("allows specific claims without warning", () => {
    expect(validateReplanKnowledgeClaim("Tôi biết Faster R-CNN và Region Proposal Network")).toEqual({
      ok: true,
      specificity: "specific",
    });
  });
});
