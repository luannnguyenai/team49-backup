"use client";

import { useState } from "react";
import type { LearningPathResponse } from "@/types";
import {
  createLearningProfileForPath,
  SUPPORTED_LEARNING_PATHS,
  type LearningProfile,
  type PlannerPathKey,
} from "../profile";
import ViewToggle, { type LearnView } from "./ViewToggle";

interface PlannerHeaderProps {
  profile: LearningProfile;
  summary: Omit<LearningPathResponse, "items"> | null;
  view: LearnView;
  onViewChange: (view: LearnView) => void;
  onProfileChange?: (profile: LearningProfile) => void;
}

export default function PlannerHeader({
  profile,
  summary,
  view,
  onViewChange,
  onProfileChange,
}: PlannerHeaderProps) {
  const [switcherOpen, setSwitcherOpen] = useState(false);

  const choosePath = (pathKey: PlannerPathKey) => {
    if (pathKey === profile.pathKey) {
      setSwitcherOpen(false);
      return;
    }

    onProfileChange?.(
      createLearningProfileForPath(pathKey, {
        weeklyHours: profile.weeklyHours,
        source: "manual",
      }),
    );
    setSwitcherOpen(false);
  };

  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Planner</p>
        <div className="relative mt-1 flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            {profile.label}
          </h1>
          <button
            type="button"
            onClick={() => setSwitcherOpen((open) => !open)}
            className="rounded-full border px-3 py-1 text-xs font-semibold text-primary-600 transition hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-500/40 dark:hover:bg-primary-950/30"
            style={{ borderColor: "var(--border)" }}
          >
            Đổi
          </button>

          {switcherOpen ? (
            <div
              role="dialog"
              aria-label="Đổi lộ trình"
              className="absolute left-0 top-full z-30 mt-2 w-72 rounded-2xl border bg-white p-2 shadow-xl dark:bg-slate-950"
              style={{ borderColor: "var(--border)" }}
            >
              <p className="px-3 py-2 text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                Chọn lộ trình muốn học
              </p>
              {(Object.keys(SUPPORTED_LEARNING_PATHS) as PlannerPathKey[]).map((pathKey) => {
                const path = SUPPORTED_LEARNING_PATHS[pathKey];
                const active = pathKey === profile.pathKey;

                return (
                  <button
                    key={pathKey}
                    type="button"
                    onClick={() => choosePath(pathKey)}
                    className="flex w-full items-start justify-between gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-slate-50 dark:hover:bg-slate-900"
                  >
                    <span>
                      <span className="block text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                        {path.label}
                      </span>
                      <span className="mt-0.5 block text-xs" style={{ color: "var(--text-secondary)" }}>
                        {path.selectedCourseIds.join(" → ")}
                      </span>
                    </span>
                    {active ? (
                      <span className="rounded-full bg-primary-50 px-2 py-0.5 text-xs font-semibold text-primary-600 dark:bg-primary-950/40">
                        Hiện tại
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
        {profile.weeklyHours ? (
          <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            {profile.weeklyHours} giờ/tuần
          </p>
        ) : null}
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
