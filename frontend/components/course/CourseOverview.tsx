import Button from "@/components/ui/Button";
import CourseStatusBadge from "@/components/course/CourseStatusBadge";
import { buildCourseOverviewViewModel } from "@/features/course-platform/presenters";
import ReactMarkdown from "react-markdown";
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
      <section className="card overflow-hidden rounded-card-lg border p-0 shadow-card">
        <div className="grid gap-0 lg:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.85fr)]">
          <div className="space-y-6 p-6 md:p-8">
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-xs font-semibold uppercase tracking-widest-md text-primary-700">
                Tổng quan khóa học
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

            <div className="prose prose-sm max-w-2xl text-slate-600 prose-p:my-0 prose-ul:my-3 prose-li:my-1">
              <ReactMarkdown>{data.overview.summary_markdown}</ReactMarkdown>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                {model.courseTitle}
              </span>
              <span className="rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-700">
                {data.overview.estimated_duration_text ?? "Thời lượng sẽ được cập nhật"}
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
                <p className="text-xs font-semibold uppercase tracking-widest-sm text-slate-500">
                  Những gì bạn sẽ học
                </p>
                <p className="mt-2 text-2xl font-semibold text-slate-950">
                  {model.courseTitle}
                </p>
              </div>

              <div className="space-y-3 text-sm leading-6 text-slate-600">
                <p>
                  <span className="font-semibold text-slate-950">Đối tượng:</span>{" "}
                  {data.overview.target_audience ?? "Dành cho tất cả học viên"}
                </p>
                <p>
                  <span className="font-semibold text-slate-950">Yêu cầu trước:</span>{" "}
                  {data.overview.prerequisites_summary ?? "Chưa có yêu cầu"}
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
        <article className="card rounded-card p-7">
          <p className="text-xs font-semibold uppercase tracking-widest-sm text-primary-700">
            Kết quả học tập
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

        <article className="card rounded-card p-7">
          <p className="text-xs font-semibold uppercase tracking-widest-sm text-primary-700">
            Cấu trúc khóa học
          </p>
          <p className="mt-5 text-sm leading-7" style={{ color: "var(--text-secondary)" }}>
            {typeof data.overview.structure_snapshot?.summary === "string"
              ? data.overview.structure_snapshot.summary
              : "Chi tiết cấu trúc khóa học sẽ được cập nhật sớm."}
          </p>
        </article>
      </section>
    </div>
  );
}
