"use client";

import type { LearningPathResponse } from "@/types";
import type { LearningProfile } from "../profile";
import ViewToggle, { type LearnView } from "./ViewToggle";

interface PlannerHeaderProps {
  profile: LearningProfile;
  summary: Omit<LearningPathResponse, "items"> | null;
  view: LearnView;
  onViewChange: (view: LearnView) => void;
}

export default function PlannerHeader({ profile, summary, view, onViewChange }: PlannerHeaderProps) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Planner</p>
        <h1 className="mt-1 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          {profile.label}
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Render theo path cụ thể: {profile.selectedCourseIds.join(" → ")}
          {profile.weeklyHours ? ` · ${profile.weeklyHours} giờ/tuần` : ""}
        </p>
        {summary ? (
          <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
            {summary.completed_units}/{summary.total_units} bài hoàn thành · {summary.in_progress_units} bài đang học
          </p>
        ) : null}
      </div>
      <ViewToggle view={view} onChange={onViewChange} />
    </div>
  );
}
