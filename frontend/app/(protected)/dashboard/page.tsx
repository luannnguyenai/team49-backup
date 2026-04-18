"use client";
// app/(protected)/dashboard/page.tsx
// Dashboard: welcome, stats, and course listing with 4 filter tabs.

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, TrendingUp, Clock, Play, ChevronDown } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { contentApi, historyApi } from "@/lib/api";
import type { ModuleListItem, HistorySummary } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

// ---- Difficulty helpers ----
type Difficulty = "for-you" | "basic" | "intermediate" | "advanced";

function getDifficulty(m: ModuleListItem): "basic" | "intermediate" | "advanced" {
  const prereqs = m.prerequisite_module_ids?.length ?? 0;
  if (prereqs === 0) return "basic";
  if (prereqs === 1) return "intermediate";
  return "advanced";
}

const DIFF_LABEL: Record<string, string> = {
  basic: "Cơ bản",
  intermediate: "Trung bình",
  advanced: "Nâng cao",
};

const DIFF_COLOR: Record<string, string> = {
  basic: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  intermediate: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  advanced: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

// Gradient thumbnails per order_index
const GRADIENTS = [
  "from-blue-500 to-indigo-600",
  "from-violet-500 to-purple-600",
  "from-emerald-500 to-teal-600",
  "from-orange-500 to-red-500",
  "from-pink-500 to-rose-600",
  "from-cyan-500 to-blue-500",
];

const TABS: { key: Difficulty; label: string }[] = [
  { key: "for-you", label: "Dành cho bạn" },
  { key: "basic", label: "Cơ bản" },
  { key: "intermediate", label: "Trung bình" },
  { key: "advanced", label: "Nâng cao" },
];

// ---- Stat card ----
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

// ---- Course card ----
function CourseCard({ module, idx }: { module: ModuleListItem; idx: number }) {
  const diff = getDifficulty(module);
  const gradient = GRADIENTS[idx % GRADIENTS.length];

  return (
    <div
      className="card overflow-hidden flex flex-col group hover:shadow-md transition-shadow"
      style={{ backgroundColor: "var(--bg-card)", padding: 0 }}
    >
      {/* Thumbnail */}
      <div className={`relative h-36 bg-gradient-to-br ${gradient} flex items-center justify-center`}>
        <BookOpen className="h-12 w-12 text-white opacity-30" />
        <span
          className={`absolute top-3 right-3 rounded-full px-2.5 py-0.5 text-xs font-semibold ${DIFF_COLOR[diff]}`}
        >
          {DIFF_LABEL[diff]}
        </span>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3
            className="font-semibold leading-snug line-clamp-2"
            style={{ color: "var(--text-primary)" }}
          >
            {module.name}
          </h3>
          {module.description && (
            <p
              className="mt-1 text-sm line-clamp-2"
              style={{ color: "var(--text-secondary)" }}
            >
              {module.description}
            </p>
          )}
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
          <span className="flex items-center gap-1">
            <Play className="h-3 w-3" />
            {module.topics_count} bài
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            0 bài tập
          </span>
        </div>

        {/* Progress bar */}
        <div>
          <div
            className="h-1.5 w-full rounded-full overflow-hidden"
            style={{ backgroundColor: "var(--bg-page)" }}
          >
            <div className="h-full w-0 rounded-full bg-primary-600" />
          </div>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Tiến độ: 0%
          </p>
        </div>

        {/* CTA */}
        <Link
          href="/courses/cs231n/start"
          className="mt-auto flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium transition-opacity hover:opacity-90"
          style={{ backgroundColor: "var(--primary-600, #2563eb)", color: "white" }}
        >
          <Play className="h-3.5 w-3.5" />
          Bắt đầu học
        </Link>
      </div>
    </div>
  );
}

// ---- Page ----
export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const [modules, setModules] = useState<ModuleListItem[]>([]);
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Difficulty>("for-you");

  useEffect(() => {
    Promise.all([
      contentApi.modules(),
      historyApi.list({ page_size: 1 }),
    ])
      .then(([mods, hist]) => {
        setModules(mods);
        setSummary(hist.summary);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Filter courses based on active tab
  const filtered =
    activeTab === "for-you"
      ? modules
      : modules.filter((m) => getDifficulty(m) === activeTab);

  const totalHours = summary
    ? Math.round((summary.total_study_seconds ?? 0) / 3600)
    : 0;
  const avgScore = summary?.avg_score != null ? Math.round(summary.avg_score) : 0;

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-fade-in">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Chào mừng trở lại! 👋
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Tiếp tục hành trình học AI của bạn
        </p>
      </div>

      {/* Stat cards */}
      {loading ? (
        <div className="flex items-center justify-center h-24">
          <LoadingSpinner size="md" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            icon={<BookOpen className="h-6 w-6 text-blue-600" />}
            iconBg="bg-blue-100 dark:bg-blue-900/30"
            value={String(modules.length)}
            label="Khóa học đang học"
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

      {/* Course listing */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
            Tất cả khóa học
          </h2>
          {/* Sort dropdown — visual only */}
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

        {/* Filter tabs */}
        <div
          className="flex gap-1 rounded-xl p-1 mb-6 w-fit"
          style={{ backgroundColor: "var(--bg-page)" }}
        >
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === key
                  ? "bg-white dark:bg-slate-800 shadow-sm text-primary-600"
                  : "hover:bg-white/60 dark:hover:bg-slate-800/60"
              }`}
              style={activeTab !== key ? { color: "var(--text-secondary)" } : {}}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Cards grid */}
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <LoadingSpinner size="md" />
          </div>
        ) : filtered.length === 0 ? (
          <div
            className="flex items-center justify-center h-40 rounded-xl border"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          >
            Không có khóa học nào.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((m, i) => (
              <CourseCard key={m.id} module={m} idx={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
