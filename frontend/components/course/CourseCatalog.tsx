import Link from "next/link";

import CourseStatusBadge from "@/components/course/CourseStatusBadge";
import type { CourseCatalogItem } from "@/types";

interface CourseCatalogProps {
  items: CourseCatalogItem[];
}

export default function CourseCatalog({ items }: CourseCatalogProps) {
  if (items.length === 0) {
    return (
      <div className="card rounded-[28px] border-dashed p-10 text-center">
        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
          No courses are available in this view yet.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      {items.map((course) => (
        <article
          key={course.slug}
          className="card group overflow-hidden rounded-[28px] border p-0 shadow-[0_18px_55px_rgba(15,23,42,0.08)] transition-transform duration-200 hover:-translate-y-1"
        >
          <div className="relative overflow-hidden border-b border-slate-200/80 bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_42%),linear-gradient(135deg,#0f172a_0%,#1e293b_50%,#f8fafc_100%)] px-6 py-8 text-white">
            <div className="absolute right-5 top-5 h-20 w-20 rounded-full bg-white/10 blur-2xl" />
            <div className="relative space-y-4">
              <CourseStatusBadge status={course.status} />
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/70">
                  Stanford Course Demo
                </p>
                <h2 className="text-2xl font-semibold leading-tight">{course.title}</h2>
                <p className="max-w-xl text-sm leading-6 text-white/80">
                  {course.short_description}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4 p-6">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                {course.hero_badge ?? "Explore overview"}
              </p>
              {course.is_recommended && (
                <span className="rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-700">
                  Recommended
                </span>
              )}
            </div>

            <Link
              href={`/courses/${course.slug}`}
              className="inline-flex items-center justify-center rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
            >
              Open overview
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}
