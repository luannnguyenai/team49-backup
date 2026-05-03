import type {
  AssessmentStartResponse,
  CanonicalAssessmentStartPayload,
  AnswerInput,
  CourseSectionDetail,
  QuestionForAssessment,
  SelectedAnswer,
} from "@/types";

export const ASSESSMENT_STORAGE_KEYS = {
  canonicalUnitIds: "al_pending_canonical_unit_ids",
  unitNames: "al_pending_canonical_unit_names",
  assessmentDepth: "al_pending_assessment_depth",
  startedAssessment: "al_started_assessment",
} as const;

interface BuildCanonicalAssessmentContextInput {
  sections: CourseSectionDetail[];
  knownUnitIds: string[];
  desiredSectionIds: string[];
  selectedCourseIds?: string[];
}

export interface CanonicalAssessmentContext {
  canonicalUnitIds: string[];
  unitNameMap: Record<string, string>;
  assessmentDepth?: CanonicalAssessmentStartPayload["assessment_depth"];
}

export interface StartedCanonicalAssessmentContext {
  sessionId: string;
  questions: AssessmentStartResponse["questions"];
  canonicalUnitIds: string[];
  unitNameMap: Record<string, string>;
}

function unique<T>(values: T[]): T[] {
  return Array.from(new Set(values));
}

export function buildCanonicalAssessmentContext({
  sections,
  knownUnitIds,
  desiredSectionIds,
  selectedCourseIds = [],
}: BuildCanonicalAssessmentContextInput): CanonicalAssessmentContext {
  const selectedUnitSet = new Set(knownUnitIds);
  const selectedSectionSet = new Set(desiredSectionIds);
  const selectedCourseSet = new Set(
    selectedCourseIds.map((courseId) => courseId.toLowerCase()),
  );
  const unitRows =
    selectedUnitSet.size > 0
      ? sections.flatMap((section) =>
          section.learning_units.filter((unit) => selectedUnitSet.has(unit.id)),
        )
      : selectedSectionSet.size > 0
        ? sections.flatMap((section) =>
            selectedSectionSet.has(section.id) ? section.learning_units : [],
          )
        : sections.flatMap((section) => {
            const courseIds = [
              section.course_id,
              section.canonical_course_id ?? "",
            ].map((courseId) => courseId.toLowerCase());
            return courseIds.some((courseId) => selectedCourseSet.has(courseId))
              ? section.learning_units
              : [];
          });

  const canonicalUnitIds = unique(
    unitRows
      .map((unit) => unit.canonical_unit_id ?? null)
      .filter((value): value is string => Boolean(value)),
  );

  const unitNameMap = unitRows.reduce<Record<string, string>>((acc, unit) => {
    if (unit.canonical_unit_id) {
      acc[unit.canonical_unit_id] = unit.title;
    }
    return acc;
  }, {});

  return {
    canonicalUnitIds,
    unitNameMap,
  };
}

export function getAssessmentQuestionKey(question: QuestionForAssessment): string {
  return question.canonical_item_id ?? question.id ?? question.item_id;
}

export function buildAssessmentAnswerInput(
  question: QuestionForAssessment,
  selectedAnswer: SelectedAnswer,
  responseTimeMs: number | null,
): AnswerInput {
  if (question.canonical_item_id) {
    return {
      canonical_item_id: question.canonical_item_id,
      selected_answer: selectedAnswer,
      response_time_ms: responseTimeMs,
    };
  }

  return {
    question_id: question.id,
    selected_answer: selectedAnswer,
    response_time_ms: responseTimeMs,
  };
}

export function readPendingCanonicalAssessment(): CanonicalAssessmentContext {
  if (typeof window === "undefined") {
    return { canonicalUnitIds: [], unitNameMap: {} };
  }

  const canonicalIdsRaw = window.sessionStorage.getItem(
    ASSESSMENT_STORAGE_KEYS.canonicalUnitIds,
  );
  const unitNamesRaw = window.sessionStorage.getItem(
    ASSESSMENT_STORAGE_KEYS.unitNames,
  );

  return {
    canonicalUnitIds: canonicalIdsRaw ? JSON.parse(canonicalIdsRaw) as string[] : [],
    unitNameMap: unitNamesRaw
      ? JSON.parse(unitNamesRaw) as Record<string, string>
      : {},
    assessmentDepth:
      window.sessionStorage.getItem(ASSESSMENT_STORAGE_KEYS.assessmentDepth) as
        | CanonicalAssessmentStartPayload["assessment_depth"]
        | null
        ?? undefined,
  };
}

export function readStartedCanonicalAssessment(): StartedCanonicalAssessmentContext | null {
  if (typeof window === "undefined") return null;

  const raw = window.sessionStorage.getItem(ASSESSMENT_STORAGE_KEYS.startedAssessment);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as StartedCanonicalAssessmentContext;
    if (!parsed.sessionId || !Array.isArray(parsed.questions)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writePendingCanonicalAssessment(
  context: CanonicalAssessmentContext,
): void {
  if (typeof window === "undefined") return;

  window.sessionStorage.setItem(
    ASSESSMENT_STORAGE_KEYS.canonicalUnitIds,
    JSON.stringify(context.canonicalUnitIds),
  );
  window.sessionStorage.setItem(
    ASSESSMENT_STORAGE_KEYS.unitNames,
    JSON.stringify(context.unitNameMap),
  );
  if (context.assessmentDepth) {
    window.sessionStorage.setItem(
      ASSESSMENT_STORAGE_KEYS.assessmentDepth,
      context.assessmentDepth,
    );
  }
}

export function writeStartedCanonicalAssessment(
  context: StartedCanonicalAssessmentContext,
): void {
  if (typeof window === "undefined") return;

  window.sessionStorage.setItem(
    ASSESSMENT_STORAGE_KEYS.startedAssessment,
    JSON.stringify(context),
  );
}

export function clearPendingAssessmentContext(): void {
  if (typeof window === "undefined") return;

  Object.values(ASSESSMENT_STORAGE_KEYS).forEach((key) => {
    window.sessionStorage.removeItem(key);
  });
}
