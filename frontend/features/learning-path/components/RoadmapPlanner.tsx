"use client";

import React, { useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Circle,
  FileText,
  HelpCircle,
  PlayCircle,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { PathItemResponse, PathStatus } from "@/types";
import { formatDurationFromHours } from "../lib/duration";
import {
  derivePlayerInsight,
  type PlayerProgressSnapshot,
} from "../player-insights";
import {
  isDoneForPlannerProgress,
  isIncludedInMainPath,
  isOptionalIntroItem,
} from "../lib/status";
import { describePlannerReason } from "../planner-reasons";
import { computeRecommendedNext, sortByOrder } from "../presenters";
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
  courseId: string | null;
  title: string;
  items: PathItemResponse[];
  lectures: LectureGroup[];
}

function slugify(value: string): string {
  return (
    value
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "group"
  );
}

function courseKeyFor(item: PathItemResponse): string {
  return item.course_id || `course-${slugify(item.course_title || "course")}`;
}

function lectureKeyFor(courseKey: string, lectureTitle: string): string {
  return `${courseKey}:${slugify(lectureTitle)}`;
}

function groupItemsByCourseAndLecture(
  items: PathItemResponse[],
): CourseGroup[] {
  const courseByKey = new Map<string, CourseGroup>();
  const courses: CourseGroup[] = [];

  for (const item of sortByOrder(items).filter(isIncludedInMainPath)) {
    const courseKey = courseKeyFor(item);
    let course = courseByKey.get(courseKey);
    if (!course) {
      course = {
        key: courseKey,
        courseId: item.course_id ?? null,
        title: item.course_title || "Learning Path",
        items: [],
        lectures: [],
      };
      courseByKey.set(courseKey, course);
      courses.push(course);
    }

    course.items.push(item);

    const lectureTitle = item.section_title || "Other";
    const lectureKey = lectureKeyFor(courseKey, lectureTitle);
    let lecture = course.lectures.find(
      (candidate) => candidate.key === lectureKey,
    );
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

  for (const course of courses) {
    course.lectures.sort(compareLectures);
  }

  return courses.sort(
    (a, b) => Number(isCourseComplete(a.items)) - Number(isCourseComplete(b.items)),
  );
}

function extractLectureNumber(title: string): number | null {
  const match = title.match(/\blecture\s+(\d+)\b/i);
  if (!match) return null;
  return Number.parseInt(match[1], 10);
}

function compareLectures(a: LectureGroup, b: LectureGroup): number {
  const aNumber = extractLectureNumber(a.title);
  const bNumber = extractLectureNumber(b.title);

  if (aNumber != null && bNumber != null && aNumber !== bNumber) {
    return aNumber - bNumber;
  }

  if (aNumber != null && bNumber == null) return -1;
  if (aNumber == null && bNumber != null) return 1;

  const aOrder = Math.min(
    ...a.items.map((item) => item.order_index ?? Number.MAX_SAFE_INTEGER),
  );
  const bOrder = Math.min(
    ...b.items.map((item) => item.order_index ?? Number.MAX_SAFE_INTEGER),
  );
  return aOrder - bOrder;
}

function statusIcon(status: PathStatus) {
  if (status === "completed")
    return <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />;
  if (status === "in_progress")
    return (
      <Circle className="h-5 w-5 shrink-0 fill-blue-500/20 text-blue-600" />
    );
  if (status === "skipped")
    return <ArrowRight className="h-5 w-5 shrink-0 text-slate-400" />;
  return <Circle className="h-5 w-5 shrink-0 text-slate-300" />;
}

function unitIconFor(item: PathItemResponse) {
  const color =
    item.status === "completed" ? "text-emerald-600" : "text-slate-600";
  if (item.has_quiz_items || item.reason_codes?.includes("quiz_available")) {
    return <HelpCircle className={cn("h-5 w-5", color)} />;
  }
  if (item.content_type === "video") {
    return <PlayCircle className={cn("h-5 w-5", color)} />;
  }
  return <FileText className={cn("h-5 w-5", color)} />;
}

function reasonIcon(code: string) {
  if (code === "critical_kp" || code === "required_prerequisite") {
    return <AlertTriangle className="h-3 w-3" />;
  }
  if (code === "quiz_available") {
    return <HelpCircle className="h-3 w-3" />;
  }
  if (code === "quick_review" || code === "skip_by_mastery") {
    return <CheckCircle2 className="h-3 w-3" />;
  }
  return null;
}

function reasonClassName(code: string): string {
  if (code === "critical_kp" || code === "required_prerequisite") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (code === "quiz_available") {
    return "border-blue-200 bg-blue-50 text-blue-800";
  }
  if (code === "high_salience") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (code === "quick_review" || code === "skip_by_mastery") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (code === "reference_only") {
    return "border-slate-200 bg-slate-50 text-slate-600";
  }
  return "border-slate-200 bg-slate-100 text-slate-700";
}

function countCompleted(items: PathItemResponse[]): number {
  return items.filter(isDoneForPlannerProgress).length;
}

function isCourseComplete(items: PathItemResponse[]): boolean {
  return items.length > 0 && items.every(isDoneForPlannerProgress);
}

function isOptionalIntroLecture(lecture: LectureGroup): boolean {
  return lecture.items.length > 0 && lecture.items.every(isOptionalIntroItem);
}

function isUuidLike(value: string | null | undefined): boolean {
  return Boolean(
    value?.match(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    ),
  );
}

function courseCodeFromTitle(title: string): string | null {
  const match = title.match(/^\s*([A-Z]{2,}\d{2,}[a-zA-Z]?)\s*:\s*/);
  return match?.[1] ?? null;
}

function cleanCourseTitle(title: string): string {
  const withoutCode = title
    .replace(/^\s*[A-Z]{2,}\d{2,}[a-zA-Z]?\s*:\s*/, "")
    .trim();
  return withoutCode.replace(/^Deep Learning for\s+/i, "").trim() || title;
}

function courseDisplay(course: CourseGroup): {
  code: string | null;
  title: string;
} {
  const codeFromTitle = courseCodeFromTitle(course.title);
  const codeFromId =
    course.courseId && !isUuidLike(course.courseId) ? course.courseId : null;

  return {
    code: codeFromTitle ?? codeFromId,
    title: cleanCourseTitle(course.title),
  };
}

function CourseCodeBadge({ code }: { code: string | null }) {
  if (!code) return null;
  return (
    <span className="-rotate-2 inline-flex rounded-lg border-2 border-blue-200 bg-blue-50 px-3.5 py-1 text-lg font-extrabold tracking-wide text-blue-600 shadow-[2px_2px_0px_#bfdbfe]">
      {code}
    </span>
  );
}

function UnitCard({
  item,
  isRecommended,
  currentProgress,
  onSelectItem,
}: {
  item: PathItemResponse;
  isRecommended: boolean;
  currentProgress?: PlayerProgressSnapshot | null;
  onSelectItem?: (id: string) => void;
  key?: React.Key;
}) {
  const isSkipped = item.action === "skip" || item.status === "skipped";
  const insight =
    item.learning_unit_id === currentProgress?.learning_unit_id
      ? derivePlayerInsight(currentProgress)
      : null;
  const estimatedTime = formatDurationFromHours(item.estimated_hours);

  return (
    <button
      type="button"
      onClick={() => onSelectItem?.(item.id)}
      className={cn(
        "group flex w-full flex-col rounded-xl border-2 bg-white p-4 text-left transition-all",
        onSelectItem && "cursor-pointer",
        isRecommended
          ? "border-blue-600 shadow-[3px_3px_0px_#3b82f6]"
          : "border-slate-200 hover:border-slate-800 hover:shadow-[3px_3px_0px_#1e293b]",
        item.status === "completed" && "opacity-75",
        isSkipped && "opacity-70",
      )}
    >
      <div className="flex w-full items-start gap-3">
        <div
          className={cn(
            "mt-0.5 rounded-lg border p-1.5",
            isRecommended
              ? "border-blue-200 bg-blue-50"
              : "border-slate-100 bg-slate-50",
          )}
        >
          {unitIconFor(item)}
        </div>
        <div className="min-w-0 flex-1 pr-2">
          <h4
            className={cn(
              "text-sm font-bold leading-tight text-slate-800 md:text-base",
              item.status === "completed" &&
              "text-slate-500 line-through decoration-slate-300",
            )}
          >
            {item.learning_unit_title}
          </h4>
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            {estimatedTime ? (
              <span className="flex items-center gap-1 text-xs font-semibold text-slate-500">
                <Clock className="h-3 w-3" />
                {estimatedTime}
              </span>
            ) : null}
            {isRecommended ? (
              <span className="flex items-center gap-1 text-[10px] uppercase border font-bold text-blue-800 border-blue-200 bg-blue-100 px-2 py-0.5 rounded-md">
                <PlayCircle className="h-3 w-3" />
                Next up
              </span>
            ) : null}
            {item.phase_tag === "phase_b" && item.is_locked ? (
              <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-500">
                Upcoming
              </span>
            ) : null}
            {isSkipped ? (
              <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-700">
                Skip
              </span>
            ) : null}
          </div>
        </div>
        <div className="mt-0.5 shrink-0">
          {isSkipped ? (
            <ArrowRight className="h-5 w-5 shrink-0 text-slate-400" />
          ) : (
            statusIcon(item.status)
          )}
        </div>
      </div>

      {insight ? (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <PlayerInsightBadge insight={insight} />
        </div>
      ) : null}

      {item.reason_codes?.length &&
        !item.reason_codes.includes("quiz_available") ? (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
          {item.reason_codes.slice(0, 4).map((code) => {
            const reason = describePlannerReason(code);
            return (
              <span
                key={code}
                title={reason.details}
                className={cn(
                  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase",
                  reasonClassName(code),
                )}
              >
                {reasonIcon(code)}
                {reason.label}
              </span>
            );
          })}
        </div>
      ) : null}

      {item.reason_codes?.includes("quiz_available") ? (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
          <span className="bg-purple-50 text-purple-700 border border-purple-200 text-[10px] uppercase font-bold px-2 py-0.5 rounded-md flex items-center gap-1">
            <HelpCircle className="w-3 h-3" /> Quiz
          </span>
        </div>
      ) : null}
    </button>
  );
}

export default function RoadmapPlanner({
  items,
  currentProgress,
  onSelectItem,
}: RoadmapPlannerProps) {
  const groupedCourses = useMemo(
    () => groupItemsByCourseAndLecture(items),
    [items],
  );
  const recommendedNextId = useMemo(
    () => computeRecommendedNext(items),
    [items],
  );
  const [expandedLectureKeys, setExpandedLectureKeys] = useState<Set<string>>(
    () => new Set(),
  );

  if (!groupedCourses.length) {
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
    <div className="mx-auto w-full max-w-[980px] py-8">
      {groupedCourses.map((course) => {
        const completedUnits = countCompleted(course.items);
        const totalUnits = course.items.length;
        const progressPercent =
          totalUnits > 0 ? Math.round((completedUnits / totalUnits) * 100) : 0;
        const display = courseDisplay(course);

        return (
          <section key={course.key} className="mb-12 md:mb-16">
            <div className="relative overflow-hidden rounded-2xl border-2 border-slate-800 bg-white p-5 shadow-[4px_4px_0px_#e2e8f0] md:p-8 md:shadow-[8px_8px_0px_#e2e8f0]">
              <div
                className="pointer-events-none absolute inset-0 opacity-[0.03]"
                style={{
                  backgroundImage:
                    "radial-gradient(circle at 2px 2px, #000 1px, transparent 0)",
                  backgroundSize: "24px 24px",
                }}
              />

              <div className="relative z-10 mb-10 flex flex-col justify-between gap-4 border-b-2 border-slate-100 pb-6 md:flex-row md:items-end">
                <div>
                  <CourseCodeBadge code={display.code} />
                  <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-800 md:text-4xl">
                    {display.title}
                  </h2>
                </div>
                <div className="flex shrink-0 flex-col gap-1 md:items-end">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-bold uppercase tracking-widest text-slate-500">
                      {progressPercent}% done
                    </span>
                    <div className="h-3 w-24 overflow-hidden rounded-full border-2 border-slate-800 bg-slate-100 shadow-[1px_1px_0px_#1e293b] transition-all hover:h-4 md:w-32">
                      <div
                        className="h-full rounded-r-none bg-blue-600 transition-all duration-500 ease-out"
                        style={{ width: `${progressPercent}%` }}
                      />
                    </div>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-slate-500">
                    {course.lectures.length} lectures · {totalUnits} units
                  </p>
                </div>
              </div>

              <div className="relative isolate px-0 md:px-4">
                <div className="absolute bottom-4 left-[23px] top-6 -z-10 w-0 border-l-[2px] border-dashed border-blue-600 md:left-[47px]" />

                {course.lectures.map((lecture, index) => {
                  const isExpanded = expandedLectureKeys.has(lecture.key);
                  const completedLectureUnits = countCompleted(lecture.items);
                  const expandedLectureItems = lecture.items;
                  const optionalIntro = isOptionalIntroLecture(lecture);
                  const isCompleted =
                    lecture.items.length > 0 &&
                    completedLectureUnits === lecture.items.length;
                  const isInProgress =
                    lecture.items.some(
                      (item) =>
                        item.status === "in_progress" ||
                        item.status === "completed",
                    ) && !isCompleted;
                  const hasRecommended = lecture.items.some(
                    (item) => item.id === recommendedNextId,
                  );

                  return (
                    <div
                      key={lecture.key}
                      className="relative flex items-start gap-4 pb-2 pt-4 md:gap-6 group/lecture"
                    >
                      <button
                        type="button"
                        onClick={() => toggleLecture(lecture.key)}
                        className="relative z-10 mt-[14px] flex shrink-0 cursor-pointer"
                        aria-label={`${isExpanded ? "Collapse" : "Expand"} ${lecture.title}`}
                      >
                        <span
                          className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-full border-2 border-slate-800 shadow-[2px_2px_0px_#1e293b] md:shadow-[3px_3px_0px_#1e293b] transition-transform hover:scale-110 md:h-16 md:w-16",
                            isCompleted && "bg-emerald-400",
                            isInProgress && "bg-[#fde047]",
                            optionalIntro &&
                            !isCompleted &&
                            !isInProgress &&
                            "bg-blue-100",
                            hasRecommended &&
                            !isCompleted &&
                            !isInProgress &&
                            !optionalIntro &&
                            "bg-blue-100",
                            !isCompleted &&
                            !isInProgress &&
                            !hasRecommended &&
                            !optionalIntro &&
                            "bg-white",
                          )}
                        >
                          {isCompleted ? (
                            <CheckCircle2 className="h-6 w-6 text-slate-800 md:h-8 md:w-8" />
                          ) : (
                            <span className="text-lg font-bold text-slate-800 md:text-2xl">
                              {index + 1}
                            </span>
                          )}
                        </span>
                      </button>

                      <div className="min-w-0 flex-1 pb-4">
                        <button
                          type="button"
                          onClick={() => toggleLecture(lecture.key)}
                          className={cn(
                            "w-full rounded-xl border-2 border-slate-800 bg-white p-4 text-left transition-all md:p-5",
                            isExpanded
                              ? "translate-y-[2px] shadow-[2px_2px_0px_#1e293b]"
                              : "shadow-[4px_4px_0px_#1e293b] hover:translate-y-[1px] hover:bg-slate-50 hover:shadow-[3px_3px_0px_#1e293b]",
                            hasRecommended &&
                            "bg-amber-50 border-amber-200",
                            optionalIntro &&
                            !hasRecommended &&
                            !isExpanded &&
                            "bg-blue-50 border-blue-200",
                          )}
                          aria-expanded={isExpanded}
                        >
                          <div className="flex items-center justify-between gap-4">
                            <div className="min-w-0">
                              <h3 className="text-lg font-extrabold leading-tight text-slate-800 md:text-xl">
                                {lecture.title}
                              </h3>
                              <p className="mt-1 text-sm font-semibold text-slate-500">
                                {completedLectureUnits} / {lecture.items.length}{" "}
                                units
                                {hasRecommended ? " · next up here" : ""}
                                {optionalIntro && !hasRecommended
                                  ? " · optional intro"
                                  : ""}
                              </p>
                            </div>
                            <span
                              className={cn(
                                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 transition-transform",
                                isExpanded && "rotate-180",
                              )}
                            >
                              <ChevronDown className="h-5 w-5 text-slate-600" />
                            </span>
                          </div>
                        </button>

                        <AnimatePresence>
                          {isExpanded && expandedLectureItems.length > 0 && (
                            <motion.div
                              initial={{ opacity: 0, height: 0, marginTop: 0 }}
                              animate={{
                                opacity: 1,
                                height: "auto",
                                marginTop: 16,
                              }}
                              exit={{ opacity: 0, height: 0, marginTop: 0 }}
                              transition={{ duration: 0.2, ease: "easeOut" }}
                              className="overflow-hidden relative"
                            >
                              <div className="grid grid-cols-1 gap-3 pb-2 pl-0 lg:grid-cols-2 lg:pl-2">
                                {expandedLectureItems.map((item) => (
                                  <UnitCard
                                    key={item.id}
                                    item={item}
                                    isRecommended={
                                      item.id === recommendedNextId
                                    }
                                    currentProgress={currentProgress}
                                    onSelectItem={onSelectItem}
                                  />
                                ))}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        );
      })}
    </div>
  );
}
