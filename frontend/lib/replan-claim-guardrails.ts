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

const TOO_SHORT_MESSAGE = 'Please describe specific concepts or units you know, e.g., "CNN, R-CNN, Faster R-CNN".';
const SKIP_ALL_MESSAGE =
  "I cannot create an assessment to skip your entire learning path from such a general description. Please specify the concepts or units you already know.";
const BROAD_WARNING = "Your description is quite broad. Please carefully review the selected unit list before starting the assessment.";

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
  if (SKIP_ALL_PATTERNS.some((pattern) => pattern.test(claim))) {
    return { ok: false, reason: "skip_all", message: SKIP_ALL_MESSAGE };
  }
  if (isTooShortForSearch(claim)) {
    return { ok: false, reason: "too_short", message: TOO_SHORT_MESSAGE };
  }
  if (BROAD_PATTERNS.some((pattern) => pattern.test(claim))) {
    return { ok: true, specificity: "broad", warning: BROAD_WARNING };
  }
  return { ok: true, specificity: "specific" };
}

function isTooShortForSearch(claim: string): boolean {
  const compact = claim.replace(/\s+/g, "");
  return compact.length < 2;
}
