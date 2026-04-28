import { describe, expect, it } from "vitest";
import type { PathItemResponse } from "@/types";
import {
  computeRecommendedNext,
  groupByWeek,
  normalizeTimelineOrder,
  pathToFlow,
} from "@/features/learning-path/presenters";

function item(overrides: Partial<PathItemResponse> & { id: string; order_index: number }): PathItemResponse {
  return {
    id: overrides.id,
    learning_unit_id: overrides.learning_unit_id ?? overrides.id,
    learning_unit_title: overrides.learning_unit_title ?? `Unit ${overrides.id}`,
    section_title: overrides.section_title ?? "Section A",
    action: overrides.action ?? "standard_learn",
    estimated_hours: overrides.estimated_hours ?? 1,
    order_index: overrides.order_index,
    week_number: overrides.week_number ?? null,
    status: overrides.status ?? "pending",
    canonical_unit_id: overrides.canonical_unit_id ?? null,
    segment_policy: overrides.segment_policy,
    phase_tag: overrides.phase_tag,
    is_locked: overrides.is_locked,
  };
}

describe("learning path presenters", () => {
  it("returns empty flow for empty path", () => {
    expect(pathToFlow([])).toEqual({ nodes: [], edges: [], sectionSummaries: [] });
  });

  it("builds topic and subtopic nodes from sections", () => {
    const flow = pathToFlow([
      item({ id: "b", order_index: 1, section_title: "S2" }),
      item({ id: "a", order_index: 0, section_title: "S1" }),
      item({ id: "c", order_index: 2, section_title: "S2" }),
    ]);

    expect(flow.sectionSummaries).toHaveLength(2);
    expect(flow.nodes.filter((node) => node.type === "topic")).toHaveLength(2);
    expect(flow.nodes.filter((node) => node.type === "subtopic")).toHaveLength(3);
    expect(flow.edges.some((edge) => edge.source === "unit-a" && edge.target === "unit-b")).toBe(true);
    expect(flow.edges.some((edge) => edge.source === "unit-b" && edge.target === "unit-c")).toBe(true);
  });

  it("groups timeline by week with null fallback and excludes skipped or optional items", () => {
    const timeline = groupByWeek([
      item({ id: "a", order_index: 0, week_number: null, estimated_hours: 1.5 }),
      item({ id: "b", order_index: 1, week_number: 2, estimated_hours: 2 }),
      item({ id: "c", order_index: 2, week_number: 2, action: "skip" }),
      item({ id: "d", order_index: 3, week_number: 2, segment_policy: "hidden" }),
      item({ id: "e", order_index: 4, week_number: 2, section_title: "Lecture 1: Introduction" }),
    ]);

    expect(timeline.total_weeks).toBe(2);
    expect(timeline.items[0]).toMatchObject({ week: 1, total_hours: 1.5 });
    expect(timeline.items[1]).toMatchObject({ week: 2, total_hours: 2 });
    expect(timeline.items.flatMap((week) => week.learning_units).map((unit) => unit.id)).toEqual(["a", "b"]);
  });

  it("orders timeline units by course and lecture display order", () => {
    const timeline = groupByWeek([
      item({ id: "lecture-4", order_index: 0, section_title: "Lecture 4: Adversarial" }),
      item({ id: "lecture-2", order_index: 1, section_title: "Lecture 2: Supervised" }),
      item({ id: "lecture-3", order_index: 2, section_title: "Lecture 3: Project" }),
    ]);

    expect(timeline.items[0].learning_units.map((unit) => unit.id)).toEqual([
      "lecture-2",
      "lecture-3",
      "lecture-4",
    ]);
  });

  it("normalizes backend timeline unit order before render", () => {
    const timeline = normalizeTimelineOrder({
      total_weeks: 1,
      items: [
        {
          week: 1,
          total_hours: 1,
          learning_units: [
            item({ id: "lecture-9", order_index: 0, section_title: "Lecture 9: Interpretability" }),
            item({ id: "lecture-1", order_index: 1, section_title: "Lecture 1: Intro" }),
          ],
        },
      ],
    });

    expect(timeline.items[0].learning_units.map((unit) => unit.id)).toEqual([
      "lecture-1",
      "lecture-9",
    ]);
  });

  it("computes recommended next as first pending non-skip by global order", () => {
    expect(
      computeRecommendedNext([
        item({ id: "a", order_index: 0, status: "completed" }),
        item({ id: "b", order_index: 1, action: "skip" }),
        item({ id: "c", order_index: 2, status: "pending" }),
      ]),
    ).toBe("c");
  });

  it("does not recommend optional intro before the first core lecture", () => {
    expect(
      computeRecommendedNext([
        item({
          id: "intro",
          order_index: 0,
          section_title: "Lecture 1: Introduction to Deep Learning",
          phase_tag: "phase_b",
          is_locked: true,
        }),
        item({
          id: "future",
          order_index: 1,
          section_title: "Lecture 3: Later",
          phase_tag: "phase_b",
          is_locked: true,
        }),
        item({ id: "core", order_index: 2, section_title: "Lecture 2: Core" }),
      ]),
    ).toBe("core");
  });

  it("recommends next item by lecture display order rather than phase order", () => {
    expect(
      computeRecommendedNext([
        item({
          id: "lecture-4",
          order_index: 0,
          section_title: "Lecture 4: Adversarial Robustness",
        }),
        item({
          id: "lecture-2",
          order_index: 1,
          section_title: "Lecture 2: Supervised Learning",
        }),
      ]),
    ).toBe("lecture-2");
  });

  it("returns null when no eligible item exists", () => {
    expect(
      computeRecommendedNext([
        item({ id: "a", order_index: 0, status: "completed" }),
        item({ id: "b", order_index: 1, action: "skip" }),
      ]),
    ).toBeNull();
  });
});
