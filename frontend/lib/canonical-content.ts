import type {
  CanonicalAssessmentStartPayload,
  CourseCatalogItem,
  CourseSectionSummary,
  LearningUnitQuizRef,
  LearningUnitResponse,
  ModuleListItem,
  TopicContent,
} from "@/types";

export function mapCourseCatalogItemToModuleListItem(
  course: CourseCatalogItem,
): ModuleListItem {
  return {
    id: course.slug,
    name: course.title,
    description: course.short_description,
    order_index: 0,
    prerequisite_module_ids: null,
    topics_count: 0,
  };
}

export function mapLearningUnitToTopicContent(
  unit: LearningUnitResponse,
  section: CourseSectionSummary,
): TopicContent {
  return {
    topic_id: unit.unit.id,
    topic_name: unit.unit.title,
    module_id: section.id,
    module_name: section.title,
    content_markdown: unit.content.body_markdown,
    video_url: unit.content.video_url,
  };
}

export function mapLearningUnitToQuizRef(
  unit: LearningUnitResponse,
): LearningUnitQuizRef {
  return {
    learning_unit_id: unit.unit.id,
    canonical_unit_id: unit.unit.id,
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
