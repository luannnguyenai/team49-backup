import Button from "@/components/ui/Button";
import CourseStatusBadge from "@/components/course/CourseStatusBadge";
import { buildCourseOverviewViewModel } from "@/features/course-platform/presenters";
import type { CourseOverviewResponse } from "@/types";

interface CourseOverviewProps {
  data: CourseOverviewResponse;
  isStarting?: boolean;
  onStart?: () => void;
}

export default function CourseOverview({
  data,
  isStarting = false,
  onStart,
}: CourseOverviewProps) {
  const model = buildCourseOverviewViewModel({ data, isStarting });

  return (
    <div className="space-y-8">
      <section className="card overflow-hidden rounded-[32px] border p-0 shadow-[0_18px_55px_rgba(15,23,42,0.08)]">
        <div className="grid gap-0 lg:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.85fr)]">
          <div className="space-y-6 p-6 md:p-8">
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">
                Course overview
              </p>
              <CourseStatusBadge status={data.course.status} />
            </div>

            <div className="space-y-3">
              <h1 className="text-3xl font-semibold leading-tight text-slate-950 lg:text-4xl">
                {data.overview.headline}
              </h1>
              {data.overview.subheadline && (
                <p className="max-w-2xl text-base leading-7 text-slate-600">
                  {data.overview.subheadline}
                </p>
              )}
            </div>

            <p className="max-w-2xl text-sm leading-7 text-slate-600">
              {data.overview.summary_markdown}
            </p>

            <div className="flex flex-wrap gap-2">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                {model.courseTitle}
              </span>
              <span className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700">
                {data.overview.estimated_duration_text ?? "Duration will be added later"}
              </span>
              {data.course.hero_badge && (
                <span className="rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-700">
                  {data.course.hero_badge}
                </span>
              )}
            </div>
          </div>

          <aside className="border-t bg-slate-50/80 p-6 md:p-8 lg:border-l lg:border-t-0">
            <div className="space-y-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                  What to expect
                </p>
                <p className="mt-2 text-2xl font-semibold text-slate-950">
                  {model.courseTitle}
                </p>
              </div>

              <div className="space-y-3 text-sm leading-6 text-slate-600">
                <p>
                  <span className="font-semibold text-slate-950">Audience:</span>{" "}
                  {data.overview.target_audience ?? "General learners"}
                </p>
                <p>
                  <span className="font-semibold text-slate-950">Prerequisites:</span>{" "}
                  {data.overview.prerequisites_summary ?? "To be added"}
                </p>
              </div>

              {model.bannerMessage && (
                <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {model.bannerMessage}
                </p>
              )}

              <Button
                onClick={onStart}
                disabled={model.cta.disabled}
                loading={model.cta.loading}
                className="w-full rounded-full"
              >
                {model.cta.label}
              </Button>
            </div>
          </aside>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(260px,0.8fr)]">
        <article className="card rounded-[28px] p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-700">
            What you will get
          </p>
          <ul className="mt-5 space-y-4">
            {data.overview.learning_outcomes.map((outcome) => (
              <li
                key={outcome}
                className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm leading-6"
                style={{ color: "var(--text-primary)" }}
              >
                {outcome}
              </li>
            ))}
          </ul>
        </article>

        <article className="card rounded-[28px] p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-700">
            Structure
          </p>
          <p className="mt-5 text-sm leading-7" style={{ color: "var(--text-secondary)" }}>
            {typeof data.overview.structure_snapshot?.summary === "string"
              ? data.overview.structure_snapshot.summary
              : "Course structure details will be backed by authoritative metadata later."}
          </p>
        </article>
      </section>
    </div>
  );
}
