"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { AlertCircle, RefreshCw } from "lucide-react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import LearningUnitDrawer from "./LearningUnitDrawer";
import PathRequiredState from "./PathRequiredState";
import PlannerHeader from "./PlannerHeader";
import ProfileChangeBanner from "./ProfileChangeBanner";
import TimelineBoard from "./TimelineBoard";
import { usePersistedLearnView } from "./ViewToggle";
import { useLearningPathStore } from "../store";

const RoadmapCanvas = dynamic(() => import("./RoadmapCanvas"), {
  ssr: false,
  loading: () => <CanvasSkeleton />,
});

function CanvasSkeleton() {
  return (
    <div className="h-[70vh] animate-pulse rounded-2xl border p-8" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
      <div className="mx-auto h-16 w-56 rounded-2xl bg-slate-200 dark:bg-slate-800" />
      <div className="mx-auto mt-12 grid max-w-4xl grid-cols-2 gap-8">
        {Array.from({ length: 8 }).map((_, idx) => (
          <div key={idx} className="h-20 rounded-2xl bg-slate-200 dark:bg-slate-800" />
        ))}
      </div>
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="grid grid-flow-col auto-cols-[280px] gap-4 overflow-hidden pb-4">
      {Array.from({ length: 3 }).map((_, col) => (
        <div key={col} className="h-96 animate-pulse rounded-2xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
          <div className="h-5 w-24 rounded bg-slate-200 dark:bg-slate-800" />
          <div className="mt-5 space-y-3">
            {Array.from({ length: 4 }).map((__, idx) => (
              <div key={idx} className="h-20 rounded-xl bg-slate-200 dark:bg-slate-800" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LearningPathShell() {
  const [view, setView] = usePersistedLearnView();
  const profile = useLearningPathStore((s) => s.profile);
  const previousProfile = useLearningPathStore((s) => s.previousProfile);
  const generatedTopologyHash = useLearningPathStore((s) => s.generatedTopologyHash);
  const items = useLearningPathStore((s) => s.items);
  const summary = useLearningPathStore((s) => s.summary);
  const loading = useLearningPathStore((s) => s.loading);
  const error = useLearningPathStore((s) => s.error);
  const loadPath = useLearningPathStore((s) => s.loadPath);

  useEffect(() => {
    if (profile) {
      loadPath();
    }
  }, [loadPath, profile]);

  if (!profile) {
    return (
      <div className="mx-auto max-w-7xl animate-fade-in">
        <PathRequiredState />
      </div>
    );
  }

  if (!loading && !error && items.length === 0) {
    return (
      <div className="mx-auto max-w-7xl animate-fade-in">
        <PathRequiredState />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in">
      <PlannerHeader profile={profile} summary={summary} view={view} onViewChange={setView} />
      <ProfileChangeBanner
        previousProfile={previousProfile}
        currentProfile={profile}
        generatedTopologyHash={generatedTopologyHash}
        onRefreshPath={loadPath}
        refreshing={loading}
      />

      {loading ? (
        view === "graph" ? <CanvasSkeleton /> : <TimelineSkeleton />
      ) : error ? (
        <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border p-8 text-center" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
          <AlertCircle className="h-10 w-10 text-red-500" />
          <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>{error}</p>
          <button type="button" onClick={loadPath} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">
            <RefreshCw className="h-4 w-4" /> Thử lại
          </button>
        </div>
      ) : view === "graph" ? (
        <RoadmapCanvas />
      ) : (
        <TimelineBoard />
      )}

      {loading && (
        <div className="sr-only">
          <LoadingSpinner size="sm" />
        </div>
      )}
      <LearningUnitDrawer />
    </div>
  );
}
