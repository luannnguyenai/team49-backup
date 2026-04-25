import { describe, expect, it } from "vitest";
import { getStatusIconName, getStatusLabel, isVisibleInTimeline } from "@/features/learning-path/lib/status";
import type { PathItemResponse } from "@/types";

describe("learning path status helpers", () => {
  it("maps every status to Vietnamese labels and icon names", () => {
    expect(getStatusLabel("pending")).toBe("Chưa học");
    expect(getStatusLabel("in_progress")).toBe("Đang học");
    expect(getStatusLabel("completed")).toBe("Hoàn thành");
    expect(getStatusLabel("skipped")).toBe("Bỏ qua");
    expect(getStatusIconName("pending")).toBe("circle");
    expect(getStatusIconName("in_progress")).toBe("play");
    expect(getStatusIconName("completed")).toBe("check");
    expect(getStatusIconName("skipped")).toBe("skip");
  });

  it("hides skip actions from timeline", () => {
    const base: PathItemResponse = {
      id: "1",
      learning_unit_id: "1",
      learning_unit_title: "Unit",
      section_title: "Section",
      action: "standard_learn",
      estimated_hours: 1,
      order_index: 0,
      week_number: null,
      status: "pending",
      canonical_unit_id: null,
    };
    expect(isVisibleInTimeline(base)).toBe(true);
    expect(isVisibleInTimeline({ ...base, action: "skip" })).toBe(false);
  });
});
