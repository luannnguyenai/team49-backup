import { describe, expect, it } from "vitest";
import { CHART_PALETTE, CHART_SERIES, CHART_STATUS } from "@/lib/admin/chart-theme";

describe("Admin chart theme contract", () => {
  it("palette uses CSS variables", () => {
    Object.values(CHART_PALETTE).forEach((color) => {
      expect(color).toMatch(/^var\(--chart-/);
    });
  });

  it("status colors use state tokens", () => {
    expect(CHART_STATUS.success).toMatch(/var\(--state-success/);
    expect(CHART_STATUS.error).toMatch(/var\(--state-error/);
    expect(CHART_STATUS.warning).toMatch(/var\(--state-warning/);
  });

  it("series has five distinct entries", () => {
    expect(new Set(CHART_SERIES).size).toBe(5);
  });
});
