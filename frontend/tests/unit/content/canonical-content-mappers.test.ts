import { describe, expect, it } from "vitest";

import {
  buildCanonicalAssessmentStartPayload,
  mapCourseCatalogItemToSectionCard,
  mapLearningUnitToContentById,
  mapLearningUnitToQuizRef,
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

  it("maps a course catalog item into a canonical section-style card", () => {
    expect(mapCourseCatalogItemToSectionCard(CS231N_ITEM)).toEqual({
      id: CS231N_ITEM.slug,
      title: CS231N_ITEM.title,
      description: CS231N_ITEM.short_description,
      order_index: 0,
      prerequisite_section_ids: null,
      learning_units_count: 0,
    });
  });

  it("maps a learning unit into content-by-id shape", () => {
    expect(mapLearningUnitToContentById(LECTURE_1_UNIT, section)).toEqual({
      learning_unit_id: LECTURE_1_UNIT.unit.id,
      title: LECTURE_1_UNIT.unit.title,
      section_id: section.id,
      section_title: section.title,
      content_markdown: LECTURE_1_UNIT.content.body_markdown,
      video_url: LECTURE_1_UNIT.content.video_url,
    });
  });

  it("builds a canonical quiz reference from a learning unit", () => {
    expect(mapLearningUnitToQuizRef(LECTURE_1_UNIT)).toEqual({
      learning_unit_id: LECTURE_1_UNIT.unit.id,
      canonical_artifact_unit_id: null,
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
