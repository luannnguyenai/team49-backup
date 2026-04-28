import type { CourseCatalogItem } from "@/types";

function stripVietnameseDiacritics(value: string): string {
  return value.normalize("NFD").replace(/\p{Diacritic}/gu, "");
}

export function normalizeCourseSearchQuery(query: string): string {
  return stripVietnameseDiacritics(query)
    .toLowerCase()
    .trim()
    .replace(/\s+/g, " ");
}

export function matchesCourseQuery(course: CourseCatalogItem, query: string): boolean {
  const normalizedQuery = normalizeCourseSearchQuery(query);
  if (normalizedQuery.length < 2) {
    return true;
  }

  const haystack = normalizeCourseSearchQuery(
    [course.title, course.short_description, course.hero_kicker ?? ""].join(" "),
  );

  return haystack.includes(normalizedQuery);
}

export function filterCoursesByQuery(
  courses: CourseCatalogItem[],
  query: string,
): CourseCatalogItem[] {
  const normalizedQuery = normalizeCourseSearchQuery(query);
  if (normalizedQuery.length < 2) {
    return courses;
  }

  return courses.filter((course) => matchesCourseQuery(course, normalizedQuery));
}
