import { describe, expect, it } from "vitest";
import {
  getStatusIconName,
  getStatusLabel,
  isIncludedInMainPath,
  isVisibleInMainPath,
  isVisibleInTimeline,
} from "@/features/learning-path/lib/status";
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

  it("keeps only actionable learning items in the main path", () => {
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
      segment_policy: "core",
    };

    expect(isVisibleInMainPath(base)).toBe(true);
    expect(isVisibleInMainPath({ ...base, action: "skip" })).toBe(false);
    expect(isVisibleInMainPath({ ...base, status: "skipped" })).toBe(false);
    expect(isVisibleInMainPath({ ...base, segment_policy: "reference" })).toBe(false);
    expect(isVisibleInMainPath({ ...base, segment_policy: "hidden" })).toBe(false);
    expect(isVisibleInMainPath({ ...base, phase_tag: "phase_b", is_locked: true })).toBe(false);
    expect(isVisibleInMainPath({ ...base, phase_tag: "phase_b", is_locked: false })).toBe(true);
  });

  it("keeps evidence-skipped and optional intro items in progress counts but not future locked content", () => {
    const base: PathItemResponse = {
      id: "1",
      learning_unit_id: "1",
      learning_unit_title: "Unit",
      section_title: "Lecture 2: Core",
      action: "standard_learn",
      estimated_hours: 1,
      order_index: 0,
      week_number: null,
      status: "pending",
      canonical_unit_id: null,
      segment_policy: "core",
      phase_tag: "phase_b",
      is_locked: true,
    };

    expect(isIncludedInMainPath(base)).toBe(false);
    expect(isIncludedInMainPath({ ...base, action: "skip" })).toBe(true);
    expect(isVisibleInMainPath({ ...base, action: "skip" })).toBe(false);
    expect(
      isIncludedInMainPath({
        ...base,
        section_title: "Lecture 1: Introduction to Deep Learning",
      }),
    ).toBe(true);
  });
});
