import { describe, expect, it } from "vitest";
import {
  buildPriorCandidateTopics,
  buildPriorShortlistFallback,
  mergePriorAnalysisIntoCandidates,
  selectRepresentativeUnitIds,
  selectSuggestedKnownUnitIds,
} from "@/components/onboarding/priorCandidateBuilder";
import type { CourseSectionDetail } from "@/types";

const sections = [
  {
    id: "dl-intro",
    course_id: "c-dl",
    canonical_course_id: "cs230",
    title: "Lecture 1: Introduction to Deep Learning",
    description: null,
    order_index: 1,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    learning_units: [
      {
        id: "intro-u",
        title: "What is deep learning",
        description: null,
        order_index: 0,
        estimated_hours_beginner: 1,
        estimated_hours_intermediate: 0.5,
      },
    ],
  },
  {
    id: "dl-career",
    course_id: "c-dl",
    canonical_course_id: "cs230",
    title: "Lecture 8: Career Advice in AI",
    description: null,
    order_index: 8,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    learning_units: [
      {
        id: "career-u",
        title: "Career advice",
        description: null,
        order_index: 0,
        estimated_hours_beginner: 1,
        estimated_hours_intermediate: 0.5,
      },
    ],
  },
  {
    id: "cv-cnn",
    course_id: "c-cv",
    canonical_course_id: "cs231n",
    title: "Lecture 6: CNN Architectures",
    description: null,
    order_index: 6,
    prerequisite_section_ids: null,
    learning_units_count: 3,
    learning_units: [
      { id: "cnn-1", title: "AlexNet", description: null, order_index: 0, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
      { id: "cnn-2", title: "VGG", description: null, order_index: 1, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
      { id: "cnn-3", title: "ResNet", description: null, order_index: 2, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
    ],
  },
  {
    id: "cv-human",
    course_id: "c-cv",
    canonical_course_id: "cs231n",
    title: "Lecture 18: Human-Centered AI",
    description: null,
    order_index: 18,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    learning_units: [
      { id: "human-u", title: "Responsible AI", description: null, order_index: 0, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
    ],
  },
  {
    id: "nlp-agents",
    course_id: "c-nlp",
    canonical_course_id: "cs224n",
    title: "Lecture 14 - Reasoning and Agents by Shikhar Murty",
    description: null,
    order_index: 14,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    learning_units: [
      { id: "agent-u", title: "Tool use", description: null, order_index: 0, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
    ],
  },
  {
    id: "nlp-pytorch",
    course_id: "c-nlp",
    canonical_course_id: "cs224n",
    title: "PyTorch Tutorial, Drew Kaul",
    description: null,
    order_index: 98,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    learning_units: [
      { id: "pytorch-u", title: "PyTorch tensors", description: null, order_index: 0, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
    ],
  },
  {
    id: "nlp-bci",
    course_id: "c-nlp",
    canonical_course_id: "cs224n",
    title: "Lecture 13 - Brain-Computer Interfaces, Chaofei Fan",
    description: null,
    order_index: 13,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    learning_units: [
      { id: "bci-u", title: "BCI", description: null, order_index: 0, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
    ],
  },
] satisfies CourseSectionDetail[];

describe("prior candidate builder", () => {
  it("keeps common CV topics but hides niche CV lectures", () => {
    const topics = buildPriorCandidateTopics({
      goalId: "computer_vision",
      sections,
    });

    expect(topics.confirmEligible.map((topic) => topic.displayLabel)).toContain("CNN architecture design");
    expect(topics.hidden.map((topic) => topic.rawTitle)).toContain("Lecture 1: Introduction to Deep Learning");
    expect(topics.hidden.map((topic) => topic.rawTitle)).toContain("Lecture 8: Career Advice in AI");
    expect(topics.hidden.map((topic) => topic.rawTitle)).toContain("Lecture 18: Human-Centered AI");
  });

  it("keeps NLP agents for LLM scoring and treats coding tutorials as context only", () => {
    const topics = buildPriorCandidateTopics({
      goalId: "nlp",
      sections,
    });

    expect(topics.confirmEligible.map((topic) => topic.displayLabel)).toContain("LLM reasoning and agents");
    expect(topics.contextOnly.map((topic) => topic.displayLabel)).toContain("PyTorch coding basics");
    expect(topics.hidden.map((topic) => topic.rawTitle)).toContain("Lecture 13 - Brain-Computer Interfaces, Chaofei Fan");
  });

  it("selects more representative units for confident topics than reviewed topics", () => {
    const topic = buildPriorCandidateTopics({
      goalId: "computer_vision",
      sections,
    }).confirmEligible.find((candidate) => candidate.id === "cv-cnn");

    expect(topic).toBeDefined();
    expect(selectRepresentativeUnitIds(topic!, "reviewed")).toEqual(["cnn-1", "cnn-2"]);
    expect(selectRepresentativeUnitIds(topic!, "confident")).toEqual(["cnn-1", "cnn-2", "cnn-3"]);
    expect(selectRepresentativeUnitIds(topic!, "not_started")).toEqual([]);
  });

  it("merges AI metadata into all candidates instead of dropping unmentioned topics", () => {
    const topics = buildPriorCandidateTopics({
      goalId: "computer_vision",
      sections,
    }).confirmEligible;

    const merged = mergePriorAnalysisIntoCandidates(topics, [
      {
        id: "cv-cnn",
        label: "CNN architecture design",
        summary: "Covers AlexNet, VGG, and ResNet.",
        level: "confident",
      },
    ]);

    expect(merged).toHaveLength(topics.length);
    expect(merged.find((topic) => topic.id === "cv-cnn")).toMatchObject({
      aiDisplayLabel: "CNN architecture design",
      summary: "Covers AlexNet, VGG, and ResNet.",
      suggestedLevel: "confident",
    });
  });

  it("uses curated web copy before AI analysis and keeps it when AI only returns level", () => {
    const topics = buildPriorCandidateTopics({
      goalId: "computer_vision",
      sections: [
        {
          id: "cv-interpretability",
          course_id: "c-cv",
          canonical_course_id: "cs231n",
          title: "Lecture 9: What Is Going On Inside My Model?",
          description: null,
          order_index: 9,
          prerequisite_section_ids: null,
          learning_units_count: 1,
          learning_units: [
            {
              id: "interp-u",
              title: "Class activation maps",
              description: null,
              order_index: 0,
              estimated_hours_beginner: 1,
              estimated_hours_intermediate: 0.5,
            },
          ],
        },
      ],
    }).confirmEligible;

    expect(topics[0]).toMatchObject({
      displayLabel: "Model interpretability for computer vision",
      summary: "Learn how to inspect what CNNs and vision transformers focus on using saliency, activation maps, and related visualization tools.",
    });

    const merged = mergePriorAnalysisIntoCandidates(topics, [
      { id: "cv-interpretability", level: "not_started" },
    ]);

    expect(merged[0]).toMatchObject({
      displayLabel: "Model interpretability for computer vision",
      summary: "Learn how to inspect what CNNs and vision transformers focus on using saliency, activation maps, and related visualization tools.",
      suggestedLevel: "not_started",
    });
  });

  it("uses shortlisted IDs as confident fallback when AI metadata is missing", () => {
    const topics = buildPriorCandidateTopics({
      goalId: "computer_vision",
      sections,
    }).confirmEligible;

    const merged = mergePriorAnalysisIntoCandidates(topics, [], ["cv-cnn"]);

    expect(merged.find((topic) => topic.id === "cv-cnn")).toMatchObject({
      displayLabel: "CNN architecture design",
      suggestedLevel: "confident",
    });
  });

  it("marks common foundation topics as reviewed from one year of AI experience", () => {
    const topics = buildPriorCandidateTopics({
      goalId: "computer_vision",
      sections: [
        {
          id: "project",
          course_id: "c-dl",
          canonical_course_id: "cs230",
          title: "Lecture 3: Full Cycle of a Deep Learning Project",
          description: null,
          order_index: 3,
          prerequisite_section_ids: null,
          learning_units_count: 3,
          learning_units: [
            { id: "project-1", title: "Train dev test split", description: null, order_index: 0, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
            { id: "project-2", title: "Bias variance diagnosis", description: null, order_index: 1, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
            { id: "project-3", title: "Error analysis", description: null, order_index: 2, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
          ],
        },
        {
          id: "detection",
          course_id: "c-cv",
          canonical_course_id: "cs231n",
          title: "Lecture 9: Object Detection, Image Segmentation, Visualizing and Understanding",
          description: null,
          order_index: 9,
          prerequisite_section_ids: null,
          learning_units_count: 2,
          learning_units: [
            { id: "det-1", title: "Object detection", description: null, order_index: 0, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
            { id: "det-2", title: "Segmentation", description: null, order_index: 1, estimated_hours_beginner: 1, estimated_hours_intermediate: 0.5 },
          ],
        },
      ],
    }).confirmEligible;

    const fallback = buildPriorShortlistFallback({
      topics,
      priorKnowledgeText: "I have studied AI for 1 year.",
      codingExperienceText: "",
    });
    const analyzed = mergePriorAnalysisIntoCandidates(topics, [], [], fallback);

    expect(analyzed.find((topic) => topic.id === "project")).toMatchObject({
      suggestedLevel: "reviewed",
    });
    expect(analyzed.find((topic) => topic.id === "detection")?.suggestedLevel).toBeUndefined();
    expect(selectSuggestedKnownUnitIds(analyzed)).toEqual(["project-1", "project-2"]);
  });
});
