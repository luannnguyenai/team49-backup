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
    course_id: overrides.course_id ?? "course-a",
    course_title: overrides.course_title ?? "Course A",
    segment_policy: overrides.segment_policy,
  };
}

describe("roadmap model", () => {
  it("returns a safe empty canvas", () => {
    expect(buildRoadmapModel([])).toMatchObject({
      width: 760,
      height: 520,
      nodes: [],
      connectors: [],
    });
  });

  it("groups visible units under course containers and lecture topic rows", () => {
    const model = buildRoadmapModel([
      item({ id: "hidden", order_index: 0, segment_policy: "hidden" }),
      item({ id: "a", order_index: 1, course_id: "cs230", course_title: "CS230", section_title: "Deep Learning" }),
      item({ id: "b", order_index: 2, course_id: "cs231n", course_title: "CS231n", section_title: "Computer Vision" }),
    ]);

    expect(model.nodes.map((node) => node.id)).toEqual([
      "course-cs230",
      "topic-cs230-deep-learning",
      "unit-a",
      "course-cs231n",
      "topic-cs231n-computer-vision",
      "unit-b",
    ]);
    expect(model.nodes.find((node) => node.id === "course-cs230")).toMatchObject({
      kind: "course",
      title: "CS230",
    });
    expect(model.nodes.find((node) => node.id === "topic-cs230-deep-learning")).toMatchObject({
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
    expect(connectorPath(model.nodes[1], model.nodes[2])).toMatch(/^M \d+ \d+ C \d+ \d+/);
  });
});
