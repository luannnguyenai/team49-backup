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
      <section className="relative overflow-hidden rounded-2xl border-2 border-slate-800 bg-white p-5 shadow-[4px_4px_0px_#e2e8f0] md:p-8 md:shadow-[8px_8px_0px_#e2e8f0]">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.035]"
          style={{
            backgroundImage: "radial-gradient(circle at 2px 2px, #000 1px, transparent 0)",
            backgroundSize: "24px 24px",
          }}
        />

        <div className="relative z-10 mb-8 flex flex-col justify-between gap-4 border-b-2 border-slate-100 pb-6 sm:flex-row sm:items-end">
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

        <div className="relative z-10 space-y-10">
          {weekPlan.courses.map((course) => {
            const display = courseTitleParts(course.course_title);
            return (
              <div key={course.key} className="rounded-2xl border-2 border-slate-800 bg-white/90 p-5 shadow-[4px_4px_0px_#e2e8f0] md:p-7">
                <div className="mb-8 flex items-start justify-between gap-4 border-b-2 border-slate-100 pb-6">
                  <div>
                    {display.code ? (
                      <span className="-rotate-2 inline-flex rounded-lg border-2 border-blue-200 bg-blue-50 px-3 py-1 text-lg font-extrabold tracking-wide text-blue-600 shadow-[2px_2px_0px_#bfdbfe]">
                        {display.code}
                      </span>
                    ) : null}
                    <h4 className="mt-3 text-2xl font-extrabold tracking-tight text-slate-900 md:text-3xl">
                      {display.title}
                    </h4>
                  </div>
                  <div className="shrink-0 text-right text-sm font-semibold text-slate-500">
                    <p>{formatDurationFromHours(course.total_hours) ?? "0 phút"}</p>
                    <p className="mt-1">{course.lectures.length} lecture</p>
                  </div>
                </div>

                <div className="relative px-0 md:px-4">
                  <div className="absolute left-[23px] top-6 bottom-4 w-0 border-l-2 border-dashed border-blue-500 md:left-[47px]" />
                  {course.lectures.map((lecture, index) => {
                    const isExpanded = expandedLectures.has(lecture.key);
                    return (
                      <div key={lecture.key} className="relative flex items-start gap-4 pb-5 md:gap-6">
                        <div className="relative z-10 mt-3 shrink-0">
                          <span className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-full border-2 border-slate-800 text-lg font-extrabold text-slate-900 shadow-[2px_2px_0px_#1e293b] md:h-16 md:w-16 md:text-2xl",
                            isExpanded ? "bg-yellow-300" : "bg-white",
                          )}>
                            {index + 1}
                          </span>
                        </div>
                        <div className="min-w-0 flex-1">
                          <button
                            type="button"
                            onClick={() => toggleLecture(lecture.key)}
                            className={cn(
                              "flex w-full items-center justify-between gap-4 rounded-xl border-2 bg-white p-4 text-left transition-all md:p-5",
                              isExpanded
                                ? "border-slate-800 shadow-[2px_2px_0px_#1e293b] translate-y-[2px]"
                                : "border-slate-800 shadow-[4px_4px_0px_#1e293b] hover:translate-y-[1px] hover:bg-slate-50 hover:shadow-[3px_3px_0px_#1e293b]",
                            )}
                          >
                            <div>
                              <p className="text-lg font-extrabold leading-tight text-slate-900 md:text-xl">
                                {lecture.title}
                              </p>
                              <p className="mt-1 text-sm font-semibold text-slate-500">
                                {lecture.learning_units.length} bài · {formatDurationFromHours(lecture.total_hours) ?? "0 phút"}
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
                          </button>

                          {isExpanded ? (
                            <div className="mt-4 grid gap-3 pl-0 md:grid-cols-2 md:pl-2">
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
