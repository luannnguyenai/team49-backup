import type {
  CourseCatalogItem,
  CourseCatalogResponse,
  CourseOverviewResponse,
  StartLearningDecisionResponse,
} from "@/types";

const MOCK_HERO_BADGE = "Coming soon";

export const MOCK_COURSES: CourseCatalogItem[] = [
  {
    id: "mock_course_rag_prod",
    slug: "rag-production-systems",
    title: "RAG Production Systems",
    short_description:
      "Design retrieval, indexing, chunking, and guardrail pipelines to bring RAG into real products.",
    status: "coming_soon",
    cover_image_url: null,
    hero_kicker: "LLM systems",
    hero_badge: MOCK_HERO_BADGE,
    is_recommended: false,
    progress_percent: null,
  },
  {
    id: "mock_course_agent_eval",
    slug: "agent-evaluation-playbook",
    title: "Agent Evaluation Playbook",
    short_description:
      "Build agent evaluation criteria, test by task, and track regressions when prompts or tools change.",
    status: "coming_soon",
    cover_image_url: null,
    hero_kicker: "Evaluation",
    hero_badge: MOCK_HERO_BADGE,
    is_recommended: false,
    progress_percent: null,
  },
  {
    id: "mock_course_mlops_foundations",
    slug: "mlops-foundations",
    title: "MLOps Foundations",
    short_description:
      "From experiment tracking and model packaging to deployment and monitoring for machine learning systems.",
    status: "coming_soon",
    cover_image_url: null,
    hero_kicker: "Operations",
    hero_badge: MOCK_HERO_BADGE,
    is_recommended: false,
    progress_percent: null,
  },
  {
    id: "mock_course_multimodal",
    slug: "multimodal-ai-studio",
    title: "Multimodal AI Studio",
    short_description:
      "Combine text, image, and audio to build multimodal AI experiences that can be demoed and scaled.",
    status: "coming_soon",
    cover_image_url: null,
    hero_kicker: "Multimodal",
    hero_badge: MOCK_HERO_BADGE,
    is_recommended: false,
    progress_percent: null,
  },
  {
    id: "mock_course_ai_pm",
    slug: "ai-product-strategy",
    title: "AI Product Strategy",
    short_description:
      "Turn AI use cases into a product roadmap, choose success metrics, and avoid demos that create no value.",
    status: "coming_soon",
    cover_image_url: null,
    hero_kicker: "Product",
    hero_badge: MOCK_HERO_BADGE,
    is_recommended: false,
    progress_percent: null,
  },
];

const MOCK_START_DECISION: StartLearningDecisionResponse = {
  decision: "course_unavailable",
  target: "",
  reason: "course_unavailable",
};

function buildMockOverview(course: CourseCatalogItem): CourseOverviewResponse {
  return {
    course,
    overview: {
      headline: `${course.title} is coming soon`,
      subheadline:
        "This course is currently marked as coming soon. You can preview its direction before the learning content officially opens.",
      summary_markdown: [
        `**${course.title}** has been added to the catalog so learners can preview upcoming learning directions.`,
        course.short_description,
        "When the course officially launches, this page will be replaced with the full overview and learning path.",
      ].join("\n\n"),
      learning_outcomes: [
        "Understand the scope and main goals of the course before starting.",
        "See which topics will open in the next release wave.",
        "Keep the catalog experience continuous as the number of courses grows.",
      ],
      target_audience:
        "Learners who want to track upcoming courses and plan their study path.",
      prerequisites_summary:
        "None yet. Detailed metadata will be added when the course opens.",
      estimated_duration_text: "Coming soon",
      structure_snapshot: {
        summary:
          "A temporary overview page for an upcoming course. Detailed learning content and units will be added later.",
      },
      cta_label: "Coming soon",
    },
    entry: MOCK_START_DECISION,
  };
}

const MOCK_OVERVIEW_BY_SLUG = new Map(
  MOCK_COURSES.map((course) => [course.slug, buildMockOverview(course)]),
);

export function mergeMockCourses(response: CourseCatalogResponse): CourseCatalogResponse {
  const existingSlugs = new Set(response.items.map((item) => item.slug));
  const mergedItems = [
    ...response.items,
    ...MOCK_COURSES.filter((course) => !existingSlugs.has(course.slug)),
  ];

  return {
    ...response,
    items: mergedItems,
  };
}

export function findMockCourseOverview(courseSlug: string): CourseOverviewResponse | null {
  return MOCK_OVERVIEW_BY_SLUG.get(courseSlug) ?? null;
}

export function isMockCourseSlug(courseSlug: string): boolean {
  return MOCK_OVERVIEW_BY_SLUG.has(courseSlug);
}

export function getMockCourseStartDecision(courseSlug: string): StartLearningDecisionResponse | null {
  return isMockCourseSlug(courseSlug) ? MOCK_START_DECISION : null;
}
