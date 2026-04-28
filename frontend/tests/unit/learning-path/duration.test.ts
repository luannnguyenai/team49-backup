import { describe, expect, it } from "vitest";
import { formatDurationFromHours } from "@/features/learning-path/lib/duration";

describe("learning path duration formatting", () => {
  it("formats common sub-hour unit durations as minutes", () => {
    expect(formatDurationFromHours(0.13333333333333333)).toBe("8 phút");
    expect(formatDurationFromHours(0.15)).toBe("9 phút");
    expect(formatDurationFromHours(0.2)).toBe("12 phút");
  });

  it("formats longer week totals as hours and minutes", () => {
    expect(formatDurationFromHours(32.6333)).toBe("32 giờ 38 phút");
  });

  it("keeps seconds only for short non-minute durations", () => {
    expect(formatDurationFromHours(0.001)).toBe("4 giây");
    expect(formatDurationFromHours(0.025)).toBe("1 phút 30 giây");
  });

  it("returns null for missing or zero durations", () => {
    expect(formatDurationFromHours(null)).toBeNull();
    expect(formatDurationFromHours(0)).toBeNull();
  });
});
