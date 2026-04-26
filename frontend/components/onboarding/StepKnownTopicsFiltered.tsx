"use client";
// components/onboarding/StepKnownTopicsFiltered.tsx
// Step 3 (experienced flow) — Known topics filtered by goals.
// Units are shown as a flat grid sorted by their original lecture order.
// Section headers are hidden; grouping logic replaced by the Experience Level step.

import { useEffect, useState } from "react";
import { Check, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { canonicalSectionApi } from "@/lib/api";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { CourseSectionDetail, LearningUnitSelectionItem } from "@/types";

// ---------------------------------------------------------------------------
// Goal → canonical course ID mapping (must match backend GOAL_COURSE_MAP)
// ---------------------------------------------------------------------------

const GOAL_COURSE_MAP: Record<string, string | undefined> = {
  computer_vision: "cs231n",
  nlp: "cs224n",
  deep_learning: "cs230",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  onNext: () => void;
  onBack: () => void;
  onSkipAll: () => void; // called by parent when user proceeds with 0 topics selected
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

  // ── Filter sections by selected goals ─────────────────────────────────
  const targetCourseIds =
    goalIds.length > 0
      ? new Set(goalIds.map((g) => GOAL_COURSE_MAP[g]).filter(Boolean))
      : null;

  const visibleSections =
    targetCourseIds === null
      ? allSections
      : allSections.filter(
          (s) => s.canonical_course_id && targetCourseIds.has(s.canonical_course_id),
        );

  // Flat list of units preserving section → unit sort order
  const flatUnits: LearningUnitSelectionItem[] = visibleSections.flatMap(
    (s) => s.learning_units,
  );

  // ── Toggle ─────────────────────────────────────────────────────────────
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

      {flatUnits.length === 0 && !error && (
        <div className="py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Không có units nào để hiển thị.
        </div>
      )}

      {/* Flat unit grid — no section headers */}
      {flatUnits.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {flatUnits.map((unit) => {
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

      {/* Navigation — no skip button; user can proceed with 0 selected */}
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
