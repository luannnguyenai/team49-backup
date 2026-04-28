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
      "Thiết kế pipeline retrieval, indexing, chunking và guardrail để đưa RAG vào sản phẩm thật.",
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
      "Xây bộ tiêu chí đánh giá agent, kiểm thử theo task, và theo dõi regression khi prompt hoặc tool thay đổi.",
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
      "Từ experiment tracking, model packaging đến deployment và monitoring cho mô hình học máy.",
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
      "Kết hợp text, image và audio để xây trải nghiệm AI đa phương thức có thể demo và mở rộng.",
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
      "Biến use case AI thành roadmap sản phẩm, chọn chỉ số thành công và tránh xây demo không ra giá trị.",
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
      headline: `${course.title} sẽ mở sớm`,
      subheadline:
        "Khóa học đang ở trạng thái coming soon. Bạn có thể xem định hướng nội dung trước khi phần học chính thức mở.",
      summary_markdown: [
        `**${course.title}** được thêm vào catalog để người học thấy trước các hướng học tiếp theo.`,
        course.short_description,
        "Khi khóa học mở chính thức, trang này sẽ được thay bằng overview và lộ trình học đầy đủ.",
      ].join("\n\n"),
      learning_outcomes: [
        "Hiểu phạm vi và mục tiêu chính của khóa học trước khi bắt đầu.",
        "Biết chủ đề nào sẽ được mở trong đợt phát hành tiếp theo.",
        "Giữ được tính liên tục của catalog khi số lượng khóa học tăng lên.",
      ],
      target_audience:
        "Người học muốn theo dõi các khóa học sắp mở để lên kế hoạch học tập.",
      prerequisites_summary:
        "Chưa yêu cầu. Metadata chi tiết sẽ được cập nhật khi khóa học mở.",
      estimated_duration_text: "Coming soon",
      structure_snapshot: {
        summary:
          "Trang overview tạm thời cho course sắp ra mắt. Nội dung học và unit chi tiết sẽ được bổ sung sau.",
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
