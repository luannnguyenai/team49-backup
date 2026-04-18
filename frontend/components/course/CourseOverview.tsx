import Button from "@/components/ui/Button";
import { getCourseGateState } from "@/lib/course-gate";
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
  const gate = getCourseGateState(data.course.status, data.entry);
  const ctaLabel = gate.canStartLearning
    ? data.overview.cta_label ?? "Start learning"
    : "Coming soon";

  return (
    <div className="space-y-8">
      <section className="card overflow-hidden rounded-[32px] border p-0 shadow-[0_24px_60px_rgba(15,23,42,0.08)]">
        <div className="grid gap-8 bg-[linear-gradient(145deg,#082f49_0%,#0f172a_48%,#f8fafc_100%)] px-8 py-10 text-white lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.9fr)]">
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
              Course overview
            </p>
            <div className="space-y-3">
              <h1 className="text-3xl font-semibold leading-tight lg:text-4xl">
                {data.overview.headline}
              </h1>
              {data.overview.subheadline && (
                <p className="max-w-2xl text-base leading-7 text-slate-200">
                  {data.overview.subheadline}
                </p>
              )}
            </div>
            <p className="max-w-2xl text-sm leading-7 text-slate-200">
              {data.overview.summary_markdown}
            </p>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-white/8 p-6 backdrop-blur">
            <div className="space-y-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/60">
                  Availability
                </p>
                <p className="mt-2 text-2xl font-semibold">{data.course.title}</p>
                <p className="mt-2 text-sm text-slate-200">
                  {data.overview.estimated_duration_text ?? "Duration will be added later"}
                </p>
              </div>

              <div className="space-y-2 text-sm text-slate-200">
                <p>
                  <span className="font-semibold text-white">Audience:</span>{" "}
                  {data.overview.target_audience ?? "General learners"}
                </p>
                <p>
                  <span className="font-semibold text-white">Prerequisites:</span>{" "}
                  {data.overview.prerequisites_summary ?? "To be added"}
                </p>
              </div>

              {gate.message && (
                <p className="rounded-2xl border border-amber-200/50 bg-amber-50/10 px-4 py-3 text-sm text-amber-100">
                  {gate.message}
                </p>
              )}

              <Button
                onClick={onStart}
                disabled={!gate.canStartLearning}
                loading={isStarting}
                className="w-full rounded-full"
              >
                {ctaLabel}
              </Button>
            </div>
          </div>
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
