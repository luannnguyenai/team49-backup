"use client";
// components/onboarding/StepDesiredModules.tsx
// Step 2 — "Bạn muốn học gì?"
// Large selectable cards, one per module.

import { BookOpen, Check, Clock, Code2, Database, Layers } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleDetail } from "@/types";

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
  modules: ModuleDetail[];
  selectedIds: string[];
  onToggle: (id: string) => void;
  error?: string;
}

export default function StepDesiredModules({
  modules,
  selectedIds,
  onToggle,
  error,
}: Props) {
  const selectedSet = new Set(selectedIds);

  return (
    <div className="space-y-3">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Chọn 1 hoặc nhiều modules bạn muốn học trong khoá này.
        {selectedIds.length > 0 && (
          <span className="ml-2 font-semibold text-primary-600">
            ({selectedIds.length} đã chọn)
          </span>
        )}
      </p>

      {modules.length === 0 && (
        <div className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Không có modules nào để hiển thị.
        </div>
      )}

      {modules.map((module, idx) => {
        const isSelected = selectedSet.has(module.id);
        const { gradient, Icon } = MODULE_CONFIGS[idx % MODULE_CONFIGS.length];

        // Compute estimated hours from topics
        const totalHours = module.topics
          .reduce((sum, t) => sum + (t.estimated_hours_beginner ?? 0), 0)
          .toFixed(1);

        return (
          <button
            key={module.id}
            type="button"
            onClick={() => onToggle(module.id)}
            className={cn(
              "w-full rounded-xl border-2 p-4 text-left",
              "transition-all duration-150 hover:shadow-md active:scale-[0.99]",
              isSelected
                ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                : "hover:border-slate-300 dark:hover:border-slate-600"
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
                    {module.name}
                  </h3>
                  {isSelected && (
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-600">
                      <Check className="h-3.5 w-3.5 text-white" />
                    </span>
                  )}
                </div>

                {module.description && (
                  <p
                    className="mt-0.5 line-clamp-2 text-sm"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {module.description}
                  </p>
                )}

                {/* Meta badges */}
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <span
                    className="flex items-center gap-1 text-xs"
                    style={{ color: "var(--text-muted)" }}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    {module.topics_count} topics
                  </span>
                  <span
                    className="flex items-center gap-1 text-xs"
                    style={{ color: "var(--text-muted)" }}
                  >
                    <Clock className="h-3.5 w-3.5" />
                    ~{totalHours} giờ
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
