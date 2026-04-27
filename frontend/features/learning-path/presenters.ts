import type { PathItemResponse, TimelineResponse, WeekEntry } from "@/types";
import { isVisibleInTimeline } from "./lib/status";

export interface SectionSummary {
  key: string;
  title: string;
  items: PathItemResponse[];
}

export interface TopicNodeData {
  kind: "topic";
  sectionKey: string;
  title: string;
  count: number;
}

export interface SubtopicNodeData {
  kind: "subtopic";
  item: PathItemResponse;
  isRecommended: boolean;
}

export type LearningPathNodeData = TopicNodeData | SubtopicNodeData;

export interface FlowNode<TData = LearningPathNodeData> {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: TData;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
}

export interface FlowModel {
  nodes: FlowNode[];
  edges: FlowEdge[];
  sectionSummaries: SectionSummary[];
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "section";
}

export function sortByOrder(items: PathItemResponse[]): PathItemResponse[] {
  return [...items].sort((a, b) => a.order_index - b.order_index);
}

export function computeRecommendedNext(items: PathItemResponse[]): string | null {
  return sortByOrder(items).find((item) => item.status === "pending" && item.action !== "skip")?.id ?? null;
}

export function groupByWeek(items: PathItemResponse[]): TimelineResponse {
  const grouped = new Map<number, PathItemResponse[]>();
  for (const item of sortByOrder(items)) {
    if (!isVisibleInTimeline(item)) continue;
    const week = item.week_number ?? 1;
    grouped.set(week, [...(grouped.get(week) ?? []), item]);
  }

  const entries: WeekEntry[] = [...grouped.entries()]
    .sort(([a], [b]) => a - b)
    .map(([week, learning_units]) => ({
      week,
      learning_units,
      total_hours: Number(
        learning_units.reduce((sum, item) => sum + (item.estimated_hours ?? 0), 0).toFixed(4),
      ),
    }));

  return { total_weeks: entries.length, items: entries };
}

export function pathToFlow(items: PathItemResponse[]): FlowModel {
  const ordered = sortByOrder(items);
  const recommendedId = computeRecommendedNext(ordered);
  const sections: SectionSummary[] = [];
  const sectionByTitle = new Map<string, SectionSummary>();

  for (const item of ordered) {
    const title = item.section_title || "Khác";
    let section = sectionByTitle.get(title);
    if (!section) {
      section = {
        key: `section-${item.order_index}-${slugify(title)}`,
        title,
        items: [],
      };
      sectionByTitle.set(title, section);
      sections.push(section);
    }
    section.items.push(item);
  }

  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];

  for (const section of sections) {
    const topicId = `topic-${section.key}`;
    nodes.push({
      id: topicId,
      type: "topic",
      position: { x: 0, y: 0 },
      data: {
        kind: "topic",
        sectionKey: section.key,
        title: section.title,
        count: section.items.length,
      },
    });

    const first = section.items[0];
    if (first) {
      edges.push({
        id: `${topicId}-unit-${first.id}`,
        source: topicId,
        target: `unit-${first.id}`,
        type: "smoothstep",
      });
    }
  }

  for (const item of ordered) {
    nodes.push({
      id: `unit-${item.id}`,
      type: "subtopic",
      position: { x: 0, y: 0 },
      data: {
        kind: "subtopic",
        item,
        isRecommended: item.id === recommendedId,
      },
    });
  }

  for (let idx = 0; idx < ordered.length - 1; idx += 1) {
    const source = ordered[idx];
    const target = ordered[idx + 1];
    edges.push({
      id: `unit-${source.id}-unit-${target.id}`,
      source: `unit-${source.id}`,
      target: `unit-${target.id}`,
      type: "smoothstep",
      animated: target.id === recommendedId,
    });
  }

  return { nodes, edges, sectionSummaries: sections };
}
