import type { PathItemResponse, TimelineResponse, WeekEntry } from "@/types";
import {
  isDoneForPlannerProgress,
  isIncludedInMainPath,
  isOptionalIntroItem,
  isVisibleInMainPath,
  isVisibleInTimeline,
} from "./lib/status";

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

export interface TimelineLectureGroup {
  key: string;
  title: string;
  learning_units: PathItemResponse[];
  total_hours: number;
}

export interface TimelineCourseGroup {
  key: string;
  course_id: string | null;
  course_title: string;
  lectures: TimelineLectureGroup[];
  total_hours: number;
}

export interface CurrentWeekPlan {
  week: number;
  learning_units: PathItemResponse[];
  total_hours: number;
  courses: TimelineCourseGroup[];
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

function extractLectureNumber(title: string | null | undefined): number | null {
  const match = title?.match(/\blecture\s+(\d+)\b/i);
  if (!match) return null;
  return Number.parseInt(match[1], 10);
}

function courseKey(item: PathItemResponse): string {
  return item.course_id || item.course_title || "";
}

export function sortByPlannerDisplayOrder(
  items: PathItemResponse[],
): PathItemResponse[] {
  const firstCourseOrder = new Map<string, number>();
  for (const item of sortByOrder(items)) {
    const key = courseKey(item);
    if (!firstCourseOrder.has(key)) {
      firstCourseOrder.set(key, item.order_index);
    }
  }

  return [...items].sort((a, b) => {
    const courseDiff =
      (firstCourseOrder.get(courseKey(a)) ?? Number.MAX_SAFE_INTEGER) -
      (firstCourseOrder.get(courseKey(b)) ?? Number.MAX_SAFE_INTEGER);
    if (courseDiff !== 0) return courseDiff;

    const aLecture = extractLectureNumber(a.section_title);
    const bLecture = extractLectureNumber(b.section_title);
    if (aLecture != null && bLecture != null && aLecture !== bLecture) {
      return aLecture - bLecture;
    }
    if (aLecture != null && bLecture == null) return -1;
    if (aLecture == null && bLecture != null) return 1;

    return a.order_index - b.order_index;
  });
}

export function computeRecommendedNext(items: PathItemResponse[]): string | null {
  return sortByPlannerDisplayOrder(items).find((item) =>
    item.status === "pending" &&
    isVisibleInMainPath(item) &&
    !isOptionalIntroItem(item)
  )?.id ?? null;
}

export function groupByWeek(items: PathItemResponse[]): TimelineResponse {
  const grouped = new Map<number, PathItemResponse[]>();
  for (const item of sortByPlannerDisplayOrder(items)) {
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

export function normalizeTimelineOrder(timeline: TimelineResponse): TimelineResponse {
  return {
    ...timeline,
    items: timeline.items
      .map((week) => ({
        ...week,
        learning_units: sortByPlannerDisplayOrder(week.learning_units).filter(isVisibleInTimeline),
      }))
      .sort((a, b) => a.week - b.week),
  };
}

function roundHours(hours: number): number {
  return Number(hours.toFixed(4));
}

export function buildCurrentWeekPlan(
  items: PathItemResponse[],
  weeklyHours: number | null | undefined,
): CurrentWeekPlan {
  const budget = weeklyHours && weeklyHours > 0 ? weeklyHours : 5;
  const candidates = sortByPlannerDisplayOrder(items).filter(
    (item) => isVisibleInTimeline(item) && !isDoneForPlannerProgress(item),
  );
  const learningUnits: PathItemResponse[] = [];
  let totalHours = 0;

  for (const item of candidates) {
    learningUnits.push(item);
    totalHours += item.estimated_hours ?? 0;
    if (totalHours >= budget) break;
  }

  const courses: TimelineCourseGroup[] = [];
  const courseByKey = new Map<string, TimelineCourseGroup>();

  for (const item of learningUnits) {
    const key = courseKey(item) || "course";
    let course = courseByKey.get(key);
    if (!course) {
      course = {
        key,
        course_id: item.course_id ?? null,
        course_title: item.course_title || "Learning Path",
        lectures: [],
        total_hours: 0,
      };
      courseByKey.set(key, course);
      courses.push(course);
    }

    const title = item.section_title || "Other";
    const lectureKey = `${key}:${slugify(title)}`;
    let lecture = course.lectures.find((candidate) => candidate.key === lectureKey);
    if (!lecture) {
      lecture = {
        key: lectureKey,
        title,
        learning_units: [],
        total_hours: 0,
      };
      course.lectures.push(lecture);
    }

    lecture.learning_units.push(item);
    lecture.total_hours = roundHours(lecture.total_hours + (item.estimated_hours ?? 0));
    course.total_hours = roundHours(course.total_hours + (item.estimated_hours ?? 0));
  }

  return {
    week: 1,
    learning_units: learningUnits,
    total_hours: roundHours(totalHours),
    courses,
  };
}

export function pathToFlow(items: PathItemResponse[]): FlowModel {
  const ordered = sortByOrder(items).filter(isIncludedInMainPath);
  const recommendedId = computeRecommendedNext(ordered);
  const sections: SectionSummary[] = [];
  const sectionByKey = new Map<string, SectionSummary>();

  for (const item of ordered) {
    const title = item.section_title || "Other";
    const courseKey = item.course_id || `course-${slugify(item.course_title || "course")}`;
    const sectionKey = `${courseKey}:${slugify(title)}`;
    let section = sectionByKey.get(sectionKey);
    if (!section) {
      section = {
        key: sectionKey,
        title,
        items: [],
      };
      sectionByKey.set(sectionKey, section);
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
