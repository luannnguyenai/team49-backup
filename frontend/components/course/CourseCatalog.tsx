import Link from "next/link";

import CourseStatusBadge from "@/components/course/CourseStatusBadge";
import type { CourseCatalogItem } from "@/types";

interface CourseCatalogProps {
  items: CourseCatalogItem[];
}

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

export default function CourseCatalog({ items }: CourseCatalogProps) {
  if (items.length === 0) {
    return (
      <div className="card rounded-card border-dashed p-10 text-center">
        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
          Chưa có khóa học nào trong mục này.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      {items.map((course) => (
        <article
          key={course.slug}
          className="card group overflow-hidden rounded-card border p-0 shadow-card transition-all duration-200 hover:-translate-y-1 hover:shadow-card-hover"
        >
          <div
            className={`relative overflow-hidden bg-gradient-to-br px-6 py-6 text-white ${
              getGradientClass(course.slug)
            }`}
          >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.22),_transparent_36%)]" />
            <div className="relative flex min-h-[160px] flex-col justify-between gap-6">
              <div className="flex items-start justify-between gap-4">
                <CourseStatusBadge status={course.status} />
                <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold text-white/80">
                  {course.hero_badge ?? "Xem tổng quan"}
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

          <div className="flex flex-1 flex-col gap-4 p-6">
            <div className="flex flex-wrap items-center gap-2">
              {course.is_recommended && (
                <span className="rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-700">
                  Đề xuất
                </span>
              )}
            </div>

            <p className="text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
              {course.short_description}
            </p>

            <Link
              href={`/courses/${course.slug}`}
              className="mt-auto inline-flex w-full items-center justify-center rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
            >
              Xem khóa học
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}
