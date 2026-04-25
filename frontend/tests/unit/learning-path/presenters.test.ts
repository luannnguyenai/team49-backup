import { describe, expect, it } from "vitest";
import type { PathItemResponse } from "@/types";
import { computeRecommendedNext, groupByWeek, pathToFlow } from "@/features/learning-path/presenters";

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

  it("groups timeline by week with null fallback and excludes skipped actions", () => {
    const timeline = groupByWeek([
      item({ id: "a", order_index: 0, week_number: null, estimated_hours: 1.5 }),
      item({ id: "b", order_index: 1, week_number: 2, estimated_hours: 2 }),
      item({ id: "c", order_index: 2, week_number: 2, action: "skip" }),
    ]);

    expect(timeline.total_weeks).toBe(2);
    expect(timeline.items[0]).toMatchObject({ week: 1, total_hours: 1.5 });
    expect(timeline.items[1]).toMatchObject({ week: 2, total_hours: 2 });
    expect(timeline.items.flatMap((week) => week.learning_units).map((unit) => unit.id)).toEqual(["a", "b"]);
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

  it("returns null when no eligible item exists", () => {
    expect(
      computeRecommendedNext([
        item({ id: "a", order_index: 0, status: "completed" }),
        item({ id: "b", order_index: 1, action: "skip" }),
      ]),
    ).toBeNull();
  });
});
