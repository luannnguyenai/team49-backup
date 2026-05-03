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
        There are no new lessons for this week. Skipped, completed, and optional intro items are excluded from the weekly plan.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="relative overflow-hidden rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-50 via-slate-50 to-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.08)] md:p-8">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage: "radial-gradient(circle at 2px 2px, #2563eb 1px, transparent 0)",
            backgroundSize: "28px 28px",
          }}
        />

        <div className="relative z-10 mb-8 flex flex-col justify-between gap-4 rounded-2xl border border-white/70 bg-white/75 p-5 shadow-sm backdrop-blur sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-primary-600">
              Week {weekPlan.week}
            </p>
            <h3 className="mt-1 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              What to learn next
            </h3>
            <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
              Skipped, completed, and optional intro items are hidden.
            </p>
          </div>
          <div className="text-sm sm:text-right" style={{ color: "var(--text-secondary)" }}>
            <p>
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                {formatDurationFromHours(weekPlan.total_hours) ?? "0 min"}
              </span>{" "}
              / {formatDurationFromHours(profile?.weeklyHours ?? 5) ?? "5 hours"}
            </p>
            <p>{weekPlan.learning_units.length} lessons this week</p>
          </div>
        </div>

        <div className="relative z-10 space-y-8">
          {weekPlan.courses.map((course) => {
            const display = courseTitleParts(course.course_title);
            return (
              <div key={course.key} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_14px_35px_rgba(15,23,42,0.10)] ring-1 ring-white md:p-7">
                <div className="mb-8 flex items-start justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-4 ring-1 ring-slate-100">
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
                    <p>{formatDurationFromHours(course.total_hours) ?? "0 min"}</p>
                    <p className="mt-1">{course.lectures.length} lectures</p>
                  </div>
                </div>

                <div className="relative px-0 md:px-4">
                  <div className="absolute left-[23px] top-7 bottom-6 w-0 border-l-2 border-dashed border-blue-300 md:left-[47px]" />
                  {course.lectures.map((lecture, index) => {
                    const isExpanded = expandedLectures.has(lecture.key);
                    return (
                      <div key={lecture.key} className="relative flex items-start gap-4 pb-6 last:pb-0 md:gap-6">
                        <div className="relative z-10 mt-4 shrink-0">
                          <span className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-full border text-lg font-extrabold shadow-sm md:h-16 md:w-16 md:text-2xl",
                            isExpanded
                              ? "border-blue-300 bg-blue-100 text-blue-700"
                              : "border-slate-200 bg-white text-slate-700",
                          )}>
                            {index + 1}
                          </span>
                        </div>
                        <div className="min-w-0 flex-1">
                          <button
                            type="button"
                            onClick={() => toggleLecture(lecture.key)}
                            className={cn(
                              "flex w-full items-center justify-between gap-4 rounded-2xl border bg-white p-4 text-left transition-all md:p-5",
                              isExpanded
                                ? "border-blue-200 shadow-[0_10px_24px_rgba(37,99,235,0.14)] ring-1 ring-blue-100"
                                : "border-slate-200 shadow-sm hover:border-slate-300 hover:shadow-md",
                            )}
                          >
                            <div>
                              <p className="text-lg font-extrabold leading-tight text-slate-900 md:text-xl">
                                {lecture.title}
                              </p>
                              <p className="mt-1 text-sm font-semibold text-slate-500">
                                {lecture.learning_units.length} lessons · {formatDurationFromHours(lecture.total_hours) ?? "0 min"}
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
                            <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50/80 p-3 md:p-4">
                              <div className="grid gap-3 md:grid-cols-2">
                              {lecture.learning_units.map((item) => (
                                <LearningUnitCard
                                  key={item.id}
                                  item={item}
                                  isRecommended={item.id === recommendedId}
                                  onClick={() => selectItem(item.id)}
                                />
                              ))}
                              </div>
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
