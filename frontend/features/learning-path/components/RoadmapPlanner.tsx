"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, ChevronDown, Circle, PlayCircle, SkipForward } from "lucide-react";
import type { PathItemResponse, PathStatus } from "@/types";
import { cn } from "@/lib/utils";
import { derivePlayerInsight, type PlayerProgressSnapshot } from "../player-insights";
import { describePlannerReason } from "../planner-reasons";
import { computeRecommendedNext, sortByOrder } from "../presenters";
import { getStatusLabel } from "../lib/status";
import PathRequiredState from "./PathRequiredState";
import PlayerInsightBadge from "./PlayerInsightBadge";

interface RoadmapPlannerProps {
  items: PathItemResponse[];
  currentProgress?: PlayerProgressSnapshot | null;
  onSelectItem?: (id: string) => void;
  onSelectSection?: (sectionKey: string) => void;
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

function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "group";
}

function statusIcon(status: PathStatus) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "in_progress") return <PlayCircle className="h-4 w-4" />;
  if (status === "skipped") return <SkipForward className="h-4 w-4" />;
  return <Circle className="h-4 w-4" />;
}

function groupPath(items: PathItemResponse[]): CourseGroup[] {
  const groups: CourseGroup[] = [];
  const courseByKey = new Map<string, CourseGroup>();

  for (const item of sortByOrder(items).filter((candidate) => candidate.segment_policy !== "hidden")) {
    const courseTitle = item.course_title || "Course";
    const courseKey = item.course_id || `course-${slugify(courseTitle)}`;
    let course = courseByKey.get(courseKey);
    if (!course) {
      course = {
        key: courseKey,
        title: courseTitle,
        items: [],
        lectures: [],
      };
      courseByKey.set(courseKey, course);
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

function unitStatusCounts(items: PathItemResponse[]) {
  return {
    completed: items.filter((item) => item.status === "completed").length,
    inProgress: items.filter((item) => item.status === "in_progress").length,
    skipped: items.filter((item) => item.status === "skipped").length,
  };
}

function UnitRow({
  item,
  isRecommended,
  currentProgress,
  onSelectItem,
}: {
  item: PathItemResponse;
  isRecommended: boolean;
  currentProgress?: PlayerProgressSnapshot | null;
  onSelectItem?: (id: string) => void;
}) {
  const insight =
    item.learning_unit_id === currentProgress?.learning_unit_id
      ? derivePlayerInsight(currentProgress)
      : null;

  return (
    <button
      type="button"
      onClick={() => onSelectItem?.(item.id)}
      className={cn(
        "w-full rounded-2xl border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md dark:bg-slate-950",
        isRecommended && "border-amber-300 ring-2 ring-amber-100 dark:ring-amber-950/50",
        item.status === "completed" && "opacity-75",
        item.status === "skipped" && "opacity-55",
      )}
      style={{ borderColor: isRecommended ? undefined : "var(--border)" }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="line-clamp-2 text-sm font-semibold leading-snug text-slate-950 dark:text-white">
            {item.learning_unit_title}
          </p>
          <p className="mt-1 line-clamp-1 text-xs text-slate-500 dark:text-slate-400">
            {item.section_title ?? "Khác"}
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {statusIcon(item.status)}
          {getStatusLabel(item.status)}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {isRecommended ? (
          <span className="rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-800">
            Nên học tiếp
          </span>
        ) : null}
        {item.reason_codes?.slice(0, 3).map((code) => {
          const reason = describePlannerReason(code);
          return (
            <span
              key={code}
              title={reason.details}
              className="rounded-full bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-200"
            >
              {reason.label}
            </span>
          );
        })}
      </div>
      {insight ? <PlayerInsightBadge insight={insight} /> : null}
    </button>
  );
}

export default function RoadmapPlanner({ items, currentProgress, onSelectItem }: RoadmapPlannerProps) {
  const courses = useMemo(() => groupPath(items), [items]);
  const recommendedId = useMemo(() => computeRecommendedNext(items), [items]);
  const [expandedLectureKeys, setExpandedLectureKeys] = useState<Set<string>>(() => new Set());

  if (courses.length === 0) {
    return <PathRequiredState />;
  }

  const toggleLecture = (lectureKey: string) => {
    setExpandedLectureKeys((current) => {
      const next = new Set(current);
      if (next.has(lectureKey)) {
        next.delete(lectureKey);
      } else {
        next.add(lectureKey);
      }
      return next;
    });
  };

  return (
    <div
      className="rounded-[28px] border bg-slate-50/80 p-3 shadow-sm dark:bg-slate-950/60 sm:p-5"
      style={{ borderColor: "var(--border)" }}
    >
      <div className="mx-auto max-w-4xl space-y-5">
        {courses.map((course, courseIndex) => {
          const counts = unitStatusCounts(course.items);
          return (
            <section
              key={course.key}
              className="overflow-hidden rounded-[24px] border bg-white shadow-sm dark:bg-slate-950"
              style={{ borderColor: "var(--border)" }}
            >
              <div
                className="border-b bg-gradient-to-r from-blue-50 via-white to-slate-50 px-4 py-4 dark:from-blue-950/30 dark:via-slate-950 dark:to-slate-950 sm:px-5"
                style={{ borderColor: "var(--border)" }}
              >
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-300">
                  Course {courseIndex + 1}
                </p>
                <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-slate-950 dark:text-white">{course.title}</h2>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {course.lectures.length} lectures · {course.items.length} units
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs font-medium">
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200">
                      {counts.completed} done
                    </span>
                    <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
                      {counts.inProgress} active
                    </span>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      {counts.skipped} skipped
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-2.5 p-3 sm:p-4">
                {course.lectures.map((lecture, lectureIndex) => {
                  const expanded = expandedLectureKeys.has(lecture.key);
                  const lectureCounts = unitStatusCounts(lecture.items);
                  const hasRecommended = lecture.items.some((item) => item.id === recommendedId);
                  return (
                    <article
                      key={lecture.key}
                      className={cn(
                        "rounded-2xl border bg-slate-50/70 transition dark:bg-slate-900/40",
                        expanded && "bg-white shadow-sm dark:bg-slate-950",
                        hasRecommended && !expanded && "border-amber-200 bg-amber-50/50 dark:border-amber-900 dark:bg-amber-950/20",
                      )}
                      style={{ borderColor: hasRecommended ? undefined : "var(--border)" }}
                    >
                      <button
                        type="button"
                        onClick={() => toggleLecture(lecture.key)}
                        className="flex w-full items-center justify-between gap-4 rounded-2xl px-4 py-3.5 text-left transition hover:bg-white dark:hover:bg-slate-900"
                        aria-expanded={expanded}
                      >
                        <div className="flex min-w-0 items-start gap-3">
                          <span
                            className={cn(
                              "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold",
                              hasRecommended ? "bg-amber-400 text-amber-950" : "bg-blue-600 text-white",
                            )}
                          >
                            {lectureIndex + 1}
                          </span>
                          <div className="min-w-0">
                            <h3 className="line-clamp-2 text-base font-semibold text-slate-950 dark:text-white">
                              {lecture.title}
                            </h3>
                            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                              {lecture.items.length} units · {lectureCounts.completed} done
                              {hasRecommended ? " · next up" : ""}
                            </p>
                          </div>
                        </div>
                        <ChevronDown
                          className={cn(
                            "h-5 w-5 shrink-0 text-slate-400 transition",
                            expanded && "rotate-180 text-blue-600",
                          )}
                        />
                      </button>

                      {expanded ? (
                        <div className="grid gap-3 border-t p-3 sm:grid-cols-2" style={{ borderColor: "var(--border)" }}>
                          {lecture.items.map((item) => (
                            <UnitRow
                              key={item.id}
                              item={item}
                              isRecommended={item.id === recommendedId}
                              currentProgress={currentProgress}
                              onSelectItem={onSelectItem}
                            />
                          ))}
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
