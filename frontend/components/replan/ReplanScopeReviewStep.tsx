"use client";

import { useEffect, useMemo, useState } from "react";

type DifficultyFilter = "easy" | "easy_medium" | "easy_medium_hard" | "all";
type QuestionCountBreakdown = ReplanReviewUnit["questionCounts"];

export interface ReplanReviewUnit {
  canonicalUnitId: string;
  title: string;
  source: "matched_from_description" | "suggested_prerequisite";
  suggestedForTitle?: string;
  knowledgePoints: string[];
  questionCounts: {
    easy: number;
    medium: number;
    hard: number;
    application: number;
  };
}

export type ReplanSelectedAssessmentUnit = ReplanReviewUnit & {
  difficultyFilter: DifficultyFilter;
  selectedQuestionCount: number;
};

interface Props {
  units: ReplanReviewUnit[];
  onStartAssessment: (selectedUnits: ReplanSelectedAssessmentUnit[]) => void;
  onDescribeAgain: () => void;
}

const FILTER_LABELS: Record<DifficultyFilter, string> = {
  easy: "Easy only",
  easy_medium: "Easy + Medium",
  easy_medium_hard: "Easy + Medium + Hard",
  all: "All",
};

function sourceLabel(unit: ReplanReviewUnit): string {
  if (unit.source === "suggested_prerequisite") {
    return `Suggested prerequisite for ${unit.suggestedForTitle ?? "selected unit"}`;
  }
  return "Matched from your description";
}

function countForFilter(unit: ReplanReviewUnit, filter: DifficultyFilter): number {
  const counts = countsForFilter(unit, filter);
  return counts.easy + counts.medium + counts.hard + counts.application;
}

function countsForFilter(unit: ReplanReviewUnit, filter: DifficultyFilter): QuestionCountBreakdown {
  const counts = unit.questionCounts;
  return {
    easy: counts.easy,
    medium: filter === "easy" ? 0 : counts.medium,
    hard: filter === "easy" || filter === "easy_medium" ? 0 : counts.hard,
    application: filter === "all" ? counts.application : 0,
  };
}

export default function ReplanScopeReviewStep({
  units,
  onStartAssessment,
  onDescribeAgain,
}: Props) {
  const [selectedUnitIds, setSelectedUnitIds] = useState(() => new Set(units.map((unit) => unit.canonicalUnitId)));
  const [filters, setFilters] = useState<Record<string, DifficultyFilter>>(() =>
    units.reduce<Record<string, DifficultyFilter>>((acc, unit) => {
      acc[unit.canonicalUnitId] = "all";
      return acc;
    }, {}),
  );

  useEffect(() => {
    setSelectedUnitIds(new Set(units.map((unit) => unit.canonicalUnitId)));
    setFilters(
      units.reduce<Record<string, DifficultyFilter>>((acc, unit) => {
        acc[unit.canonicalUnitId] = "all";
        return acc;
      }, {}),
    );
  }, [units]);

  const selectedQuestions = useMemo(
    () =>
      units.reduce((total, unit) => {
        if (!selectedUnitIds.has(unit.canonicalUnitId)) return total;
        return total + countForFilter(unit, filters[unit.canonicalUnitId] ?? "all");
      }, 0),
    [filters, selectedUnitIds, units],
  );
  const selectedQuestionBreakdown = useMemo(
    () =>
      units.reduce<QuestionCountBreakdown>(
        (total, unit) => {
          if (!selectedUnitIds.has(unit.canonicalUnitId)) return total;
          const counts = countsForFilter(unit, filters[unit.canonicalUnitId] ?? "all");
          return {
            easy: total.easy + counts.easy,
            medium: total.medium + counts.medium,
            hard: total.hard + counts.hard,
            application: total.application + counts.application,
          };
        },
        { easy: 0, medium: 0, hard: 0, application: 0 },
      ),
    [filters, selectedUnitIds, units],
  );
  const selectedUnits = useMemo(
    () =>
      units
        .filter((unit) => selectedUnitIds.has(unit.canonicalUnitId))
        .map((unit) => {
          const difficultyFilter = filters[unit.canonicalUnitId] ?? "all";
          return {
            ...unit,
            difficultyFilter,
            selectedQuestionCount: countForFilter(unit, difficultyFilter),
          };
        }),
    [filters, selectedUnitIds, units],
  );
  const estimatedMinutes = Math.ceil((selectedQuestions * 10) / 60);

  function toggleUnit(unitId: string) {
    setSelectedUnitIds((current) => {
      const next = new Set(current);
      if (next.has(unitId)) next.delete(unitId);
      else next.add(unitId);
      return next;
    });
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Review verification scope
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          All matched eligible units are selected. Untick units you do not want to test, or narrow each unit by difficulty.
        </p>
      </div>

      <div className="space-y-3">
        {units.map((unit) => {
          const selected = selectedUnitIds.has(unit.canonicalUnitId);
          const filter = filters[unit.canonicalUnitId] ?? "all";
          return (
            <section
              key={unit.canonicalUnitId}
              className="rounded-xl border-2 p-4"
              style={{ borderColor: selected ? "rgb(37 99 235)" : "var(--border)", backgroundColor: "var(--bg-card)" }}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <label className="flex min-w-0 items-start gap-3">
                  <input
                    type="checkbox"
                    aria-label={`Include ${unit.title}`}
                    checked={selected}
                    onChange={() => toggleUnit(unit.canonicalUnitId)}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-primary-600"
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      {unit.title}
                    </span>
                    <span className="mt-1 block text-xs font-medium text-primary-600">
                      Source: {sourceLabel(unit)}
                    </span>
                  </span>
                </label>

                <select
                  aria-label={`Difficulty filter for ${unit.title}`}
                  value={filter}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      [unit.canonicalUnitId]: event.target.value as DifficultyFilter,
                    }))
                  }
                  className="rounded-lg border bg-white px-3 py-2 text-xs font-medium"
                  style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
                >
                  {Object.entries(FILTER_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mt-4 rounded-lg border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-page)" }}>
                <p className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                  Knowledge Points:
                </p>
                <ul className="ml-4 mt-2 list-disc space-y-1 text-xs" style={{ color: "var(--text-muted)" }}>
                  {unit.knowledgePoints.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </div>

              <p className="mt-3 text-xs font-medium text-primary-600">
                Easy {unit.questionCounts.easy} · Medium {unit.questionCounts.medium} · Hard {unit.questionCounts.hard} · Application {unit.questionCounts.application}
              </p>
            </section>
          );
        })}
      </div>

      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-page)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Total selected questions: {selectedQuestions}
        </p>
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--text-muted)" }}>
            Selected question breakdown
          </p>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ["Easy", selectedQuestionBreakdown.easy, "bg-emerald-50 text-emerald-700 border-emerald-100"],
              ["Medium", selectedQuestionBreakdown.medium, "bg-sky-50 text-sky-700 border-sky-100"],
              ["Hard", selectedQuestionBreakdown.hard, "bg-amber-50 text-amber-700 border-amber-100"],
              ["Application", selectedQuestionBreakdown.application, "bg-violet-50 text-violet-700 border-violet-100"],
            ].map(([label, count, className]) => (
              <span
                key={label}
                className={`rounded-lg border px-3 py-2 text-xs font-semibold ${className}`}
              >
                {label} {count}
              </span>
            ))}
          </div>
        </div>
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
          Estimated time: ~{estimatedMinutes} minutes
        </p>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={onDescribeAgain}
          className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          Describe again
        </button>
        <button
          type="button"
          onClick={() => onStartAssessment(selectedUnits)}
          className="ml-auto rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Start assessment
        </button>
      </div>
    </div>
  );
}
