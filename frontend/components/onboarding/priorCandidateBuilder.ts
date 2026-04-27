import type { CourseSectionDetail, LearningUnitSelectionItem } from "@/types";

export type PlannerGoalId = "computer_vision" | "nlp";
export type PriorTopicVisibility = "confirm" | "context" | "hidden";
export type PriorTopicLevel = "not_started" | "reviewed" | "confident";

export interface PriorCandidateTopic {
  id: string;
  courseId: string;
  rawTitle: string;
  displayLabel: string;
  visibility: PriorTopicVisibility;
  units: LearningUnitSelectionItem[];
}

export interface PriorCandidateTopics {
  confirmEligible: PriorCandidateTopic[];
  contextOnly: PriorCandidateTopic[];
  hidden: PriorCandidateTopic[];
}

const GOAL_COURSE_IDS: Record<PlannerGoalId, string[]> = {
  computer_vision: ["cs230", "cs231n"],
  nlp: ["cs230", "cs224n"],
};

const SHARED_HIDDEN_TITLE_PATTERN =
  /career advice|human[- ]centered|course introduction|historical|history|motivation|administrivia|recap/i;

const INTRO_TITLE_PATTERN =
  /(^|\b)(lecture|lec\.?)\s*1\s*[:-]\s*(intro|introduction)\b|^intro\b|^introduction\b/i;

const NLP_HIDDEN_TITLE_PATTERN =
  /brain[- ]computer|linguistics|philosophy|interpretability|model editing|benchmarking|efficient training|after dpo/i;

const CV_HIDDEN_TITLE_PATTERN = /3d vision|robot learning|distributed training/i;

const NLP_CONTEXT_TITLE_PATTERN = /python tutorial|pytorch tutorial|hugging ?face tutorial|coding/i;

function normalizeCourseId(courseId: string | null | undefined): string {
  return courseId?.trim().toLowerCase() ?? "";
}

function stripLecturePrefix(title: string): string {
  return title
    .replace(/^lecture\s*\d+\s*[:-]\s*/i, "")
    .replace(/\s+by\s+.+$/i, "")
    .replace(/,\s+[A-Z][A-Za-z .'-]+$/g, "")
    .trim();
}

export function displayLabelForSectionTitle(title: string): string {
  if (/cnn architectures|convolutional nets|convolutional neural/i.test(title)) {
    return "CNN architectures";
  }
  if (/reasoning and agents|agents/i.test(title)) {
    return "LLM reasoning and agents";
  }
  if (/pytorch tutorial/i.test(title)) {
    return "PyTorch coding basics";
  }
  if (/python tutorial/i.test(title)) {
    return "Python coding basics";
  }
  if (/hugging ?face/i.test(title)) {
    return "HuggingFace tooling";
  }
  if (/word vectors/i.test(title)) {
    return "Word vectors and embeddings";
  }
  if (/language model/i.test(title)) {
    return "Language modeling";
  }
  if (/attention|transformer/i.test(title)) {
    return "Attention and transformers";
  }
  if (/detection|segmentation/i.test(title)) {
    return "Object detection and segmentation";
  }
  if (/generative|diffusion/i.test(title)) {
    return "Generative vision models";
  }
  if (/backprop|neural networks/i.test(title)) {
    return "Neural networks and backpropagation";
  }

  return stripLecturePrefix(title);
}

function classifyVisibility(goalId: PlannerGoalId, title: string): PriorTopicVisibility {
  if (SHARED_HIDDEN_TITLE_PATTERN.test(title) || INTRO_TITLE_PATTERN.test(title)) {
    return "hidden";
  }

  if (goalId === "computer_vision" && CV_HIDDEN_TITLE_PATTERN.test(title)) {
    return "hidden";
  }

  if (goalId === "nlp") {
    if (NLP_HIDDEN_TITLE_PATTERN.test(title)) {
      return "hidden";
    }
    if (NLP_CONTEXT_TITLE_PATTERN.test(title)) {
      return "context";
    }
  }

  return "confirm";
}

function toCandidateTopic(goalId: PlannerGoalId, section: CourseSectionDetail): PriorCandidateTopic {
  const visibility = classifyVisibility(goalId, section.title);
  return {
    id: section.id,
    courseId: normalizeCourseId(section.canonical_course_id),
    rawTitle: section.title,
    displayLabel: displayLabelForSectionTitle(section.title),
    visibility,
    units: [...section.learning_units].sort(
      (a, b) => (a.order_index ?? 0) - (b.order_index ?? 0),
    ),
  };
}

export function buildPriorCandidateTopics({
  goalId,
  sections,
}: {
  goalId: PlannerGoalId;
  sections: CourseSectionDetail[];
}): PriorCandidateTopics {
  const selectedCourseIds = new Set(GOAL_COURSE_IDS[goalId]);
  const topics = sections
    .filter((section) => selectedCourseIds.has(normalizeCourseId(section.canonical_course_id)))
    .filter((section) => section.learning_units.length > 0)
    .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0))
    .map((section) => toCandidateTopic(goalId, section));

  return {
    confirmEligible: topics.filter((topic) => topic.visibility === "confirm"),
    contextOnly: topics.filter((topic) => topic.visibility === "context"),
    hidden: topics.filter((topic) => topic.visibility === "hidden"),
  };
}

function textMatchesTopic(text: string, topic: PriorCandidateTopic): boolean {
  const normalized = text.toLowerCase();
  const haystack = `${topic.rawTitle} ${topic.displayLabel} ${topic.units
    .map((unit) => unit.title)
    .join(" ")}`.toLowerCase();

  return normalized
    .split(/[^a-z0-9+#.]+/i)
    .filter((token) => token.length >= 3)
    .some((token) => haystack.includes(token));
}

export function buildPriorShortlistFallback({
  topics,
  priorKnowledgeText,
  codingExperienceText,
  limit = 8,
}: {
  topics: PriorCandidateTopic[];
  priorKnowledgeText: string;
  codingExperienceText: string;
  limit?: number;
}): PriorCandidateTopic[] {
  const combinedText = `${priorKnowledgeText} ${codingExperienceText}`.trim();
  const matched = combinedText
    ? topics.filter((topic) => textMatchesTopic(combinedText, topic))
    : [];
  const fallback = topics.filter((topic) => !matched.some((item) => item.id === topic.id));

  return [...matched, ...fallback].slice(0, limit);
}

export function selectRepresentativeUnitIds(
  topic: PriorCandidateTopic,
  level: PriorTopicLevel,
): string[] {
  if (level === "not_started") return [];

  const limit = level === "confident" ? 4 : 2;
  return topic.units.slice(0, limit).map((unit) => unit.id);
}
