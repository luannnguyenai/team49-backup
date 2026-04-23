import type {
  AnswerInput,
  ModuleDetail,
  QuestionForAssessment,
  SelectedAnswer,
} from "@/types";

export const ASSESSMENT_STORAGE_KEYS = {
  canonicalUnitIds: "al_pending_canonical_unit_ids",
  unitNames: "al_pending_canonical_unit_names",
  moduleIds: "al_pending_module_ids",
  topicIds: "al_pending_topic_ids",
  topicNames: "al_pending_topic_names",
} as const;

interface BuildCanonicalAssessmentContextInput {
  modules: ModuleDetail[];
  knownTopicIds: string[];
  desiredModuleIds: string[];
}

export interface CanonicalAssessmentContext {
  canonicalUnitIds: string[];
  unitNameMap: Record<string, string>;
}

function unique<T>(values: T[]): T[] {
  return Array.from(new Set(values));
}

export function buildCanonicalAssessmentContext({
  modules,
  knownTopicIds,
  desiredModuleIds,
}: BuildCanonicalAssessmentContextInput): CanonicalAssessmentContext {
  const selectedTopicSet = new Set(knownTopicIds);
  const selectedModuleSet = new Set(desiredModuleIds);
  const topicRows =
    selectedTopicSet.size > 0
      ? modules.flatMap((module) =>
          module.topics.filter((topic) => selectedTopicSet.has(topic.id)),
        )
      : modules.flatMap((module) =>
          selectedModuleSet.has(module.id) ? module.topics : [],
        );

  const canonicalUnitIds = unique(
    topicRows
      .map((topic) => topic.canonical_unit_id ?? null)
      .filter((value): value is string => Boolean(value)),
  );

  const unitNameMap = topicRows.reduce<Record<string, string>>((acc, topic) => {
    if (topic.canonical_unit_id) {
      acc[topic.canonical_unit_id] = topic.name;
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
  };
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
}

export function clearPendingAssessmentContext(): void {
  if (typeof window === "undefined") return;

  Object.values(ASSESSMENT_STORAGE_KEYS).forEach((key) => {
    window.sessionStorage.removeItem(key);
  });
}
