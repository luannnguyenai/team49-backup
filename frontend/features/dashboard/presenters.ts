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
    const recommended = courses.filter((course) => course.is_recommended);
    return recommended.length > 0 ? recommended : courses;
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
      ctaLabel: "Bắt đầu học",
      statusDetail: "Sẵn sàng để bắt đầu ngay bây giờ",
    };
  }

  if (course.status === "coming_soon") {
    return {
      href: `/courses/${course.slug}`,
      ctaLabel: "Xem tổng quan",
      statusDetail: "Khóa học đang hiển thị trước khi metadata hoàn thiện",
    };
  }

  return {
    href: `/courses/${course.slug}`,
    ctaLabel: "Xem tổng quan",
    statusDetail: "Metadata đang được hoàn thiện để mở quyền học",
  };
}
