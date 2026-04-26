import { redirect } from "next/navigation";

import LearningPageScreen from "@/components/learn/LearningPageScreen";
import { fetchLearningUnit, ServerCourseApiError } from "@/lib/server-course-api";

interface LearningPageProps {
  params: Promise<{
    courseSlug: string;
    unitSlug: string;
  }>;
}

export default async function LearningPage({ params }: LearningPageProps) {
  const resolvedParams = await params;
  let error: string | null = null;
  let data = null;

  try {
    data = await fetchLearningUnit(resolvedParams.courseSlug, resolvedParams.unitSlug);
  } catch (err) {
    if (
      err instanceof ServerCourseApiError &&
      (err.status === 401 || err.status === 403)
    ) {
      redirect(`/courses/${resolvedParams.courseSlug}/start`);
    }

    if (err instanceof ServerCourseApiError && err.status === 404) {
      error =
        "This learning unit is not available. It may not exist or the course content has not been published yet.";
    } else {
      error =
        err instanceof Error
          ? err.message
          : "Failed to load learning unit.";
    }
  }

  return (
    <LearningPageScreen
      courseSlug={resolvedParams.courseSlug}
      unitSlug={resolvedParams.unitSlug}
      data={data}
      error={error}
    />
  );
}
