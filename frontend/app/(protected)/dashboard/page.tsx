"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, TrendingUp, Clock, Play, ChevronDown } from "lucide-react";

import CourseStatusBadge from "@/components/course/CourseStatusBadge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import {
  buildDashboardCourseCardModel,
  filterDashboardCourses,
  type DashboardCourseTab,
} from "@/features/dashboard/presenters";
import { courseApi, historyApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type { CourseCatalogItem, HistorySummary } from "@/types";

const GRADIENTS = [
  "from-blue-500 to-indigo-600",
  "from-violet-500 to-purple-600",
  "from-emerald-500 to-teal-600",
  "from-orange-500 to-red-500",
  "from-pink-500 to-rose-600",
  "from-cyan-500 to-blue-500",
];

const TABS: { key: DashboardCourseTab; label: string }[] = [
  { key: "for-you", label: "Dành cho bạn" },
  { key: "all", label: "Tất cả" },
  { key: "ready", label: "Sẵn sàng" },
  { key: "coming_soon", label: "Sắp ra mắt" },
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
    <div
      className="card flex items-center gap-4"
      style={{ backgroundColor: "var(--bg-card)" }}
    >
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${iconBg}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          {value}
        </p>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {label}
        </p>
      </div>
    </div>
  );
}

function CourseCard({ course, idx }: { course: CourseCatalogItem; idx: number }) {
  const gradient = GRADIENTS[idx % GRADIENTS.length];
  const model = buildDashboardCourseCardModel(course);

  return (
    <div
      className="card flex flex-col overflow-hidden transition-shadow group hover:shadow-md"
      style={{ backgroundColor: "var(--bg-card)", padding: 0 }}
    >
      <div
        className={`relative flex h-36 items-center justify-center bg-gradient-to-br ${gradient}`}
      >
        <BookOpen className="h-12 w-12 text-white opacity-30" />
        <div className="absolute right-3 top-3">
          <CourseStatusBadge status={course.status} />
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3
            className="line-clamp-2 font-semibold leading-snug"
            style={{ color: "var(--text-primary)" }}
          >
            {course.title}
          </h3>
          <p
            className="mt-1 line-clamp-2 text-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            {course.short_description}
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
          <span className="flex items-center gap-1">
            <Play className="h-3 w-3" />
            {course.status === "ready" ? "Sẵn sàng học" : "Đang hoàn thiện"}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {model.statusDetail}
          </span>
        </div>

        <div>
          <div
            className="h-1.5 w-full overflow-hidden rounded-full"
            style={{ backgroundColor: "var(--bg-page)" }}
          >
            <div className="h-full w-0 rounded-full bg-primary-600" />
          </div>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Tiến độ: 0%
          </p>
        </div>

        <Link
          href={model.href}
          className="mt-auto flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium transition-opacity hover:opacity-90"
          style={{ backgroundColor: "var(--primary-600, #2563eb)", color: "white" }}
        >
          <Play className="h-3.5 w-3.5" />
          {model.ctaLabel}
        </Link>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const [courses, setCourses] = useState<CourseCatalogItem[]>([]);
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<DashboardCourseTab>("for-you");

  useEffect(() => {
    Promise.all([courseApi.catalog({ includeUnavailable: true }), historyApi.list({ page_size: 1 })])
      .then(([catalog, hist]) => {
        setCourses(catalog.items);
        setSummary(hist.summary);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = filterDashboardCourses(courses, activeTab);
  const totalHours = summary ? Math.round((summary.total_study_seconds ?? 0) / 3600) : 0;
  const avgScore = summary?.avg_score != null ? Math.round(summary.avg_score) : 0;
  const firstName = user?.full_name.split(" ")[0] ?? "bạn";

  return (
    <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Chào mừng trở lại, {firstName}! 👋
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Tiếp tục hành trình học của bạn hôm nay.
        </p>
      </div>

      {loading ? (
        <div className="flex h-24 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            icon={<BookOpen className="h-6 w-6 text-blue-600" />}
            iconBg="bg-blue-100 dark:bg-blue-900/30"
            value={String(courses.length)}
            label="Khóa học trong catalog"
          />
          <StatCard
            icon={<TrendingUp className="h-6 w-6 text-emerald-600" />}
            iconBg="bg-emerald-100 dark:bg-emerald-900/30"
            value={`${avgScore}%`}
            label="Tiến độ trung bình"
          />
          <StatCard
            icon={<Clock className="h-6 w-6 text-violet-600" />}
            iconBg="bg-violet-100 dark:bg-violet-900/30"
            value={`${totalHours}h`}
            label="Tổng thời gian học"
          />
        </div>
      )}

      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
            Tất cả khóa học
          </h2>
          <button
            className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
              backgroundColor: "var(--bg-card)",
            }}
          >
            Tất cả <ChevronDown className="h-4 w-4" />
          </button>
        </div>

        <div
          className="mb-6 flex gap-1 rounded-xl p-1 w-fit"
          style={{ backgroundColor: "var(--bg-page)" }}
        >
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === key
                  ? "bg-white text-primary-600 shadow-sm dark:bg-slate-800"
                  : "hover:bg-white/60 dark:hover:bg-slate-800/60"
              }`}
              style={activeTab !== key ? { color: "var(--text-secondary)" } : {}}
            >
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <LoadingSpinner size="md" />
          </div>
        ) : filtered.length === 0 ? (
          <div
            className="flex h-40 items-center justify-center rounded-xl border"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          >
            Không có khóa học nào trong mục này.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((course, idx) => (
              <CourseCard key={course.id} course={course} idx={idx} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
