"use client";
// app/(protected)/profile/page.tsx
// Profile page: user card + AI skill radar chart + stats.

import { useEffect, useState } from "react";
import { BookOpen, Trophy, Clock, TrendingUp } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { authApi, historyApi } from "@/lib/api";
import type {
  HistoryItem,
  HistorySummary,
  UserSkillSnapshot,
} from "@/types";
import RadarChart from "@/components/assessment/RadarChart";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { countJoinedCourseSlugs } from "@/features/course-membership/presenters";
import { usePageTitle } from "@/hooks/usePageTitle";
import { SKILL_COLORS } from "@/lib/ui/skillColors";

const DEFAULT_SKILLS: UserSkillSnapshot[] = [
  { label: "Machine Learning", value: 0, level: "not_started" },
  { label: "Deep Learning", value: 0, level: "not_started" },
  { label: "Computer Vision", value: 0, level: "not_started" },
  { label: "NLP", value: 0, level: "not_started" },
  { label: "LLM", value: 0, level: "not_started" },
];


interface AchievementBadge {
  title: string;
  desc: string;
  icon: string;
  color: string;
}

function getMembershipLabel(
  completedSessions: number,
  totalHours: number,
  hasSkillEvidence: boolean,
) {
  if (completedSessions >= 10 || totalHours >= 20) return "Advanced learner";
  if (hasSkillEvidence || completedSessions >= 3) return "Growing learner";
  return "New learner";
}

function normalizeDateKey(dateStr: string) {
  return new Date(dateStr).toISOString().slice(0, 10);
}

function calculateStudyStreak(items: HistoryItem[]) {
  const uniqueDays = Array.from(
    new Set(
      items
        .filter((item) => item.completed_at)
        .map((item) => normalizeDateKey(item.completed_at as string)),
    ),
  ).sort((a, b) => b.localeCompare(a));

  if (!uniqueDays.length) return 0;

  let streak = 1;
  let cursor = new Date(`${uniqueDays[0]}T00:00:00Z`);
  for (let i = 1; i < uniqueDays.length; i += 1) {
    const next = new Date(`${uniqueDays[i]}T00:00:00Z`);
    const deltaDays = Math.round((cursor.getTime() - next.getTime()) / 86_400_000);
    if (deltaDays === 1) {
      streak += 1;
      cursor = next;
      continue;
    }
    if (deltaDays > 1) break;
  }

  return streak;
}

function calculateJoinedCourseCount(items: HistoryItem[]) {
  return new Set(
    items
      .map((item) => item.course_slug)
      .filter((courseSlug): courseSlug is string => Boolean(courseSlug)),
  ).size;
}

function buildAchievements(
  completedSessions: number,
  totalHours: number,
  hasSkillEvidence: boolean,
) {
  const badges: AchievementBadge[] = [];

  if (hasSkillEvidence) {
    badges.push({
      title: "Skill profile unlocked",
      desc: "Completed the assessment to record your current ability",
      icon: "🧠",
      color: "border-tier-bronze bg-tier-bronze-soft",
    });
  }
  if (completedSessions >= 1) {
    badges.push({
      title: "First learning session",
      desc: "Completed at least 1 learning session or assessment",
      icon: "✨",
      color: "border-tier-silver bg-tier-silver-soft",
    });
  }
  if (completedSessions >= 5) {
    badges.push({
      title: "Consistent learner",
      desc: "Completed 5 or more learning sessions",
      icon: "🏆",
      color: "border-tier-gold bg-tier-gold-soft",
    });
  }
  if (totalHours >= 10) {
    badges.push({
      title: "Persistent",
      desc: "Reached 10 or more total study hours",
      icon: "⏱️",
      color: "border-tier-platinum bg-tier-platinum-soft",
    });
  }

  return badges;
}

interface StatRowProps {
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: string;
}

function StatRow({ icon, iconBg, label, value }: StatRowProps) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-surface-page px-3 py-2.5">
      <div className="flex items-center gap-2.5">
        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${iconBg}`}>
          {icon}
        </div>
        <span className="text-sm font-medium text-text-strong">
          {label}
        </span>
      </div>
      <span className="text-sm font-bold text-text-strong">
        {value}
      </span>
    </div>
  );
}

export default function ProfilePage() {
  usePageTitle("VinLearn - Profile");
  const user = useAuthStore((s) => s.user);
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [skills, setSkills] = useState<UserSkillSnapshot[]>(DEFAULT_SKILLS);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      historyApi.list({ page_size: 100 }),
      authApi.mySkills(),
    ])
      .then(([hist, skillOverview]) => {
        setSummary(hist.summary);
        setSkills(skillOverview.skills);
        setHistoryItems(hist.items);
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
  const hasSkillEvidence = skills.some((skill) => skill.level !== "not_started");
  const streakDays = calculateStudyStreak(historyItems);
  const joinedCourseCount = calculateJoinedCourseCount(historyItems);
  const membershipLabel = getMembershipLabel(
    completedSessions,
    totalHours,
    hasSkillEvidence,
  );
  const achievements = buildAchievements(
    completedSessions,
    totalHours,
    hasSkillEvidence,
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 animate-fade-in xl:max-w-7xl">
      <div>
        <h2 className="text-2xl font-bold text-text-strong">
          Your profile
        </h2>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <LoadingSpinner size="md" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          {/* ── LEFT: User info card ── */}
          <div className="space-y-4">
            <div className="card space-y-4">
              {/* Avatar + name */}
              <div className="flex flex-col items-center text-center gap-3 pb-4 border-b border-border-subtle">
                <div className="flex h-20 w-20 items-center justify-center rounded-full hero-gradient text-white text-2xl font-bold shadow-lg">
                  {initials}
                </div>
                <div>
                  <p className="text-lg font-bold text-text-strong">
                    {user.full_name}
                  </p>
                  <span className="mt-1 inline-flex items-center rounded-full bg-surface-accent-soft px-2.5 py-0.5 text-xs font-semibold text-primary-700">
                    {membershipLabel}
                  </span>
                </div>
              </div>

              {/* Stats list */}
              <div className="space-y-2">
                <StatRow
                  icon={<BookOpen className="h-4 w-4 text-stat-courses" />}
                  iconBg="bg-stat-courses-soft"
                  label="Courses"
                  value={String(joinedCourseCount)}
                />
                <StatRow
                  icon={<Trophy className="h-4 w-4 text-stat-progress" />}
                  iconBg="bg-stat-progress-soft"
                  label="Completed sessions"
                  value={String(completedSessions)}
                />
                <StatRow
                  icon={<Clock className="h-4 w-4 text-stat-time" />}
                  iconBg="bg-stat-time-soft"
                  label="Total time"
                  value={`${totalHours}h`}
                />
                <StatRow
                  icon={<TrendingUp className="h-4 w-4 text-stat-completed" />}
                  iconBg="bg-stat-completed-soft"
                  label="Streak"
                  value={`${streakDays} days`}
                />
              </div>
            </div>

            {/* Achievements */}
            <div className="card space-y-3">
              <h3 className="text-sm font-bold text-text-strong">
                Achievements
              </h3>
              {achievements.length > 0 ? (
                achievements.map((a) => (
                  <div
                    key={a.title}
                    className={`flex items-center gap-3 rounded-xl border p-3 ${a.color}`}
                  >
                    <span className="text-2xl">{a.icon}</span>
                    <div>
                      <p className="text-sm font-semibold text-text-strong">
                        {a.title}
                      </p>
                      <p className="text-xs text-text-body">
                        {a.desc}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-text-muted">
                  Complete the assessment or your first learning sessions to unlock achievements.
                </p>
              )}
            </div>

            {/* Account info */}
            <div className="card space-y-2">
              <h3 className="text-sm font-bold text-text-strong">
                Account
              </h3>
              <p className="text-sm text-text-body">
                <span className="text-text-muted">Email: </span>{user.email}
              </p>
              {user.preferred_method && (
                <p className="text-sm text-text-body">
                  <span className="text-text-muted">Learn with: </span>
                  {user.preferred_method === "video" ? "🎥 Video" : "📖 Reading materials"}
                </p>
              )}
              {user.available_hours_per_week && (
                <p className="text-sm text-text-body">
                  <span className="text-text-muted">Study hours / week: </span>
                  {user.available_hours_per_week}h
                </p>
              )}
            </div>
          </div>

          {/* ── RIGHT: Skills radar chart ── */}
          <div className="card space-y-6 xl:px-8">
            <div>
              <h3 className="text-base font-bold text-text-strong">
                Your AI skills
              </h3>
              <p className="text-sm mt-0.5 text-text-body">
                The radar chart shows your proficiency across different AI areas
              </p>
            </div>

            {/* Radar chart */}
            <div className="flex justify-center overflow-x-auto">
              <RadarChart data={skills} size={340} />
            </div>

            {/* Legend */}
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <div className="h-3 w-3 rounded-sm" style={{ backgroundColor: "rgba(37,99,235,0.3)", border: "2px solid #2563eb" }} />
              Current level
            </div>

            {/* Skill progress bars */}
            <div className="space-y-3">
              {skills.map((skill) => (
                <div key={skill.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-text-strong">
                      {skill.label}
                    </span>
                    <span
                      className="text-sm font-bold"
                      style={{ color: SKILL_COLORS[skill.level] ?? "#2563eb" }}
                    >
                      {skill.value}%
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-surface-page">
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

            <p className="text-xs text-center text-text-muted">
              {hasSkillEvidence
                ? "These skill levels are calculated from your assessment results and saved practice work."
                : "Complete the assessment to update your skills."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
