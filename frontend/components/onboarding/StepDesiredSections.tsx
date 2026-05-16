"use client";
// components/onboarding/StepDesiredSections.tsx
// Step 2 — "What do you want to study?"
// Large selectable cards, one per course section.

import { BookOpen, Check, Clock, Code2, Database, Layers } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { BootstrapCourseOption } from "@/types";

const MODULE_CONFIGS: Array<{
  gradient: string;
  Icon: LucideIcon;
}> = [
  { gradient: "from-blue-500 to-indigo-600",   Icon: Code2     },
  { gradient: "from-purple-500 to-violet-600",  Icon: Database  },
  { gradient: "from-emerald-500 to-teal-600",   Icon: BookOpen  },
  { gradient: "from-orange-500 to-amber-600",   Icon: Layers    },
  { gradient: "from-rose-500 to-pink-600",      Icon: BookOpen  },
];

interface Props {
  courses: BootstrapCourseOption[];
  topicCountsByCourseId: Record<string, number>;
  selectedIds: string[];
  onToggle: (id: string) => void;
  error?: string;
}

export default function StepDesiredSections({
  courses,
  topicCountsByCourseId,
  selectedIds,
  onToggle,
  error,
}: Props) {
  const selectedSet = new Set(selectedIds);

  return (
    <div className="space-y-3">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Choose one or more courses you want to pursue.
        {selectedIds.length > 0 && (
          <span className="ml-2 font-semibold text-primary-600">
            ({selectedIds.length} selected)
          </span>
        )}
      </p>

      {courses.length === 0 && (
        <div className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          No courses available to display.
        </div>
      )}

      {courses.map((course, idx) => {
        const isSelected = selectedSet.has(course.canonical_course_id);
        const { gradient, Icon } = MODULE_CONFIGS[idx % MODULE_CONFIGS.length];
        const topicCount = topicCountsByCourseId[course.canonical_course_id] ?? 0;

        return (
          <button
            key={course.canonical_course_id}
            type="button"
            onClick={() => onToggle(course.canonical_course_id)}
            className={cn(
              "w-full rounded-xl border-2 p-4 text-left",
              "transition-all duration-150 hover:shadow-md active:scale-[0.99]",
              isSelected
                ? "border-primary-500 bg-primary-50"
                : "hover:border-slate-300"
            )}
            style={{
              borderColor: isSelected ? undefined : "var(--border)",
              backgroundColor: isSelected ? undefined : "var(--bg-card)",
            }}
          >
            <div className="flex items-start gap-4">
              {/* Gradient icon */}
              <div
                className={cn(
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
                  "bg-gradient-to-br text-white shadow-sm",
                  gradient
                )}
              >
                <Icon className="h-5 w-5" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h3
                    className="font-semibold"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {course.title}
                  </h3>
                  {isSelected && (
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-600">
                      <Check className="h-3.5 w-3.5 text-white" />
                    </span>
                  )}
                </div>

                {course.short_description && (
                  <p
                    className="mt-0.5 line-clamp-2 text-sm"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {course.short_description}
                  </p>
                )}

                {/* Meta badges */}
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <span
                    className="flex items-center gap-1 text-xs"
                    style={{ color: "var(--text-muted)" }}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    {topicCount} topics
                  </span>
                  <span
                    className="flex items-center gap-1 text-xs"
                    style={{ color: "var(--text-muted)" }}
                  >
                    <Clock className="h-3.5 w-3.5" />
                    {course.hero_badge ?? "Open now"}
                  </span>
                </div>
              </div>
            </div>
          </button>
        );
      })}

      {error && <p className="error-msg">{error}</p>}
    </div>
  );
}
