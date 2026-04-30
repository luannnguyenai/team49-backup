import { describe, expect, it } from "vitest";
import { formatDurationFromHours } from "@/features/learning-path/lib/duration";

describe("learning path duration formatting", () => {
  it("formats common sub-hour unit durations as minutes", () => {
    expect(formatDurationFromHours(0.13333333333333333)).toBe("8 min");
    expect(formatDurationFromHours(0.15)).toBe("9 min");
    expect(formatDurationFromHours(0.2)).toBe("12 min");
  });

  it("formats longer week totals as hours and minutes", () => {
    expect(formatDurationFromHours(32.6333)).toBe("32 hr 38 min");
  });

  it("keeps seconds only for short non-minute durations", () => {
    expect(formatDurationFromHours(0.001)).toBe("4 sec");
    expect(formatDurationFromHours(0.025)).toBe("1 min 30 sec");
  });

  it("returns null for missing or zero durations", () => {
    expect(formatDurationFromHours(null)).toBeNull();
    expect(formatDurationFromHours(0)).toBeNull();
  });
});
