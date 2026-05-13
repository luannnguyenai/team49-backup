"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { BookOpen, TrendingUp, Clock, Play } from "lucide-react";

import CourseStatusBadge from "@/components/course/CourseStatusBadge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import SegmentedControl from "@/components/ui/SegmentedControl";
import {
  buildDashboardCourseCardModel,
  filterDashboardCourses,
  type DashboardCourseTab,
} from "@/features/dashboard/presenters";
import { historyApi } from "@/lib/api";
import { getCachedAllCourseCatalog } from "@/lib/course-catalog-cache";
import {
  filterCoursesByQuery,
  normalizeCourseSearchQuery,
} from "@/lib/course-search";
import { usePageTitle } from "@/hooks/usePageTitle";
import { useAuthStore } from "@/stores/authStore";
import type { CourseCatalogItem, HistorySummary } from "@/types";

const TABS: { key: DashboardCourseTab; label: string }[] = [
  { key: "for-you", label: "For you" },
  { key: "all", label: "All" },
  { key: "ready", label: "Ready" },
  { key: "coming_soon", label: "Coming soon" },
];

function StatCard({
  icon,
  iconBg,
  value,
  label,
}: {
  icon: React.ReactNode;
  iconBg: string;
  value: string;
  label: string;
}) {
  return (
    <div className="card flex items-center gap-3 p-4 sm:gap-4">
      <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${iconBg} sm:h-12 sm:w-12`}>
        {icon}
      </div>
      <div>
        <p className="text-xl font-bold text-text-strong sm:text-2xl">{value}</p>
        <p className="text-sm text-text-body">{label}</p>
      </div>
    </div>
  );
}

function CourseCard({ course }: { course: CourseCatalogItem }) {
  const model = buildDashboardCourseCardModel(course);
  const progressPercent = Math.min(Math.max(course.progress_percent ?? 0, 0), 100);

  return (
    <div className="card group flex flex-col overflow-hidden p-0 transition-shadow hover:shadow-brand-soft">
      <div
        className="relative flex h-28 items-center justify-center hero-gradient sm:h-32 lg:h-36"
      >
        <BookOpen className="h-12 w-12 text-white opacity-30" />
        <div className="absolute right-3 top-3">
          <CourseStatusBadge status={course.status} />
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
        <div>
          <h3 className="line-clamp-2 font-semibold leading-snug text-text-strong">
            {course.title}
          </h3>
          <p className="mt-1 line-clamp-2 text-sm text-text-body">
            {course.short_description}
          </p>
        </div>

        {course.status !== "ready" ? (
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {model.statusDetail}
            </span>
          </div>
        ) : null}

        {course.status === "ready" ? (
          <div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-page">
              <div
                className="h-full rounded-full bg-primary-600"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-text-muted">Progress: {progressPercent}%</p>
          </div>
        ) : null}

        <Link href={model.href} className="btn-primary mt-auto justify-center">
          <Play className="h-3.5 w-3.5" />
          {model.ctaLabel}
        </Link>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  usePageTitle("AI Learning Hub - Dashboard");
  const user = useAuthStore((s) => s.user);
  const searchParams = useSearchParams();
  const [courses, setCourses] = useState<CourseCatalogItem[]>([]);
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<DashboardCourseTab>("for-you");
  const rawQuery = searchParams.get("q") ?? "";
  const normalizedQuery = normalizeCourseSearchQuery(rawQuery);
  const hasActiveSearch = normalizedQuery.length >= 2;

  useEffect(() => {
    Promise.all([getCachedAllCourseCatalog(true), historyApi.list({ page_size: 1 })])
      .then(([catalog, hist]) => {
        setCourses(catalog.items);
        setSummary(hist.summary);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filteredByTab = filterDashboardCourses(courses, activeTab);
  const filtered = filterCoursesByQuery(filteredByTab, rawQuery);
  const totalHours = summary ? Math.round((summary.total_study_seconds ?? 0) / 3600) : 0;
  const avgScore = summary?.avg_score != null ? Math.round(summary.avg_score) : 0;
  const firstName = user?.full_name.split(" ")[0] ?? "there";
  const noRecommendations = activeTab === "for-you" && filteredByTab.length === 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in sm:space-y-8">
      <div className="space-y-3">
        <h1 className="text-2xl font-bold text-text-strong">
          Welcome back, {firstName}! 👋
        </h1>
        <p className="mt-1 text-sm text-text-body">
          Continue your learning journey today.
        </p>
      </div>

      {loading ? (
        <div className="flex h-24 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
          <StatCard
            icon={<BookOpen className="h-6 w-6 text-stat-courses" />}
            iconBg="bg-stat-courses-soft"
            value={String(courses.length)}
            label="Courses in catalog"
          />
          <StatCard
            icon={<TrendingUp className="h-6 w-6 text-stat-progress" />}
            iconBg="bg-stat-progress-soft"
            value={`${avgScore}%`}
            label="Average progress"
          />
          <StatCard
            icon={<Clock className="h-6 w-6 text-stat-time" />}
            iconBg="bg-stat-time-soft"
            value={`${totalHours}h`}
            label="Total study time"
          />
        </div>
      )}

      <div>
        <div className="mb-4 space-y-2">
          <h2 className="text-lg font-bold text-text-strong">Explore courses</h2>
          <p className="text-sm text-text-body">
            Start with the clearest next step, then branch into the wider catalog.
          </p>
        </div>

        <SegmentedControl
          ariaLabel="Course filters"
          className="mb-6 w-full max-w-full overflow-x-auto sm:w-auto"
          value={activeTab}
          onChange={setActiveTab}
          options={TABS.map(({ key, label }) => ({ value: key, label }))}
        />

        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <LoadingSpinner size="md" />
          </div>
        ) : hasActiveSearch && filtered.length === 0 ? (
          <>
            <p className="sr-only" aria-live="polite">
              0 results for keyword {rawQuery}
            </p>
            <div className="flex h-40 items-center justify-center rounded-xl border border-border-subtle text-center text-text-muted">
              No courses matched the keyword &quot;{rawQuery}&quot;.
            </div>
          </>
        ) : filtered.length === 0 ? (
          <div className="flex h-40 items-center justify-center rounded-xl border border-border-subtle text-text-muted">
            {noRecommendations
              ? "There are no personalized recommendations for you yet."
              : "There are no courses in this section."}
          </div>
        ) : (
          <>
            <p className="sr-only" aria-live="polite">
              {filtered.length} results
              {hasActiveSearch ? ` for keyword ${rawQuery}` : ""}
            </p>
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((course) => (
                <CourseCard key={course.id} course={course} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
