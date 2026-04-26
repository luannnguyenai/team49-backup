/**
 * tests/fixtures/coursePlatform.ts
 *
 * Shared fixture data for frontend course-platform tests.
 * Import these fixtures to avoid duplicating test data across test files.
 */

import type {
  CourseCatalogItem,
  LearningUnitResponse,
  CourseOverviewResponse,
} from "@/types";

// ---------------------------------------------------------------------------
// Catalog Items
// ---------------------------------------------------------------------------

export const CS231N_ITEM: CourseCatalogItem = {
  id: "course_cs231n",
  slug: "cs231n",
  title: "CS231n: Deep Learning for Computer Vision",
  short_description: "Deep learning foundations for computer vision.",
  status: "ready",
  cover_image_url: "/courses/cs231n/cover.jpg",
  hero_badge: "Available now",
  is_recommended: false,
};

export const CS224N_ITEM: CourseCatalogItem = {
  id: "course_cs224n",
  slug: "cs224n",
  title: "CS224n: Natural Language Processing with Deep Learning",
  short_description: "Modern NLP systems and language modeling.",
  status: "coming_soon",
  cover_image_url: "/courses/cs224n/cover.jpg",
  hero_badge: "Coming soon",
  is_recommended: false,
};

export const CS231N_RECOMMENDED: CourseCatalogItem = {
  ...CS231N_ITEM,
  is_recommended: true,
};

// ---------------------------------------------------------------------------
// Course Overview
// ---------------------------------------------------------------------------

export const CS231N_OVERVIEW: CourseOverviewResponse = {
  course: CS231N_ITEM,
  overview: {
    headline: "Build deep intuition for modern vision systems",
    subheadline: "Learn the path from linear classifiers to transformers.",
    summary_markdown: "Course summary...",
    learning_outcomes: [
      "Understand the core architecture families used in computer vision",
    ],
    target_audience: "Learners with Python basics",
    prerequisites_summary: "Comfort with Python",
    estimated_duration_text: "18 lectures",
    structure_snapshot: { summary: "Lecture-first course" },
    cta_label: "Start learning",
  },
  entry: {
    decision: "redirect",
    target: "/courses/cs231n/start",
    reason: "learning_ready",
  },
};

export const CS224N_OVERVIEW: CourseOverviewResponse = {
  course: CS224N_ITEM,
  overview: {
    headline: "Explore modern NLP and language modeling workflows",
    subheadline: "Visible but blocked until metadata is ready.",
    summary_markdown: "Overview placeholder.",
    learning_outcomes: [
      "See the upcoming NLP curriculum in the public catalog",
    ],
    target_audience: "Learners interested in NLP",
    prerequisites_summary: "Basic Python",
    estimated_duration_text: "Coming soon",
    structure_snapshot: { summary: "Overview only for now" },
    cta_label: "Coming soon",
  },
  entry: {
    decision: "redirect",
    target: "/courses/cs224n",
    reason: "course_unavailable",
  },
};

// ---------------------------------------------------------------------------
// Learning Units
// ---------------------------------------------------------------------------

export const LECTURE_1_UNIT: LearningUnitResponse = {
  course: {
    slug: "cs231n",
    title: "CS231n: Deep Learning for Computer Vision",
  },
  unit: {
    id: "unit_lecture_01",
    slug: "lecture-1-introduction",
    title: "Lecture 1: Introduction",
    unit_type: "lecture",
    status: "ready",
    entry_mode: "video",
  },
  content: {
    body_markdown: null,
    video_url: "/data/courses/CS231n/videos/lecture-1.mp4",
    transcript_available: true,
    slides_available: true,
  },
  tutor: {
    enabled: true,
    mode: "in_context",
    context_binding_id: "ctx_unit_lecture_01",
    legacy_lecture_id: "cs231n-lecture-1",
  },
};

export const DISABLED_TUTOR_UNIT: LearningUnitResponse = {
  course: {
    slug: "cs231n",
    title: "CS231n: Deep Learning for Computer Vision",
  },
  unit: {
    id: "unit_lecture_99",
    slug: "lecture-99-placeholder",
    title: "Lecture 99: Placeholder",
    unit_type: "lecture",
    status: "ready",
    entry_mode: "video",
  },
  content: {
    body_markdown: "Some markdown content",
    video_url: null,
    transcript_available: false,
    slides_available: false,
  },
  tutor: {
    enabled: false,
    mode: "disabled",
    context_binding_id: null,
    legacy_lecture_id: null,
  },
};
