import Link from "next/link";

import CourseStatusBadge from "@/components/course/CourseStatusBadge";
import type { CourseCatalogItem } from "@/types";

interface CourseCatalogProps {
  items: CourseCatalogItem[];
  emptyMessage?: string;
}

const DEFAULT_EMPTY_MESSAGE = "There are no courses in this section yet.";

function getGradientClass(slug: string) {
  const gradients = [
    "from-sky-500 via-cyan-500 to-slate-950",
    "from-violet-500 via-indigo-500 to-slate-950",
    "from-emerald-500 via-teal-500 to-slate-950",
    "from-amber-500 via-orange-500 to-slate-950",
  ];

  let hash = 0;
  for (let index = 0; index < slug.length; index += 1) {
    hash = (hash * 31 + slug.charCodeAt(index)) >>> 0;
  }

  return gradients[hash % gradients.length];
}

function getLearningProgressCopy(course: CourseCatalogItem) {
  if (course.status !== "ready" || typeof course.progress_percent !== "number") {
    return null;
  }

  if (course.progress_percent > 0) {
    return {
      title: "Continue lesson",
      subtitle: null,
      progressLabel: `Progress: ${course.progress_percent}%`,
    };
  }

  return {
    title: "Ready to learn",
    subtitle: "Ready to start right now",
    progressLabel: "Progress: 0%",
  };
}

export default function CourseCatalog({
  items,
  emptyMessage = DEFAULT_EMPTY_MESSAGE,
}: CourseCatalogProps) {
  if (items.length === 0) {
    return (
      <div className="card rounded-card border-dashed p-10 text-center">
        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
          {emptyMessage}
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2 lg:gap-5">
      {items.map((course) => (
        (() => {
          const progressCopy = getLearningProgressCopy(course);

          return (
            <article
              key={course.slug}
              className="card group overflow-hidden rounded-card border p-0 shadow-card transition-all duration-200 hover:-translate-y-1 hover:shadow-card-hover"
            >
              <div
                className={`relative overflow-hidden bg-gradient-to-br px-4 py-4 text-white sm:px-5 sm:py-5 md:px-6 md:py-6 ${
                  getGradientClass(course.slug)
                }`}
              >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.22),_transparent_36%)]" />
                <div className="relative flex min-h-[132px] flex-col justify-between gap-5 sm:min-h-[160px]">
                  <div className="flex items-start justify-between gap-4">
                    {progressCopy ? (
                      <div className="rounded-2xl border border-white/15 bg-white/10 px-3 py-2 text-white">
                        <p className="text-xs font-semibold uppercase tracking-widest-sm text-white/80">
                          {progressCopy.title}
                        </p>
                        {progressCopy.subtitle ? (
                          <p className="mt-1 text-xs text-white/70">{progressCopy.subtitle}</p>
                        ) : null}
                        <p className="mt-1 text-sm font-semibold text-white">
                          {progressCopy.progressLabel}
                        </p>
                      </div>
                    ) : (
                      <CourseStatusBadge status={course.status} />
                    )}
                    <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold text-white/80">
                      {course.hero_badge ?? "View overview"}
                    </span>
                  </div>

                  <div className="space-y-3">
                    {course.hero_kicker && (
                      <p className="text-xs font-semibold uppercase tracking-widest-md text-white/70">
                        {course.hero_kicker}
                      </p>
                    )}
                    <h2 className="text-2xl font-semibold leading-tight">{course.title}</h2>
                  </div>
                </div>
              </div>

              <div className="flex flex-1 flex-col gap-4 p-4 sm:p-5 md:p-6">
                <div className="flex flex-wrap items-center gap-2">
                  {course.is_recommended && (
                    <span className="rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-700 dark:bg-primary-900/30 dark:text-primary-200">
                      Recommended
                    </span>
                  )}
                </div>

                <p className="text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
                  {course.short_description}
                </p>

                <Link
                  href={`/courses/${course.slug}`}
                  className="btn-primary mt-auto inline-flex w-full items-center justify-center px-5 py-2.5"
                >
                  View course
                </Link>
              </div>
            </article>
          );
        })()
      ))}
    </div>
  );
}
