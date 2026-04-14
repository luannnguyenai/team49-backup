"use client";
// app/(protected)/profile/page.tsx
// Profile page: user card + AI skill radar chart + stats.

import { useEffect, useState } from "react";
import { BookOpen, Trophy, Clock, TrendingUp } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { contentApi, historyApi } from "@/lib/api";
import type { HistorySummary, ModuleListItem } from "@/types";
import RadarChart from "@/components/assessment/RadarChart";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

// Placeholder AI skill data — will be replaced by real assessment data when available
const PLACEHOLDER_SKILLS = [
  { label: "Machine Learning", value: 0, level: "not_started" },
  { label: "Deep Learning", value: 0, level: "not_started" },
  { label: "Computer Vision", value: 0, level: "not_started" },
  { label: "NLP", value: 0, level: "not_started" },
  { label: "LLM", value: 0, level: "not_started" },
];

const SKILL_COLORS: Record<string, string> = {
  not_started: "#94a3b8",
  novice: "#f87171",
  developing: "#fb923c",
  proficient: "#60a5fa",
  mastered: "#34d399",
};

// Achievement badge (placeholder)
const ACHIEVEMENTS = [
  { title: "Người học chăm chỉ", desc: "Hoàn thành 5 khóa học", icon: "🏆", color: "border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20" },
];

interface StatRowProps {
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: string;
}

function StatRow({ icon, iconBg, label, value }: StatRowProps) {
  return (
    <div
      className="flex items-center justify-between rounded-lg px-3 py-2.5"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      <div className="flex items-center gap-2.5">
        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${iconBg}`}>
          {icon}
        </div>
        <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          {label}
        </span>
      </div>
      <span className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
        {value}
      </span>
    </div>
  );
}

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);
  const [modules, setModules] = useState<ModuleListItem[]>([]);
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [loading, setLoading] = useState(true);

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

  if (!user) return null;

  const initials = user.full_name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const totalHours = summary
    ? Math.round((summary.total_study_seconds ?? 0) / 3600)
    : 0;

  const completedSessions = summary?.completed_sessions ?? 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Hồ sơ của bạn
        </h2>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <LoadingSpinner size="md" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* ── LEFT: User info card ── */}
          <div className="space-y-4">
            <div className="card space-y-4">
              {/* Avatar + name */}
              <div className="flex flex-col items-center text-center gap-3 pb-4 border-b" style={{ borderColor: "var(--border)" }}>
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-purple-600 text-white text-2xl font-bold shadow-lg">
                  {initials}
                </div>
                <div>
                  <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                    {user.full_name}
                  </p>
                  <span className="mt-1 inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 px-2.5 py-0.5 text-xs font-semibold">
                    Học viên Pro
                  </span>
                </div>
              </div>

              {/* Stats list */}
              <div className="space-y-2">
                <StatRow
                  icon={<BookOpen className="h-4 w-4 text-blue-600" />}
                  iconBg="bg-blue-100 dark:bg-blue-900/30"
                  label="Khóa học"
                  value={String(modules.length)}
                />
                <StatRow
                  icon={<Trophy className="h-4 w-4 text-emerald-600" />}
                  iconBg="bg-emerald-100 dark:bg-emerald-900/30"
                  label="Hoàn thành"
                  value={String(completedSessions)}
                />
                <StatRow
                  icon={<Clock className="h-4 w-4 text-violet-600" />}
                  iconBg="bg-violet-100 dark:bg-violet-900/30"
                  label="Tổng thời gian"
                  value={`${totalHours}h`}
                />
                <StatRow
                  icon={<TrendingUp className="h-4 w-4 text-orange-500" />}
                  iconBg="bg-orange-100 dark:bg-orange-900/30"
                  label="Streak"
                  value="0 ngày"
                />
              </div>
            </div>

            {/* Achievements */}
            <div className="card space-y-3">
              <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                Thành tích
              </h3>
              {ACHIEVEMENTS.map((a) => (
                <div
                  key={a.title}
                  className={`flex items-center gap-3 rounded-xl border p-3 ${a.color}`}
                >
                  <span className="text-2xl">{a.icon}</span>
                  <div>
                    <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      {a.title}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                      {a.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Account info */}
            <div className="card space-y-2">
              <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                Tài khoản
              </h3>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--text-muted)" }}>Email: </span>{user.email}
              </p>
              {user.preferred_method && (
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--text-muted)" }}>Học bằng: </span>
                  {user.preferred_method === "video" ? "🎥 Video" : "📖 Đọc tài liệu"}
                </p>
              )}
              {user.available_hours_per_week && (
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--text-muted)" }}>Giờ học / tuần: </span>
                  {user.available_hours_per_week}h
                </p>
              )}
            </div>
          </div>

          {/* ── RIGHT: Skills radar chart ── */}
          <div className="card space-y-6">
            <div>
              <h3 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
                Kỹ năng AI của bạn
              </h3>
              <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
                Biểu đồ radar hiển thị trình độ của bạn trong các lĩnh vực AI khác nhau
              </p>
            </div>

            {/* Radar chart */}
            <div className="flex justify-center">
              <RadarChart data={PLACEHOLDER_SKILLS} size={280} />
            </div>

            {/* Legend */}
            <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
              <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: "rgba(37,99,235,0.3)", border: "2px solid #2563eb" }} />
              Trình độ hiện tại
            </div>

            {/* Skill progress bars */}
            <div className="space-y-3">
              {PLACEHOLDER_SKILLS.map((skill) => (
                <div key={skill.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {skill.label}
                    </span>
                    <span
                      className="text-sm font-bold"
                      style={{ color: SKILL_COLORS[skill.level] ?? "#2563eb" }}
                    >
                      {skill.value}%
                    </span>
                  </div>
                  <div
                    className="h-2 w-full rounded-full overflow-hidden"
                    style={{ backgroundColor: "var(--bg-page)" }}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${skill.value}%`,
                        backgroundColor: SKILL_COLORS[skill.level] ?? "#2563eb",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
              Hoàn thành assessment để cập nhật kỹ năng của bạn.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
