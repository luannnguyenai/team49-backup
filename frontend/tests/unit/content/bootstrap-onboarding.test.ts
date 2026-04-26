import { describe, expect, it } from "vitest";

import {
  buildBootstrapTopicGroups,
  courseSlugToCanonicalCourseId,
  estimateSelectedCourseHours,
  normalizeBootstrapCourses,
  normalizeBootstrapTopics,
} from "@/lib/bootstrap-onboarding";
import type { BootstrapCourse, BootstrapTopic } from "@/types";

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
});
