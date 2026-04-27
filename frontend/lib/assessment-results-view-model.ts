import type {
  AssessmentResultResponse,
  LearningUnitResult,
  TopicDecisionResult,
} from "@/types";

export interface AssessmentPriorityItem {
  id: string;
  title: string;
  decision: string;
  scorePercent: number;
  masteryLevel: LearningUnitResult["mastery_level"] | string;
  questionsCorrect?: number;
  questionsTotal?: number;
}

export interface AssessmentResultViewModel {
  counts: {
    relearn: number;
    review: number;
    skip: number;
    mastered: number;
    total: number;
  };
  priorityItems: AssessmentPriorityItem[];
  masteredPreview: AssessmentPriorityItem[];
  detailRows: AssessmentPriorityItem[];
  misconceptions: Array<{ learningUnit: string; id: string }>;
}

const DECISION_RANK: Record<string, number> = {
  relearn: 0,
  review: 1,
  skip: 2,
};

function unitById(result: AssessmentResultResponse): Map<string, LearningUnitResult> {
  return new Map(result.learning_unit_results.map((unit) => [unit.learning_unit_id, unit]));
}

function fromDecision(
  decision: TopicDecisionResult,
  units: Map<string, LearningUnitResult>,
): AssessmentPriorityItem {
  const unit = units.get(decision.topic_unit_id);
  return {
    id: decision.topic_unit_id,
    title: decision.topic_unit_name,
    decision: decision.decision,
    scorePercent: decision.score_pct,
    masteryLevel: unit?.mastery_level ?? decision.mastery_level,
    questionsCorrect: decision.questions_correct,
    questionsTotal: decision.questions_total,
  };
}

function fromUnit(unit: LearningUnitResult): AssessmentPriorityItem {
  const decision =
    unit.mastery_level === "novice"
      ? "relearn"
      : unit.mastery_level === "developing"
        ? "review"
        : "skip";

  return {
    id: unit.learning_unit_id,
    title: unit.learning_unit_title,
    decision,
    scorePercent: unit.score_percent,
    masteryLevel: unit.mastery_level,
  };
}

export function buildAssessmentResultViewModel(
  result: AssessmentResultResponse,
): AssessmentResultViewModel {
  const units = unitById(result);
  const detailRows = (result.topic_decisions?.length
    ? result.topic_decisions.map((decision) => fromDecision(decision, units))
    : result.learning_unit_results.map(fromUnit)
  ).sort((a, b) => {
    const rankDiff = (DECISION_RANK[a.decision] ?? 9) - (DECISION_RANK[b.decision] ?? 9);
    if (rankDiff !== 0) return rankDiff;
    return a.scorePercent - b.scorePercent;
  });

  const relearnCount = detailRows.filter((item) => item.decision === "relearn").length;
  const reviewCount = detailRows.filter((item) => item.decision === "review").length;
  const skipCount = detailRows.filter((item) => item.decision === "skip").length;
  const masteredCount = result.learning_unit_results.filter((unit) => unit.mastery_level === "mastered").length;
  const priorityItems = detailRows.filter((item) => item.decision !== "skip").slice(0, 5);
  const masteredPreview = detailRows.filter((item) => item.decision === "skip").slice(0, 6);
  const misconceptions = result.learning_unit_results.flatMap((unit) =>
    unit.misconceptions_detected.map((id) => ({
      learningUnit: unit.learning_unit_title,
      id,
    })),
  );

  return {
    counts: {
      relearn: relearnCount,
      review: reviewCount,
      skip: skipCount,
      mastered: masteredCount,
      total: detailRows.length,
    },
    priorityItems,
    masteredPreview,
    detailRows,
    misconceptions,
  };
}
