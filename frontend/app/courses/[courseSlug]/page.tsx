import Link from "next/link";

import CourseOverviewInteractive from "@/components/course/CourseOverviewInteractive";
import TopNav from "@/components/layout/TopNav";
import {
  fetchCourseOverview,
  ServerCourseApiError,
} from "@/lib/server-course-api";

interface CourseOverviewPageProps {
  params: {
    courseSlug: string;
  };
}

export default async function CourseOverviewPage({ params }: CourseOverviewPageProps) {
  let error: string | null = null;
  let data = null;

  try {
    data = await fetchCourseOverview(params.courseSlug);
  } catch (err) {
    error =
      err instanceof ServerCourseApiError
        ? err.message
        : "Failed to load course overview.";
  }

  return (
    <>
      <TopNav />
      <main className="min-h-screen px-4 py-8 md:px-6">
        <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
          <section className="space-y-2">
            <Link
              href="/"
              className="inline-flex items-center text-sm font-medium text-slate-600 transition-colors hover:text-slate-950"
            >
              ← Back to catalog
            </Link>
          </section>

          <CourseOverviewInteractive
            courseSlug={params.courseSlug}
            data={data}
            error={error}
          />
        </div>
      </main>
    </>
  );
}
