import type {
  CanonicalAssessmentStartPayload,
  CourseSectionDetail,
  CourseSectionListItem,
  CourseCatalogItem,
  CourseSectionSummary,
  LearningUnitContentById,
  LearningUnitQuizRef,
  LearningUnitSelectionItem,
  LearningUnitResponse,
} from "@/types";

export interface LegacyTopicSummaryResponse {
  id: string;
  canonical_unit_id?: string | null;
  name: string;
  description: string | null;
  order_index: number;
  estimated_hours_beginner: number | null;
  estimated_hours_intermediate: number | null;
}

export interface LegacyModuleListItemResponse {
  id: string;
  name: string;
  description: string | null;
  order_index: number;
  prerequisite_module_ids: string[] | null;
  topics_count: number;
}

export interface LegacyModuleDetailResponse extends LegacyModuleListItemResponse {
  topics: LegacyTopicSummaryResponse[];
}

export interface LegacyTopicContentResponse {
  topic_id: string;
  topic_name: string;
  module_id: string;
  module_name: string;
  content_markdown: string | null;
  video_url: string | null;
}

function mapLegacyTopicSummaryToLearningUnitSelectionItem(
  topic: LegacyTopicSummaryResponse,
): LearningUnitSelectionItem {
  return {
    id: topic.id,
    canonical_unit_id: topic.canonical_unit_id ?? null,
    title: topic.name,
    description: topic.description,
    order_index: topic.order_index,
    estimated_hours_beginner: topic.estimated_hours_beginner,
    estimated_hours_intermediate: topic.estimated_hours_intermediate,
  };
}

export function mapCourseCatalogItemToSectionCard(
  course: CourseCatalogItem,
): CourseSectionListItem {
  return {
    id: course.slug,
    title: course.title,
    description: course.short_description,
    order_index: 0,
    prerequisite_section_ids: null,
    learning_units_count: 0,
  };
}

export function mapLegacySectionListItem(
  section: LegacyModuleListItemResponse,
): CourseSectionListItem {
  return {
    id: section.id,
    title: section.name,
    description: section.description,
    order_index: section.order_index,
    prerequisite_section_ids: section.prerequisite_module_ids,
    learning_units_count: section.topics_count,
  };
}

export function mapLegacySectionDetail(
  section: LegacyModuleDetailResponse,
): CourseSectionDetail {
  return {
    ...mapLegacySectionListItem(section),
    learning_units: section.topics.map(mapLegacyTopicSummaryToLearningUnitSelectionItem),
  };
}

export function mapLearningUnitToCompatContent(
  unit: LearningUnitResponse,
  section: CourseSectionSummary,
): LearningUnitContentById {
  return {
    learning_unit_id: unit.unit.id,
    title: unit.unit.title,
    section_id: section.id,
    section_title: section.title,
    content_markdown: unit.content.body_markdown,
    video_url: unit.content.video_url,
  };
}

export function mapLegacyTopicContent(
  content: LegacyTopicContentResponse,
): LearningUnitContentById {
  return {
    learning_unit_id: content.topic_id,
    title: content.topic_name,
    section_id: content.module_id,
    section_title: content.module_name,
    content_markdown: content.content_markdown,
    video_url: content.video_url,
  };
}

export function mapLearningUnitToQuizRef(
  unit: LearningUnitResponse,
): LearningUnitQuizRef {
  return {
    learning_unit_id: unit.unit.id,
    canonical_artifact_unit_id: null,
    course_slug: unit.course.slug,
    unit_slug: unit.unit.slug,
    title: unit.unit.title,
  };
}

export function buildCanonicalAssessmentStartPayload(
  canonicalUnitIds: string[],
): CanonicalAssessmentStartPayload {
  return {
    canonical_unit_ids: canonicalUnitIds,
  };
}
