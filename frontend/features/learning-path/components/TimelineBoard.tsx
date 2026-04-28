import { useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDurationFromHours } from "../lib/duration";
import { buildCurrentWeekPlan, computeRecommendedNext } from "../presenters";
import { useLearningPathStore } from "../store";
import LearningUnitCard from "./cards/LearningUnitCard";

function courseTitleParts(title: string): { code: string | null; title: string } {
  const match = title.match(/^\s*([A-Z]{2,}\d{2,}[a-zA-Z]?)\s*:\s*(.+)$/);
  if (!match) return { code: null, title };
  return { code: match[1], title: match[2] };
}

export default function TimelineBoard() {
  const items = useLearningPathStore((s) => s.items);
  const profile = useLearningPathStore((s) => s.profile);
  const selectItem = useLearningPathStore((s) => s.selectItem);

  const weekPlan = useMemo(
    () => buildCurrentWeekPlan(items, profile?.weeklyHours ?? null),
    [items, profile?.weeklyHours],
  );
  const recommendedId = useMemo(() => computeRecommendedNext(items), [items]);
  const firstLectureKey = weekPlan.courses[0]?.lectures[0]?.key ?? null;
  const [expandedLectures, setExpandedLectures] = useState<Set<string>>(
    () => new Set(firstLectureKey ? [firstLectureKey] : []),
  );

  useEffect(() => {
    setExpandedLectures(new Set(firstLectureKey ? [firstLectureKey] : []));
  }, [firstLectureKey]);

  const toggleLecture = (lectureKey: string) => {
    setExpandedLectures((current) => {
      const next = new Set(current);
      if (next.has(lectureKey)) {
        next.delete(lectureKey);
      } else {
        next.add(lectureKey);
      }
      return next;
    });
  };

  if (weekPlan.learning_units.length === 0) {
    return (
      <div
        className="rounded-2xl border p-6 text-sm"
        style={{
          borderColor: "var(--border)",
          color: "var(--text-secondary)",
          backgroundColor: "var(--bg-card)",
        }}
      >
        Không còn bài mới trong tuần này. Các bài đã skip, đã hoàn thành và intro optional không được đưa vào lịch tuần.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section
        className="rounded-2xl border p-5"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
      >
        <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-primary-600">
              Tuần {weekPlan.week}
            </p>
            <h3 className="mt-1 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              Việc cần học tiếp theo
            </h3>
            <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
              Đã ẩn phần skip, đã hoàn thành và intro optional.
            </p>
          </div>
          <div className="text-sm sm:text-right" style={{ color: "var(--text-secondary)" }}>
            <p>
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                {formatDurationFromHours(weekPlan.total_hours) ?? "0 phút"}
              </span>{" "}
              / {formatDurationFromHours(profile?.weeklyHours ?? 5) ?? "5 giờ"}
            </p>
            <p>{weekPlan.learning_units.length} bài trong tuần này</p>
          </div>
        </div>

        <div className="space-y-6">
          {weekPlan.courses.map((course) => {
            const display = courseTitleParts(course.course_title);
            return (
              <div key={course.key} className="rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
                <div className="mb-4 flex items-start justify-between gap-3 border-b pb-4" style={{ borderColor: "var(--border)" }}>
                  <div>
                    {display.code ? (
                      <span className="inline-flex rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-600">
                        {display.code}
                      </span>
                    ) : null}
                    <h4 className="mt-2 text-xl font-bold" style={{ color: "var(--text-primary)" }}>
                      {display.title}
                    </h4>
                  </div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                    {formatDurationFromHours(course.total_hours) ?? "0 phút"}
                  </p>
                </div>

                <div className="space-y-3">
                  {course.lectures.map((lecture, index) => {
                    const isExpanded = expandedLectures.has(lecture.key);
                    return (
                      <div key={lecture.key} className="grid grid-cols-[42px_1fr] gap-3">
                        <div className="flex justify-center pt-1">
                          <span className="flex h-9 w-9 items-center justify-center rounded-full border bg-slate-50 text-sm font-bold text-slate-700">
                            {index + 1}
                          </span>
                        </div>
                        <div>
                          <button
                            type="button"
                            onClick={() => toggleLecture(lecture.key)}
                            className={cn(
                              "flex w-full items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition",
                              isExpanded ? "border-slate-900 shadow-[2px_2px_0px_#1e293b]" : "hover:border-slate-400",
                            )}
                            style={{ backgroundColor: "var(--bg-card)" }}
                          >
                            <div>
                              <p className="font-bold" style={{ color: "var(--text-primary)" }}>
                                {lecture.title}
                              </p>
                              <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
                                {lecture.learning_units.length} bài · {formatDurationFromHours(lecture.total_hours) ?? "0 phút"}
                              </p>
                            </div>
                            <span
                              className={cn(
                                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 transition-transform",
                                isExpanded && "rotate-180",
                              )}
                            >
                              <ChevronDown className="h-4 w-4" />
                            </span>
                          </button>

                          {isExpanded ? (
                            <div className="mt-3 grid gap-3 md:grid-cols-2">
                              {lecture.learning_units.map((item) => (
                                <LearningUnitCard
                                  key={item.id}
                                  item={item}
                                  isRecommended={item.id === recommendedId}
                                  onClick={() => selectItem(item.id)}
                                />
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
