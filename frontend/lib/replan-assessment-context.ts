import { writePendingCanonicalAssessment } from "@/lib/canonical-assessment-session";

export type ReplanAssessmentUnit = {
  canonicalUnitId: string;
  title: string;
};

export type ReplanAssessmentContext = {
  units: ReplanAssessmentUnit[];
};

export function writeReplanAssessmentContext(context: ReplanAssessmentContext): void {
  writePendingCanonicalAssessment({
    canonicalUnitIds: context.units.map((unit) => unit.canonicalUnitId),
    unitNameMap: Object.fromEntries(context.units.map((unit) => [unit.canonicalUnitId, unit.title])),
    assessmentDepth: "deep",
  });
}

export function buildReplanAssessmentHref(nextPath = "/learn"): string {
  return `/assessment?next=${encodeURIComponent(nextPath)}`;
}
