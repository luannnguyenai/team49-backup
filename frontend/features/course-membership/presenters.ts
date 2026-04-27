import type { CourseCatalogItem, HistoryItem } from "@/types";

interface UserCourseCollections {
  activeCourse: CourseCatalogItem | null;
  joinedCourses: CourseCatalogItem[];
  recommendedCourses: CourseCatalogItem[];
}

export function countJoinedCourseSlugs(historyItems: HistoryItem[]) {
  return new Set(
    historyItems
      .map((item) => item.course_slug)
      .filter((courseSlug): courseSlug is string => Boolean(courseSlug)),
  ).size;
}

export function buildUserCourseCollections(
  items: CourseCatalogItem[],
  historyItems: HistoryItem[],
  activeSlug: string | null,
): UserCourseCollections {
  const joinedSlugs = new Set(
    historyItems
      .map((item) => item.course_slug)
      .filter((courseSlug): courseSlug is string => Boolean(courseSlug)),
  );

  const activeCourse = activeSlug
    ? items.find((item) => item.slug === activeSlug) ?? null
    : null;

  const joinedCourses = items.filter((item) => joinedSlugs.has(item.slug));
  const joinedCourseSlugs = new Set(joinedCourses.map((item) => item.slug));

  const recommendedCourses = items.filter(
    (item) => item.is_recommended && !joinedCourseSlugs.has(item.slug),
  );

  return {
    activeCourse,
    joinedCourses,
    recommendedCourses,
  };
}
