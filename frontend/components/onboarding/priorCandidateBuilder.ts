import type { CourseSectionDetail, LearningUnitSelectionItem } from "@/types";

export type PlannerGoalId = "computer_vision" | "nlp";
export type PriorTopicVisibility = "confirm" | "context" | "hidden";
export type PriorTopicLevel = "not_started" | "reviewed" | "confident";

export interface PriorCandidateTopic {
  id: string;
  courseId: string;
  rawTitle: string;
  displayLabel: string;
  aiDisplayLabel?: string | null;
  suggestedLevel?: PriorTopicLevel | null;
  visibility: PriorTopicVisibility;
  summary?: string | null;
  foundationEligible?: boolean;
  units: LearningUnitSelectionItem[];
}

export interface PriorCandidateTopics {
  confirmEligible: PriorCandidateTopic[];
  contextOnly: PriorCandidateTopic[];
  hidden: PriorCandidateTopic[];
}

export interface PriorAnalysisTopicMetadata {
  id: string;
  label?: string | null;
  summary?: string | null;
  level?: PriorTopicLevel | null;
}

interface CuratedTopicCopy {
  pattern: RegExp;
  label: string;
  summary: string;
  foundationEligible?: boolean;
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

const CURATED_TOPIC_COPY: CuratedTopicCopy[] = [
  {
    pattern: /supervised,\s*self-supervised,\s*and weakly supervised learning/i,
    label: "Supervised, self-supervised, and weakly supervised learning",
    summary:
      "Learn how labels, pseudo-labels, supervision strength, and weak supervision shape common neural network training setups.",
    foundationEligible: true,
  },
  {
    pattern: /full cycle of a deep learning project/i,
    label: "Full cycle of a deep learning project",
    summary:
      "Learn how to move from data splits and metrics to bias-variance diagnosis, error analysis, and model iteration.",
    foundationEligible: true,
  },
  {
    pattern: /adversarial robustness and generative models/i,
    label: "Adversarial robustness and generative modeling",
    summary:
      "Learn how models can fail under adversarial inputs and how generative models create new data-like samples.",
  },
  {
    pattern: /deep reinforcement learning/i,
    label: "Deep reinforcement learning and agents",
    summary:
      "Learn the basics of agents, rewards, policies, and value-based learning for decision-making systems.",
  },
  {
    pattern: /ai project strategy/i,
    label: "AI project strategy and error analysis",
    summary:
      "Learn practical ways to prioritize data, metrics, model changes, and error buckets during an AI project.",
  },
  {
    pattern: /beyond the model|enhancing llm applications/i,
    label: "LLM application patterns",
    summary:
      "Learn how retrieval, tools, prompting, and evaluation improve real-world LLM applications beyond the base model.",
  },
  {
    pattern: /what is going on inside my model|inside my model/i,
    label: "Model interpretability for computer vision",
    summary:
      "Learn how to inspect what CNNs and vision transformers focus on using saliency, activation maps, and related visualization tools.",
  },
  {
    pattern: /image classification with linear classifiers/i,
    label: "Image classification with simple linear models",
    summary:
      "Learn how k-NN, linear classifiers, SVM, and softmax build the foundation for image classification.",
    foundationEligible: true,
  },
  {
    pattern: /regularization and optimization/i,
    label: "Regularization and training optimization",
    summary:
      "Learn how regularization, optimization choices, and validation behavior affect neural network training.",
    foundationEligible: true,
  },
  {
    pattern: /neural networks and backpropagation|backpropagation,\s*neural network/i,
    label: "Neural networks and backpropagation",
    summary:
      "Learn how fully connected neural networks compute predictions and use backpropagation to update weights.",
    foundationEligible: true,
  },
  {
    pattern: /image classification with cnns/i,
    label: "CNN-based image classification",
    summary:
      "Learn how convolution, pooling, normalization, and local receptive fields make CNNs effective for image classification.",
  },
  {
    pattern: /cnn architectures|convolutional nets|convolutional neural/i,
    label: "CNN architecture design",
    summary:
      "Learn how architectures such as AlexNet, VGG, ResNet, and transfer learning improve CNN performance.",
  },
  {
    pattern: /recurrent neural networks/i,
    label: "Recurrent neural networks for sequence data",
    summary:
      "Learn how recurrent models process ordered inputs and why sequence modeling matters for language and vision tasks.",
  },
  {
    pattern: /attention and transformers|self-attention and transformers/i,
    label: "Attention and transformer models",
    summary:
      "Learn how attention lets models focus on relevant tokens or patches and why transformers became the default architecture.",
  },
  {
    pattern: /object detection|image segmentation|visualizing and understanding/i,
    label: "Object detection and image segmentation",
    summary:
      "Learn how models localize objects, segment pixels, and connect classification features to detection and segmentation tasks.",
  },
  {
    pattern: /video understanding/i,
    label: "Video understanding",
    summary:
      "Learn how vision models handle motion, temporal context, and actions across frames instead of single images.",
  },
  {
    pattern: /self-supervised learning/i,
    label: "Self-supervised visual representation learning",
    summary:
      "Learn how contrastive and pretext tasks help vision models learn useful features without manual labels.",
  },
  {
    pattern: /generative models/i,
    label: "Generative vision models",
    summary:
      "Learn how generative models such as VAEs, GANs, and diffusion-style methods create or transform images.",
  },
  {
    pattern: /vision and language/i,
    label: "Vision-language models",
    summary:
      "Learn how image encoders and language models connect visual content with captions, retrieval, and multimodal reasoning.",
  },
  {
    pattern: /intro and word vectors|word vectors and language models|word vectors/i,
    label: "Word vectors and language modeling",
    summary:
      "Learn how words become vectors and how language models use context to predict and represent text.",
    foundationEligible: true,
  },
  {
    pattern: /dependency parsing/i,
    label: "Dependency parsing",
    summary:
      "Learn how NLP systems represent grammatical relationships between words and use parsing for sentence structure.",
  },
  {
    pattern: /sequence to sequence/i,
    label: "Sequence-to-sequence models",
    summary:
      "Learn how encoder-decoder models transform one sequence into another for tasks like translation and summarization.",
  },
  {
    pattern: /pretraining/i,
    label: "Pretraining and foundation models",
    summary:
      "Learn why large models are pretrained on broad data before being adapted to downstream tasks.",
  },
  {
    pattern: /post-training/i,
    label: "Post-training and alignment",
    summary:
      "Learn how instruction tuning, preference optimization, and alignment steps adapt pretrained models for users.",
  },
  {
    pattern: /natural language generation/i,
    label: "Natural language generation",
    summary:
      "Learn how language models generate fluent text and how decoding choices affect output quality and behavior.",
  },
  {
    pattern: /reasoning and agents|agents/i,
    label: "LLM reasoning and agents",
    summary:
      "Learn how LLMs plan, use tools, follow multi-step reasoning patterns, and act as agentic systems.",
  },
  {
    pattern: /python tutorial/i,
    label: "Python coding basics",
    summary:
      "Review Python syntax and basic programming patterns used throughout AI coursework.",
  },
  {
    pattern: /pytorch tutorial/i,
    label: "PyTorch coding basics",
    summary:
      "Review tensors, modules, training loops, and the core PyTorch workflow for neural networks.",
  },
  {
    pattern: /hugging ?face tutorial/i,
    label: "Hugging Face tooling",
    summary:
      "Review the Hugging Face workflow for loading models, tokenizers, datasets, and common NLP pipelines.",
  },
];

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

function curatedCopyForSectionTitle(
  title: string,
): { label: string; summary: string; foundationEligible: boolean } | null {
  const normalizedTitle = stripLecturePrefix(title);
  const copy = CURATED_TOPIC_COPY.find(
    (item) => item.pattern.test(title) || item.pattern.test(normalizedTitle),
  );
  return copy
    ? {
        label: copy.label,
        summary: copy.summary,
        foundationEligible: copy.foundationEligible === true,
      }
    : null;
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
  if (/what is going on inside my model|inside my model|interpretability/i.test(title)) {
    return "Model interpretability";
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
  const curatedCopy = curatedCopyForSectionTitle(section.title);
  return {
    id: section.id,
    courseId: normalizeCourseId(section.canonical_course_id),
    rawTitle: section.title,
    displayLabel: curatedCopy?.label ?? displayLabelForSectionTitle(section.title),
    visibility,
    summary: curatedCopy?.summary ?? null,
    foundationEligible: curatedCopy?.foundationEligible ?? false,
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

function inferAiExperienceMonths(text: string): number {
  const normalized = text.toLowerCase();
  let maxMonths = 0;

  for (const match of normalized.matchAll(/(\d+(?:[.,]\d+)?)\s*(months?|tháng|mo)\b/g)) {
    const value = Number.parseFloat(match[1].replace(",", "."));
    if (Number.isFinite(value)) {
      maxMonths = Math.max(maxMonths, value);
    }
  }

  for (const match of normalized.matchAll(/(\d+(?:[.,]\d+)?)\s*(years?|năm|yr)\b/g)) {
    const value = Number.parseFloat(match[1].replace(",", "."));
    if (Number.isFinite(value)) {
      maxMonths = Math.max(maxMonths, value * 12);
    }
  }

  return maxMonths;
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
  const aiExperienceMonths = inferAiExperienceMonths(combinedText);
  const matched = combinedText
    ? topics
        .map((topic) => {
          if (textMatchesTopic(combinedText, topic)) {
            return { ...topic, suggestedLevel: "confident" as const };
          }

          if (aiExperienceMonths >= 3 && topic.foundationEligible === true) {
            return { ...topic, suggestedLevel: "reviewed" as const };
          }

          return null;
        })
        .filter((topic): topic is PriorCandidateTopic => topic !== null)
    : [];

  return matched.slice(0, limit);
}

export function selectRepresentativeUnitIds(
  topic: PriorCandidateTopic,
  level: PriorTopicLevel,
): string[] {
  if (level === "not_started") return [];

  const limit = level === "confident" ? 4 : 2;
  return topic.units.slice(0, limit).map((unit) => unit.id);
}

export function selectSuggestedKnownUnitIds(topics: PriorCandidateTopic[]): string[] {
  const selected = new Set<string>();
  for (const topic of topics) {
    if (!topic.suggestedLevel || topic.suggestedLevel === "not_started") {
      continue;
    }
    for (const unitId of selectRepresentativeUnitIds(topic, topic.suggestedLevel)) {
      selected.add(unitId);
    }
  }
  return [...selected];
}

export function mergePriorAnalysisIntoCandidates(
  topics: PriorCandidateTopic[],
  metadata: PriorAnalysisTopicMetadata[],
  shortlistedTopicIds: string[] = [],
  fallbackTopics: PriorCandidateTopic[] = [],
): PriorCandidateTopic[] {
  const metadataById = new Map(metadata.map((item) => [item.id, item]));
  const shortlistedSet = new Set(shortlistedTopicIds);
  const fallbackLevelById = new Map(
    fallbackTopics.map((topic) => [topic.id, topic.suggestedLevel ?? "confident" as const]),
  );

  return topics.map((topic) => {
    const item = metadataById.get(topic.id);
    const fallbackLevel = fallbackLevelById.get(topic.id);
    if (!item) {
      return shortlistedSet.has(topic.id) || fallbackLevel
        ? {
            ...topic,
            suggestedLevel: fallbackLevel ?? "confident",
          }
        : topic;
    }

    return {
      ...topic,
      aiDisplayLabel: item.label ?? topic.aiDisplayLabel ?? null,
      suggestedLevel:
        item.level ?? fallbackLevel ?? (shortlistedSet.has(topic.id) ? "confident" : null),
      summary: item.summary?.trim() ? item.summary : topic.summary ?? null,
    };
  });
}
