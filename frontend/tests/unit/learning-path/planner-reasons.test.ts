import { describe, expect, it } from "vitest";
import { describePlannerReason } from "@/features/learning-path/planner-reasons";

describe("describePlannerReason", () => {
  it("maps core reason codes to stable labels", () => {
    expect(describePlannerReason("critical_kp")).toMatchObject({ label: "Critical KP" });
    expect(describePlannerReason("quick_review")).toMatchObject({ label: "Quick review" });
    expect(describePlannerReason("skip_by_mastery")).toMatchObject({ label: "Skip by mastery" });
    expect(describePlannerReason("unknown")).toMatchObject({ label: "unknown" });
  });
});
