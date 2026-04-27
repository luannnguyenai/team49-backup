import { describe, expect, it } from "vitest";

import {
  buildBootstrapTopicsFromCanonicalSections,
  buildBootstrapTopicGroups,
  courseSlugToCanonicalCourseId,
  estimateSelectedCourseHours,
  normalizeBootstrapCourses,
  normalizeBootstrapTopics,
} from "@/lib/bootstrap-onboarding";
import type { BootstrapCourse, BootstrapTopic, CourseSectionDetail } from "@/types";

const COURSES: BootstrapCourse[] = [
  {
    id: "course_cs231n",
    slug: "cs231n",
    title: "CS231n",
    short_description: "Computer vision",
    status: "ready",
    visibility: "public",
    cover_image_url: null,
    hero_badge: "Available now",
    primary_subject: "computer_vision",
    sort_order: 1,
  },
  {
    id: "course_cs224n",
    slug: "cs224n",
    title: "CS224n",
    short_description: "NLP",
    status: "ready",
    visibility: "public",
    cover_image_url: null,
    hero_badge: "Available now",
    primary_subject: "nlp",
    sort_order: 2,
  },
];

const TOPICS: BootstrapTopic[] = [
  {
    slug: "cv-intro",
    module_slug: "cs231n_cv",
    name: "CV Intro",
    description: "Intro topic",
    order_index: 1,
    estimated_hours_beginner: 2,
    estimated_hours_intermediate: 1,
    estimated_hours_review: 0.25,
  },
  {
    slug: "nlp-intro",
    module_slug: "cs224n_nlp",
    name: "NLP Intro",
    description: "Intro topic",
    order_index: 2,
    estimated_hours_beginner: 3,
    estimated_hours_intermediate: 1.5,
    estimated_hours_review: 0.25,
  },
];

const CANONICAL_SECTIONS: CourseSectionDetail[] = [
  {
    id: "section-1",
    course_id: "course-uuid-1",
    canonical_course_id: "CS231n",
    title: "Lecture 1",
    description: "Foundations",
    order_index: 1,
    prerequisite_section_ids: null,
    learning_units_count: 2,
    learning_units: [
      {
        id: "unit-1",
        canonical_unit_id: "local::lecture01::seg1",
        title: "Pixels and tensors",
        description: "Intro",
        order_index: 1,
        estimated_hours_beginner: 1.5,
        estimated_hours_intermediate: 0.75,
      },
      {
        id: "unit-2",
        canonical_unit_id: "local::lecture01::seg2",
        title: "Linear classifiers",
        description: null,
        order_index: 2,
        estimated_hours_beginner: 2,
        estimated_hours_intermediate: 1,
      },
    ],
  },
];

describe("bootstrap onboarding helpers", () => {
  it("maps course slugs into canonical course ids used by runtime onboarding", () => {
    expect(courseSlugToCanonicalCourseId("cs231n")).toBe("CS231n");
    expect(courseSlugToCanonicalCourseId("cs224n")).toBe("CS224n");
  });

  it("groups bootstrap topics under their matching bootstrap courses", () => {
    const courses = normalizeBootstrapCourses(COURSES);
    const topics = normalizeBootstrapTopics(TOPICS, courses);

    expect(buildBootstrapTopicGroups(topics, courses)).toEqual([
      {
        course_key: "CS231n",
        course_title: "CS231n",
        topics: [
          {
            ...TOPICS[0],
            course_slug: "cs231n",
            canonical_course_id: "CS231n",
          },
        ],
      },
      {
        course_key: "CS224n",
        course_title: "CS224n",
        topics: [
          {
            ...TOPICS[1],
            course_slug: "cs224n",
            canonical_course_id: "CS224n",
          },
        ],
      },
    ]);
  });

  it("estimates total study hours from selected bootstrap courses", () => {
    const courses = normalizeBootstrapCourses(COURSES);
    const topics = normalizeBootstrapTopics(TOPICS, courses);

    expect(estimateSelectedCourseHours(topics, ["CS231n"])).toBe(2);
    expect(estimateSelectedCourseHours(topics, ["CS231n", "CS224n"])).toBe(5);
  });

  it("derives onboarding topics from canonical course sections when bootstrap topics are unavailable", () => {
    const courses = normalizeBootstrapCourses(COURSES);

    expect(buildBootstrapTopicsFromCanonicalSections(CANONICAL_SECTIONS, courses)).toEqual([
      {
        slug: "local::lecture01::seg1",
        module_slug: "section-1",
        name: "Pixels and tensors",
        description: "Intro",
        order_index: 1001,
        estimated_hours_beginner: 1.5,
        estimated_hours_intermediate: 0.75,
        estimated_hours_review: null,
        course_slug: "cs231n",
        canonical_course_id: "CS231n",
      },
      {
        slug: "local::lecture01::seg2",
        module_slug: "section-1",
        name: "Linear classifiers",
        description: "",
        order_index: 1002,
        estimated_hours_beginner: 2,
        estimated_hours_intermediate: 1,
        estimated_hours_review: null,
        course_slug: "cs231n",
        canonical_course_id: "CS231n",
      },
    ]);
  });
});
