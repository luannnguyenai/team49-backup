export type ReplanClaimValidation =
  | {
      ok: false;
      reason: "too_short" | "skip_all";
      message: string;
    }
  | {
      ok: true;
      specificity: "specific" | "broad";
      warning?: string;
    };

const TOO_SHORT_MESSAGE = 'Hãy mô tả cụ thể concept hoặc unit bạn đã biết, ví dụ: "CNN, R-CNN, Faster R-CNN".';
const SKIP_ALL_MESSAGE =
  "Mình không thể tạo bài kiểm tra để bỏ toàn bộ lộ trình từ một mô tả quá chung. Hãy nêu cụ thể những concept hoặc unit bạn đã biết.";
const BROAD_WARNING = "Mô tả của bạn khá rộng. Hãy kiểm tra kỹ danh sách unit được chọn trước khi bắt đầu assessment.";

const SKIP_ALL_PATTERNS = [
  /biết\s+hết/i,
  /skip\s+all/i,
  /bỏ\s+hết/i,
  /cho\s+qua\s+toàn\s+bộ/i,
  /tối\s+ưu\s+hết\s+mức/i,
  /bỏ\s+tất\s+cả/i,
  /bỏ\s+nguyên\s+path/i,
];

const BROAD_PATTERNS = [
  /cơ\s+bản/i,
  /fundamentals?/i,
  /ở\s+trường/i,
  /object\s+detection/i,
  /computer\s+vision/i,
  /machine\s+learning/i,
];

export function validateReplanKnowledgeClaim(value: string): ReplanClaimValidation {
  const claim = value.trim();
  const meaningfulTokens = claim.split(/\s+/).filter(Boolean);
  if (meaningfulTokens.length < 3) {
    return { ok: false, reason: "too_short", message: TOO_SHORT_MESSAGE };
  }
  if (SKIP_ALL_PATTERNS.some((pattern) => pattern.test(claim))) {
    return { ok: false, reason: "skip_all", message: SKIP_ALL_MESSAGE };
  }
  if (BROAD_PATTERNS.some((pattern) => pattern.test(claim))) {
    return { ok: true, specificity: "broad", warning: BROAD_WARNING };
  }
  return { ok: true, specificity: "specific" };
}
