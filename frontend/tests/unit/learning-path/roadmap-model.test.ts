import { describe, expect, it } from "vitest";
import type { PathItemResponse } from "@/types";
import { buildRoadmapModel, connectorPath } from "@/features/learning-path/roadmap-model";

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
  };
}

describe("roadmap model", () => {
  it("returns a safe empty canvas", () => {
    expect(buildRoadmapModel([])).toMatchObject({
      width: 1000,
      height: 520,
      nodes: [],
      connectors: [],
    });
  });

  it("groups visible units under section topic rows and filters hidden segments", () => {
    const model = buildRoadmapModel([
      item({ id: "hidden", order_index: 0, segment_policy: "hidden" }),
      item({ id: "a", order_index: 1, section_title: "Deep Learning" }),
      item({ id: "b", order_index: 2, section_title: "Computer Vision" }),
    ]);

    expect(model.nodes.map((node) => node.id)).toEqual([
      "topic-section-1-deep-learning",
      "unit-a",
      "topic-section-2-computer-vision",
      "unit-b",
    ]);
    expect(model.nodes.find((node) => node.id === "topic-section-1-deep-learning")).toMatchObject({
      kind: "topic",
      title: "Deep Learning",
      item: null,
    });
    expect(model.nodes.find((node) => node.id === "unit-a")).toMatchObject({
      kind: "unit",
      itemId: "a",
      isRecommended: true,
    });
    expect(model.nodes.some((node) => node.id === "unit-hidden")).toBe(false);
  });

  it("connects nodes with vertical-friendly paths", () => {
    const model = buildRoadmapModel([
      item({ id: "a", order_index: 0, section_title: "Deep Learning" }),
      item({ id: "b", order_index: 1, section_title: "Deep Learning" }),
    ]);

    expect(model.connectors).toHaveLength(2);
    expect(connectorPath(model.nodes[0], model.nodes[1])).toMatch(/^M \d+ \d+ C \d+ \d+/);
  });
});
