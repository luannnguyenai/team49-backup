import { describe, expect, it } from "vitest";

import {
  buildCanonicalAssessmentStartPayload,
  mapCourseCatalogItemToModuleListItem,
  mapLearningUnitToQuizRef,
  mapLearningUnitToTopicContent,
} from "@/lib/canonical-content";
import { CS231N_ITEM, LECTURE_1_UNIT } from "@/tests/fixtures/coursePlatform";
import type { CourseSectionSummary } from "@/types";

describe("canonical content mappers", () => {
  const section: CourseSectionSummary = {
    id: "section_convnets",
    course_id: CS231N_ITEM.id,
    course_slug: CS231N_ITEM.slug,
    course_title: CS231N_ITEM.title,
    title: "Convolutional Networks",
    description: "Vision course section",
    order_index: 2,
    topics_count: 5,
  };

  it("maps a course catalog item into a module-like card for legacy UI slots", () => {
    expect(mapCourseCatalogItemToModuleListItem(CS231N_ITEM)).toEqual({
      id: CS231N_ITEM.slug,
      name: CS231N_ITEM.title,
      description: CS231N_ITEM.short_description,
      order_index: 0,
      prerequisite_module_ids: null,
      topics_count: 0,
    });
  });

  it("maps a learning unit into a legacy topic content shape", () => {
    expect(mapLearningUnitToTopicContent(LECTURE_1_UNIT, section)).toEqual({
      topic_id: LECTURE_1_UNIT.unit.id,
      topic_name: LECTURE_1_UNIT.unit.title,
      module_id: section.id,
      module_name: section.title,
      content_markdown: LECTURE_1_UNIT.content.body_markdown,
      video_url: LECTURE_1_UNIT.content.video_url,
    });
  });

  it("builds a canonical quiz reference from a learning unit", () => {
    expect(mapLearningUnitToQuizRef(LECTURE_1_UNIT)).toEqual({
      learning_unit_id: LECTURE_1_UNIT.unit.id,
      canonical_unit_id: LECTURE_1_UNIT.unit.id,
      course_slug: LECTURE_1_UNIT.course.slug,
      unit_slug: LECTURE_1_UNIT.unit.slug,
      title: LECTURE_1_UNIT.unit.title,
    });
  });

  it("builds the canonical assessment start payload", () => {
    expect(
      buildCanonicalAssessmentStartPayload([
        LECTURE_1_UNIT.unit.id,
        "unit_lecture_02",
      ]),
    ).toEqual({
      canonical_unit_ids: [LECTURE_1_UNIT.unit.id, "unit_lecture_02"],
    });
  });
});
