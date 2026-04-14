"use client";
// components/onboarding/StepKnownTopics.tsx
// Step 1 — "Bạn đã biết gì?"
// Displays all topics grouped by module as a checkbox card grid.

import { Check, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleDetail } from "@/types";

// One color palette entry per module (cycles if > 5 modules)
const MODULE_PALETTES = [
  { dot: "bg-blue-500",   ring: "ring-blue-200 dark:ring-blue-800" },
  { dot: "bg-purple-500", ring: "ring-purple-200 dark:ring-purple-800" },
  { dot: "bg-emerald-500",ring: "ring-emerald-200 dark:ring-emerald-800" },
  { dot: "bg-orange-500", ring: "ring-orange-200 dark:ring-orange-800" },
  { dot: "bg-rose-500",   ring: "ring-rose-200 dark:ring-rose-800" },
] as const;

interface Props {
  modules: ModuleDetail[];
  selectedIds: string[];
  onToggle: (id: string) => void;
}

export default function StepKnownTopics({ modules, selectedIds, onToggle }: Props) {
  const selectedSet = new Set(selectedIds);
  const totalTopics = modules.reduce((n, m) => n + m.topics.length, 0);

  return (
    <div className="space-y-6">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Chọn những topics bạn đã nắm — hệ thống sẽ đánh giá kiến thức của bạn
        với <span className="font-semibold" style={{ color: "var(--text-primary)" }}>5 câu hỏi mỗi topic</span>.{" "}
        <span className="font-medium" style={{ color: "var(--text-primary)" }}>
          Bỏ qua nếu bạn mới bắt đầu.
        </span>
        {selectedIds.length > 0 && (
          <span className="ml-2 font-semibold text-primary-600">
            ({selectedIds.length} topic · {selectedIds.length * 5} câu hỏi)
          </span>
        )}
      </p>

      {modules.length === 0 && (
        <div className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Không có topics nào để hiển thị.
        </div>
      )}

      {modules.map((module, moduleIdx) => {
        const palette = MODULE_PALETTES[moduleIdx % MODULE_PALETTES.length];

        return (
          <div key={module.id}>
            {/* Module header */}
            <div className="mb-3 flex items-center gap-2">
              <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", palette.dot)} />
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {module.name}
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                · {module.topics.length} topics
              </span>
            </div>

            {/* Topic grid */}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {module.topics.map((topic) => {
                const isSelected = selectedSet.has(topic.id);
                return (
                  <button
                    key={topic.id}
                    type="button"
                    onClick={() => onToggle(topic.id)}
                    className={cn(
                      "relative flex flex-col gap-2 rounded-xl border-2 p-3 text-left",
                      "transition-all duration-150 hover:shadow-sm active:scale-[0.97]",
                      isSelected
                        ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                        : "hover:border-slate-300 dark:hover:border-slate-600"
                    )}
                    style={{
                      borderColor: isSelected ? undefined : "var(--border)",
                      backgroundColor: isSelected ? undefined : "var(--bg-card)",
                    }}
                  >
                    {/* Check badge */}
                    {isSelected && (
                      <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary-600">
                        <Check className="h-3 w-3 text-white" />
                      </span>
                    )}

                    {/* Module color dot */}
                    <span className={cn("h-2 w-2 shrink-0 rounded-full", palette.dot)} />

                    {/* Topic title */}
                    <span
                      className={cn(
                        "pr-4 text-xs font-medium leading-snug",
                        isSelected ? "text-primary-700 dark:text-primary-300" : ""
                      )}
                      style={{ color: isSelected ? undefined : "var(--text-primary)" }}
                    >
                      {topic.name}
                    </span>

                    {/* Estimated time */}
                    <span
                      className="flex items-center gap-1 text-xs"
                      style={{ color: "var(--text-muted)" }}
                    >
                      <Clock className="h-3 w-3" />
                      {topic.estimated_hours_beginner != null
                        ? `${Math.round(topic.estimated_hours_beginner * 60)} phút`
                        : "—"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
