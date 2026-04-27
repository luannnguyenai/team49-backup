import type { PathItemResponse, PathStatus } from "@/types";
import { computeRecommendedNext, pathToFlow, sortByOrder } from "./presenters";

const START_X = 96;
const START_Y = 56;
const TOPIC_WIDTH = 280;
const TOPIC_HEIGHT = 58;
const UNIT_WIDTH = 420;
const UNIT_HEIGHT = 92;
const TOPIC_TO_UNIT_GAP = 34;
const UNIT_GAP = 20;
const SECTION_GAP = 58;
const CANVAS_MIN_WIDTH = 1000;
const CANVAS_MIN_HEIGHT = 520;

export type RoadmapNodeKind = "topic" | "unit";

export interface RoadmapNodeModel {
  id: string;
  kind: RoadmapNodeKind;
  title: string;
  subtitle: string | null;
  itemId: string | null;
  item: PathItemResponse | null;
  sectionKey: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  status: PathStatus | "topic";
  action: PathItemResponse["action"] | null;
  isRecommended: boolean;
  segmentPolicy: PathItemResponse["segment_policy"];
}

export interface RoadmapConnectorModel {
  id: string;
  fromId: string;
  toId: string;
  isRecommended: boolean;
}

export interface RoadmapModel {
  width: number;
  height: number;
  nodes: RoadmapNodeModel[];
  connectors: RoadmapConnectorModel[];
}

function nodeRight(node: RoadmapNodeModel): number {
  return node.x + node.width;
}

function nodeBottom(node: RoadmapNodeModel): number {
  return node.y + node.height;
}

export function connectorPath(from: RoadmapNodeModel, to: RoadmapNodeModel): string {
  const fromX = from.x + from.width / 2;
  const fromY = from.y + from.height;
  const toX = to.x + to.width / 2;
  const toY = to.y;
  const midY = fromY + (toY - fromY) / 2;

  return `M ${fromX} ${fromY} C ${fromX} ${midY}, ${toX} ${midY}, ${toX} ${toY}`;
}

export function buildRoadmapModel(items: PathItemResponse[]): RoadmapModel {
  const visibleItems = sortByOrder(items).filter((item) => item.segment_policy !== "hidden");

  if (visibleItems.length === 0) {
    return {
      width: CANVAS_MIN_WIDTH,
      height: CANVAS_MIN_HEIGHT,
      nodes: [],
      connectors: [],
    };
  }

  const flow = pathToFlow(visibleItems);
  const recommendedId = computeRecommendedNext(visibleItems);
  const nodes: RoadmapNodeModel[] = [];
  const connectors: RoadmapConnectorModel[] = [];
  let y = START_Y;

  for (const section of flow.sectionSummaries) {
    const topicNode: RoadmapNodeModel = {
      id: `topic-${section.key}`,
      kind: "topic",
      title: section.title,
      subtitle: `${section.items.length} bài học`,
      itemId: null,
      item: null,
      sectionKey: section.key,
      x: START_X,
      y,
      width: TOPIC_WIDTH,
      height: TOPIC_HEIGHT,
      status: "topic",
      action: null,
      isRecommended: false,
      segmentPolicy: undefined,
    };
    nodes.push(topicNode);
    y += TOPIC_HEIGHT + TOPIC_TO_UNIT_GAP;

    for (const item of section.items) {
      const unitNode: RoadmapNodeModel = {
        id: `unit-${item.id}`,
        kind: "unit",
        title: item.learning_unit_title,
        subtitle: item.section_title,
        itemId: item.id,
        item,
        sectionKey: section.key,
        x: START_X,
        y,
        width: UNIT_WIDTH,
        height: UNIT_HEIGHT,
        status: item.status,
        action: item.action,
        isRecommended: item.id === recommendedId,
        segmentPolicy: item.segment_policy,
      };
      nodes.push(unitNode);
      y += UNIT_HEIGHT + UNIT_GAP;
    }

    y += SECTION_GAP - UNIT_GAP;
  }

  for (let index = 0; index < nodes.length - 1; index += 1) {
    const from = nodes[index];
    const to = nodes[index + 1];
    connectors.push({
      id: `${from.id}-${to.id}`,
      fromId: from.id,
      toId: to.id,
      isRecommended: to.kind === "unit" && to.itemId === recommendedId,
    });
  }

  const width = Math.max(...nodes.map(nodeRight), CANVAS_MIN_WIDTH - START_X) + START_X;
  const height = Math.max(...nodes.map(nodeBottom), CANVAS_MIN_HEIGHT - START_Y) + START_Y;

  return {
    width,
    height,
    nodes,
    connectors,
  };
}
