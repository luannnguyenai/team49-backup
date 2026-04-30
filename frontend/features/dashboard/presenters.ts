import type { CourseCatalogItem } from "@/types";

export type DashboardCourseTab = "for-you" | "all" | "ready" | "coming_soon";

export interface DashboardCourseCardModel {
  href: string;
  ctaLabel: string;
  statusDetail: string;
}

export function filterDashboardCourses(
  courses: CourseCatalogItem[],
  activeTab: DashboardCourseTab,
): CourseCatalogItem[] {
  if (activeTab === "for-you") {
    return courses.filter((course) => course.is_recommended);
  }

  if (activeTab === "all") {
    return courses;
  }

  return courses.filter((course) => course.status === activeTab);
}

export function buildDashboardCourseCardModel(
  course: CourseCatalogItem,
): DashboardCourseCardModel {
  if (course.status === "ready") {
    return {
      href: `/courses/${course.slug}/start`,
      ctaLabel: "Start learning",
      statusDetail: "Ready to start right now",
    };
  }

  if (course.status === "coming_soon") {
    return {
      href: `/courses/${course.slug}`,
      ctaLabel: "View overview",
      statusDetail: "This course is visible before its metadata is finalized",
    };
  }

  return {
    href: `/courses/${course.slug}`,
    ctaLabel: "View overview",
    statusDetail: "Metadata is still being finalized before learning access opens",
  };
}
