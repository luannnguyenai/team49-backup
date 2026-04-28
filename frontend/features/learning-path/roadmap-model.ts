import type { PathItemResponse, PathStatus } from "@/types";
import { computeRecommendedNext, sortByOrder } from "./presenters";

const START_X = 56;
const START_Y = 40;
const COURSE_WIDTH = 640;
const COURSE_PADDING_X = 24;
const COURSE_PADDING_Y = 24;
const COURSE_HEADER_HEIGHT = 72;
const TOPIC_WIDTH = 360;
const TOPIC_HEIGHT = 58;
const UNIT_WIDTH = 520;
const UNIT_HEIGHT = 112;
const TOPIC_TO_UNIT_GAP = 24;
const UNIT_GAP = 26;
const LECTURE_GAP = 48;
const COURSE_GAP = 52;
const CANVAS_MIN_WIDTH = 760;
const CANVAS_MIN_HEIGHT = 520;

export type RoadmapNodeKind = "course" | "topic" | "unit";

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

function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "group";
}

function courseTitleFor(item: PathItemResponse): string {
  return item.course_title || "Course";
}

function courseKeyFor(item: PathItemResponse, fallbackIndex: number): string {
  return item.course_id || `course-${fallbackIndex}-${slugify(courseTitleFor(item))}`;
}

interface LectureGroup {
  key: string;
  title: string;
  items: PathItemResponse[];
}

interface CourseGroup {
  key: string;
  title: string;
  items: PathItemResponse[];
  lectures: LectureGroup[];
}

function groupByCourseAndLecture(items: PathItemResponse[]): CourseGroup[] {
  const groups: CourseGroup[] = [];
  const groupByCourse = new Map<string, CourseGroup>();

  for (const item of items) {
    const fallbackIndex = groups.length;
    const courseKey = courseKeyFor(item, fallbackIndex);
    let course = groupByCourse.get(courseKey);
    if (!course) {
      course = {
        key: courseKey,
        title: courseTitleFor(item),
        items: [],
        lectures: [],
      };
      groupByCourse.set(courseKey, course);
      groups.push(course);
    }
    course.items.push(item);

    const lectureTitle = item.section_title || "Khác";
    const lectureKey = `${courseKey}:${slugify(lectureTitle)}`;
    let lecture = course.lectures.find((candidate) => candidate.key === lectureKey);
    if (!lecture) {
      lecture = {
        key: lectureKey,
        title: lectureTitle,
        items: [],
      };
      course.lectures.push(lecture);
    }
    lecture.items.push(item);
  }

  return groups;
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

  const recommendedId = computeRecommendedNext(visibleItems);
  const courses = groupByCourseAndLecture(visibleItems);
  const nodes: RoadmapNodeModel[] = [];
  const connectors: RoadmapConnectorModel[] = [];
  let y = START_Y;

  for (const course of courses) {
    const courseNode: RoadmapNodeModel = {
      id: `course-${slugify(course.key)}`,
      kind: "course",
      title: course.title,
      subtitle: `${course.lectures.length} lecture · ${course.items.length} bài học`,
      itemId: null,
      item: null,
      sectionKey: course.key,
      x: START_X,
      y,
      width: COURSE_WIDTH,
      height: COURSE_PADDING_Y * 2,
      status: "topic",
      action: null,
      isRecommended: false,
      segmentPolicy: undefined,
    };
    nodes.push(courseNode);

    const innerX = START_X + COURSE_PADDING_X;
    y += COURSE_PADDING_Y + COURSE_HEADER_HEIGHT;

    for (const lecture of course.lectures) {
      const topicNode: RoadmapNodeModel = {
        id: `topic-${slugify(lecture.key)}`,
        kind: "topic",
        title: lecture.title,
        subtitle: `${lecture.items.length} bài học`,
        itemId: null,
        item: null,
        sectionKey: lecture.key,
        x: innerX,
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

      let previousNode = topicNode;
      for (const item of lecture.items) {
        const unitNode: RoadmapNodeModel = {
          id: `unit-${item.id}`,
          kind: "unit",
          title: item.learning_unit_title,
          subtitle: item.section_title,
          itemId: item.id,
          item,
          sectionKey: lecture.key,
          x: innerX,
          y,
          width: UNIT_WIDTH,
          height: UNIT_HEIGHT,
          status: item.status,
          action: item.action,
          isRecommended: item.id === recommendedId,
          segmentPolicy: item.segment_policy,
        };
        nodes.push(unitNode);
        connectors.push({
          id: `${previousNode.id}-${unitNode.id}`,
          fromId: previousNode.id,
          toId: unitNode.id,
          isRecommended: unitNode.itemId === recommendedId,
        });
        previousNode = unitNode;
        y += UNIT_HEIGHT + UNIT_GAP;
      }

      y += LECTURE_GAP - UNIT_GAP;
    }

    courseNode.height = Math.max(y - courseNode.y + COURSE_PADDING_Y - LECTURE_GAP + UNIT_GAP, COURSE_PADDING_Y * 2);
    y = courseNode.y + courseNode.height + COURSE_GAP;
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
