import { getCourseGateState } from "@/lib/course-gate";
import type {
  CourseCatalogItem,
  CourseCatalogView,
  CourseOverviewResponse,
} from "@/types";

type CatalogUser =
  | {
      id: string;
      full_name: string;
      is_onboarded: boolean;
    }
  | null;

interface BuildCatalogPageViewModelInput {
  user: CatalogUser;
  activeView: CourseCatalogView;
  allCourses: CourseCatalogItem[];
  recommendedCourses: CourseCatalogItem[];
  hasRecommendations: boolean;
}

interface BuildCourseOverviewViewModelInput {
  data: CourseOverviewResponse;
  isStarting: boolean;
}

export function buildCatalogPageViewModel({
  user,
  activeView,
  allCourses,
  recommendedCourses,
  hasRecommendations,
}: BuildCatalogPageViewModelInput) {
  const isAuthenticated = user !== null;
  const firstName = user?.full_name.split(" ")[0] ?? null;
  const displayedCourses =
    activeView === "recommended" && hasRecommendations
      ? recommendedCourses
      : allCourses;

  return {
    hero: {
      title: isAuthenticated
        ? `Welcome back, ${firstName}`
        : "Start from the catalog, then move into a guided lecture experience with AI Tutor in context.",
      description: isAuthenticated
        ? "Pick up where you left off or explore new courses. Your recommended path is based on your skill assessment."
        : "The home landing now surfaces every public course. Ready courses open into overview and learning flow. Upcoming courses stay visible so the platform can grow without breaking the contract.",
      primaryAction: isAuthenticated
        ? null
        : {
            href: "/login",
            label: "Sign in to continue",
          },
      statusTitle: isAuthenticated
        ? "Your learning status"
        : "Current rollout rules",
      statusItems: isAuthenticated
        ? [
            hasRecommendations
              ? "✅ Skill test completed — personalized recommendations active."
              : "📋 Complete the skill assessment to unlock recommended courses.",
            "CS231n is the only learnable demo course in this phase.",
            "CS224n stays visible with a consistent coming-soon state.",
          ]
        : [
            "CS231n is the only learnable demo course in this phase.",
            "CS224n stays visible with a consistent coming-soon state.",
            "Start learning routes into auth and onboarding gates before the protected flow.",
          ],
    },
    catalog: {
      kicker: isAuthenticated && hasRecommendations ? "Your catalog" : "Public catalog",
      title: isAuthenticated && hasRecommendations
        ? "Your learning path"
        : "Explore available courses",
      showTabs: isAuthenticated && hasRecommendations,
      displayedCourses,
      tabs: [
        { key: "recommended" as const, label: "Recommended for you" },
        { key: "all" as const, label: "All courses" },
      ],
    },
  };
}

export function buildCourseOverviewViewModel({
  data,
  isStarting,
}: BuildCourseOverviewViewModelInput) {
  const gate = getCourseGateState(data.course.status, data.entry);

  return {
    courseTitle: data.course.title,
    bannerMessage: gate.message,
    cta: {
      label: gate.canStartLearning
        ? data.overview.cta_label ?? "Start learning"
        : "Coming soon",
      disabled: !gate.canStartLearning,
      loading: isStarting,
    },
    gate,
  };
}
