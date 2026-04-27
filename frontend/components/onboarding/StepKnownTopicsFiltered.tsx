"use client";
// components/onboarding/StepKnownTopicsFiltered.tsx
// Step 3 (experienced flow) — Known topics grouped by goal in accordions.

import { useEffect, useState } from "react";
import { Check, ChevronDown, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { canonicalSectionApi } from "@/lib/api";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { CourseSectionDetail, LearningUnitSelectionItem } from "@/types";

// ---------------------------------------------------------------------------
// Goal → canonical course ID mapping (must match backend GOAL_COURSE_MAP)
// ---------------------------------------------------------------------------

const GOAL_COURSE_MAP: Record<string, string[] | undefined> = {
  computer_vision: ["cs230", "cs231n"],
  nlp: ["cs230", "cs224n"],
};

const GOAL_DISPLAY_NAMES: Record<string, string> = {
  computer_vision: "Computer Vision",
  nlp: "Natural Language Processing",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  onNext: () => void;
  onBack: () => void;
  onSkipAll: () => void;
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

  // Default: open if exactly 1 goal selected, closed if ≥2
  const [openGoals, setOpenGoals] = useState<Set<string>>(
    () => new Set(goalIds.length === 1 ? [goalIds[0]] : [])
  );

  // ── Load sections on mount ─────────────────────────────────────────────
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

  // ── Build per-goal unit lists ──────────────────────────────────────────
  const selectedSet = new Set(knownUnitIds);

  // For each goalId, collect units from sections belonging to that goal's course
  const goalUnits: Array<{ goalId: string; units: LearningUnitSelectionItem[] }> =
    goalIds.map((goalId) => {
      const courseIds = GOAL_COURSE_MAP[goalId];
      const sections = courseIds
        ? allSections.filter((s) => courseIds.includes(s.canonical_course_id))
        : [];
      const units = sections.flatMap((s) => s.learning_units);
      return { goalId, units };
    });

  // ── Toggle ─────────────────────────────────────────────────────────────
  function toggle(unitId: string) {
    if (selectedSet.has(unitId)) {
      setKnownUnitIds(knownUnitIds.filter((id) => id !== unitId));
    } else {
      setKnownUnitIds([...knownUnitIds, unitId]);
    }
  }

  function toggleGoal(goalId: string) {
    setOpenGoals((prev) => {
      const next = new Set(prev);
      if (next.has(goalId)) next.delete(goalId);
      else next.add(goalId);
      return next;
    });
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
      {/* Warning banner */}
      <div className="rounded-xl border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-800 dark:border-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300">
        Chỉ chọn topic bạn thật sự đã học rồi — bạn sẽ phải làm test ngắn để đánh giá năng lực.
      </div>

      {/* Description */}
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        Chọn những units bạn đã nắm — hệ thống sẽ đánh giá kiến thức của bạn với{" "}
        <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
          5 câu hỏi mỗi unit
        </span>
        .
        {knownUnitIds.length > 0 && (
          <span className="ml-2 font-semibold text-primary-600">
            ({knownUnitIds.length} unit · {knownUnitIds.length * 5} câu hỏi)
          </span>
        )}
      </p>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {/* Accordion per goal */}
      <div className="space-y-2">
        {goalUnits.map(({ goalId, units }) => {
          const isOpen = openGoals.has(goalId);
          const selectedCount = units.filter((u) => selectedSet.has(u.id)).length;
          const goalName = GOAL_DISPLAY_NAMES[goalId] ?? goalId;

          return (
            <div
              key={goalId}
              className="overflow-hidden rounded-xl border-2 transition-all duration-150"
              style={{ borderColor: "var(--border)" }}
            >
              {/* Accordion header */}
              <button
                type="button"
                onClick={() => toggleGoal(goalId)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                style={{ backgroundColor: "var(--bg-card)" }}
              >
                <span
                  className="flex-1 text-sm font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  {goalName}
                </span>

                {/* X/Y badge */}
                <span
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-xs font-semibold",
                    selectedCount > 0
                      ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300"
                      : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                  )}
                >
                  {selectedCount}/{units.length} đã chọn
                </span>

                {/* Chevron */}
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 transition-transform duration-200",
                    isOpen ? "rotate-180" : ""
                  )}
                  style={{ color: "var(--text-muted)" }}
                />
              </button>

              {/* Accordion body */}
              {isOpen && (
                <div
                  className="border-t p-4"
                  style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-page)" }}
                >
                  {units.length === 0 ? (
                    <p className="text-center text-xs" style={{ color: "var(--text-muted)" }}>
                      Không có units nào cho goal này.
                    </p>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {units.map((unit) => {
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
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Navigation */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={onBack}
          className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
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
          className="ml-auto rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Tiếp tục
        </button>
      </div>
    </div>
  );
}
