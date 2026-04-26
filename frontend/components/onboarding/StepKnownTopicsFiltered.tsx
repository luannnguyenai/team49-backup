"use client";
// components/onboarding/StepKnownTopicsFiltered.tsx
// Step 2 — Known topics, filtered by the goals selected in Step 1.
// Reuses the same card UI as StepKnownUnits, but only shows units from
// courses that match the user's selected goals.

import { useEffect, useState } from "react";
import { Check, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { canonicalSectionApi } from "@/lib/api";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { CourseSectionDetail } from "@/types";

// ---------------------------------------------------------------------------
// Goal → canonical course ID mapping (must match backend GOAL_COURSE_MAP)
// ---------------------------------------------------------------------------

const GOAL_COURSE_MAP: Record<string, string | undefined> = {
  computer_vision: "cs231n",
  nlp: "cs224n",
};

// ---------------------------------------------------------------------------
// Section color palettes (same as StepKnownUnits)
// ---------------------------------------------------------------------------

const SECTION_PALETTES = [
  { dot: "bg-blue-500", ring: "ring-blue-200 dark:ring-blue-800" },
  { dot: "bg-purple-500", ring: "ring-purple-200 dark:ring-purple-800" },
  { dot: "bg-emerald-500", ring: "ring-emerald-200 dark:ring-emerald-800" },
  { dot: "bg-orange-500", ring: "ring-orange-200 dark:ring-orange-800" },
  { dot: "bg-rose-500", ring: "ring-rose-200 dark:ring-rose-800" },
] as const;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  onNext: () => void;
  onBack: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function StepKnownTopicsFiltered({ onNext, onBack }: Props) {
  const goalIds = useOnboardingStore((s) => s.goalIds);
  const knownUnitIds = useOnboardingStore((s) => s.knownUnitIds);
  const setKnownUnitIds = useOnboardingStore((s) => s.setKnownUnitIds);

  const [allSections, setAllSections] = useState<CourseSectionDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Load all sections on mount ─────────────────────────────────────────
  useEffect(() => {
    async function loadData() {
      try {
        const list = await canonicalSectionApi.list();
        const details = await Promise.all(
          list.map((section) => canonicalSectionApi.detail(section.id)),
        );
        setAllSections(details);
      } catch {
        setError("Không thể tải dữ liệu. Vui lòng thử lại.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // ── Filter sections by selected goals ─────────────────────────────────
  // Derive the set of course IDs that match the selected goals.
  const targetCourseIds =
    goalIds.length > 0
      ? new Set(goalIds.map((g) => GOAL_COURSE_MAP[g]).filter(Boolean))
      : null; // null → show all (graceful fallback when no goals selected)

  const visibleSections =
    targetCourseIds === null
      ? allSections
      : allSections.filter(
          (s) => s.canonical_course_id && targetCourseIds.has(s.canonical_course_id),
        );

  // ── Toggle a unit ─────────────────────────────────────────────────────
  const selectedSet = new Set(knownUnitIds);

  function toggle(unitId: string) {
    if (selectedSet.has(unitId)) {
      setKnownUnitIds(knownUnitIds.filter((id) => id !== unitId));
    } else {
      setKnownUnitIds([...knownUnitIds, unitId]);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
        Đang tải...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Chọn những units bạn đã nắm — hệ thống sẽ đánh giá kiến thức của bạn với{" "}
        <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
          5 câu hỏi mỗi unit
        </span>
        .{" "}
        <span className="font-medium" style={{ color: "var(--text-primary)" }}>
          Bỏ qua nếu bạn mới bắt đầu.
        </span>
        {knownUnitIds.length > 0 && (
          <span className="ml-2 font-semibold text-primary-600">
            ({knownUnitIds.length} unit · {knownUnitIds.length * 5} câu hỏi)
          </span>
        )}
      </p>

      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      {visibleSections.length === 0 && !error && (
        <div className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Không có units nào để hiển thị.
        </div>
      )}

      {visibleSections.map((section, sectionIdx) => {
        const palette = SECTION_PALETTES[sectionIdx % SECTION_PALETTES.length];

        return (
          <div key={section.id}>
            <div className="mb-3 flex items-center gap-2">
              <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", palette.dot)} />
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {section.title}
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                · {section.learning_units.length} units
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {section.learning_units.map((unit) => {
                const isSelected = selectedSet.has(unit.id);

                return (
                  <button
                    key={unit.id}
                    type="button"
                    onClick={() => toggle(unit.id)}
                    className={cn(
                      "relative flex flex-col gap-2 rounded-xl border-2 p-3 text-left",
                      "transition-all duration-150 hover:shadow-sm active:scale-[0.97]",
                      isSelected
                        ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                        : "hover:border-slate-300 dark:hover:border-slate-600",
                    )}
                    style={{
                      borderColor: isSelected ? undefined : "var(--border)",
                      backgroundColor: isSelected ? undefined : "var(--bg-card)",
                    }}
                  >
                    {isSelected && (
                      <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary-600">
                        <Check className="h-3 w-3 text-white" />
                      </span>
                    )}

                    <span className={cn("h-2 w-2 shrink-0 rounded-full", palette.dot)} />

                    <span
                      className={cn(
                        "pr-4 text-xs font-medium leading-snug",
                        isSelected ? "text-primary-700 dark:text-primary-300" : "",
                      )}
                      style={{ color: isSelected ? undefined : "var(--text-primary)" }}
                    >
                      {unit.title}
                    </span>

                    <span
                      className="flex items-center gap-1 text-xs"
                      style={{ color: "var(--text-muted)" }}
                    >
                      <Clock className="h-3 w-3" />
                      {unit.estimated_hours_beginner != null
                        ? `${Math.round(unit.estimated_hours_beginner * 60)} phút`
                        : "—"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Navigation */}
      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onBack}
          className="flex-1 rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          Quay lại
        </button>
        <button
          type="button"
          onClick={onNext}
          className="flex-1 rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Tiếp tục
        </button>
      </div>
    </div>
  );
}
