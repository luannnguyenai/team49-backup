import type {
  BootstrapCourse,
  BootstrapCourseOption,
  BootstrapTopic,
  BootstrapTopicGroup,
  BootstrapTopicOption,
  CourseSectionDetail,
} from "@/types";

export function courseSlugToCanonicalCourseId(slug: string): string {
  if (slug.length <= 2) {
    return slug.toUpperCase();
  }
  return `${slug.slice(0, 2).toUpperCase()}${slug.slice(2)}`;
}

export function normalizeBootstrapCourses(
  courses: BootstrapCourse[],
): BootstrapCourseOption[] {
  return [...courses]
    .sort((left, right) => left.sort_order - right.sort_order)
    .map((course) => ({
      ...course,
      canonical_course_id: courseSlugToCanonicalCourseId(course.slug),
    }));
}

export function normalizeBootstrapTopics(
  topics: BootstrapTopic[],
  courses: BootstrapCourseOption[],
): BootstrapTopicOption[] {
  return [...topics]
    .sort((left, right) => left.order_index - right.order_index)
    .map((topic) => {
      const matchedCourse =
        courses.find((course) =>
          topic.module_slug.toLowerCase().startsWith(`${course.slug.toLowerCase()}_`),
        ) ?? null;

      return {
        ...topic,
        course_slug: matchedCourse?.slug ?? null,
        canonical_course_id: matchedCourse?.canonical_course_id ?? null,
      };
    });
}

export function buildBootstrapTopicsFromCanonicalSections(
  sections: CourseSectionDetail[],
  courses: BootstrapCourseOption[],
): BootstrapTopicOption[] {
  const sortedSections = [...sections].sort((left, right) => {
    const courseCompare = (left.canonical_course_id ?? "").localeCompare(
      right.canonical_course_id ?? "",
    );
    if (courseCompare !== 0) {
      return courseCompare;
    }
    return left.order_index - right.order_index;
  });

  return sortedSections.flatMap((section) => {
    const matchedCourse =
      courses.find(
        (course) => course.canonical_course_id === section.canonical_course_id,
      ) ?? null;

    return [...section.learning_units]
      .sort((left, right) => left.order_index - right.order_index)
      .map((unit) => ({
        slug: unit.canonical_unit_id ?? unit.id,
        module_slug: section.id,
        name: unit.title,
        description: unit.description ?? "",
        order_index: section.order_index * 1000 + unit.order_index,
        estimated_hours_beginner: unit.estimated_hours_beginner,
        estimated_hours_intermediate: unit.estimated_hours_intermediate,
        estimated_hours_review: null,
        course_slug: matchedCourse?.slug ?? null,
        canonical_course_id: section.canonical_course_id ?? null,
      }));
  });
}

export function buildBootstrapTopicGroups(
  topics: BootstrapTopicOption[],
  courses: BootstrapCourseOption[],
): BootstrapTopicGroup[] {
  const grouped = courses
    .map((course) => ({
      course_key: course.canonical_course_id,
      course_title: course.title,
      topics: topics.filter(
        (topic) => topic.canonical_course_id === course.canonical_course_id,
      ),
    }))
    .filter((group) => group.topics.length > 0);

  const uncategorizedTopics = topics.filter((topic) => !topic.canonical_course_id);
  if (uncategorizedTopics.length > 0) {
    grouped.push({
      course_key: "uncategorized",
      course_title: "Khác",
      topics: uncategorizedTopics,
    });
  }

  return grouped;
}

export function estimateSelectedCourseHours(
  topics: BootstrapTopicOption[],
  selectedCourseIds: string[],
): number {
  const selected = new Set(selectedCourseIds.map((courseId) => courseId.toLowerCase()));
  return topics.reduce((sum, topic) => {
    if (!topic.canonical_course_id) {
      return sum;
    }
    if (!selected.has(topic.canonical_course_id.toLowerCase())) {
      return sum;
    }
    return sum + (topic.estimated_hours_beginner ?? 0);
  }, 0);
}
