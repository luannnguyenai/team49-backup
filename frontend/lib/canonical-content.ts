import type {
  CanonicalAssessmentStartPayload,
  CourseCatalogItem,
  CourseSectionListItem,
  CourseSectionSummary,
  LearningUnitContentById,
  LearningUnitQuizRef,
  LearningUnitResponse,
} from "@/types";

export function mapCourseCatalogItemToSectionCard(
  course: CourseCatalogItem,
): CourseSectionListItem {
  return {
    id: course.slug,
    course_id: course.id,
    canonical_course_id: null,
    title: course.title,
    description: course.short_description,
    order_index: 0,
    prerequisite_section_ids: null,
    learning_units_count: 0,
  };
}

export function mapLearningUnitToContentById(
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
