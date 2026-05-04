import { writePendingCanonicalAssessment } from "@/lib/canonical-assessment-session";

const REPLAN_ASSESSMENT_SCOPE_KEY = "al_replan_assessment_scope";

export type ReplanAssessmentUnit = {
  canonicalUnitId: string;
  title: string;
  difficultyFilter: "easy" | "easy_medium" | "easy_medium_hard" | "all";
  selectedQuestionCount: number;
};

export type ReplanAssessmentContext = {
  units: ReplanAssessmentUnit[];
};

export type ReplanAssessmentScope = {
  selectedUnits: ReplanAssessmentUnit[];
  questionTotal: number;
  estimatedSeconds: number;
  scope: "current_path_only";
};

export function writeReplanAssessmentContext(context: ReplanAssessmentContext): void {
  writePendingCanonicalAssessment({
    canonicalUnitIds: context.units.map((unit) => unit.canonicalUnitId),
    unitNameMap: Object.fromEntries(context.units.map((unit) => [unit.canonicalUnitId, unit.title])),
    assessmentDepth: "deep",
  });
  if (typeof window === "undefined") return;

  const questionTotal = context.units.reduce((total, unit) => total + unit.selectedQuestionCount, 0);
  window.sessionStorage.setItem(
    REPLAN_ASSESSMENT_SCOPE_KEY,
    JSON.stringify({
      selectedUnits: context.units,
      questionTotal,
      estimatedSeconds: questionTotal * 10,
      scope: "current_path_only",
    } satisfies ReplanAssessmentScope),
  );
}

export function readReplanAssessmentScope(): ReplanAssessmentScope | null {
  if (typeof window === "undefined") return null;

  const raw = window.sessionStorage.getItem(REPLAN_ASSESSMENT_SCOPE_KEY);
  return raw ? JSON.parse(raw) as ReplanAssessmentScope : null;
}

export function buildReplanAssessmentHref(nextPath = "/learn"): string {
  return `/assessment?next=${encodeURIComponent(nextPath)}`;
}
